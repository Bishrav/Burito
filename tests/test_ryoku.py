import http.client
from http.server import ThreadingHTTPServer
import json
import os
import queue
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit

from burito import desktop, doctor, web
from burito.windows import WindowBridgeError


class DesktopAdapterTests(unittest.TestCase):
    def test_hyprland_active_window_and_approved_focus(self):
        row = {"mapped": True, "stableId": "42", "class": "synthetic",
               "title": "Demo", "workspace": {"name": "2", "id": 2}}

        def reply(*args):
            if args[0] == "eval":
                self.assertIn('window = "stableid:42"', args[1])
                return "ok\n"
            return json.dumps({"clients": [row], "activewindow": row,
                               "activeworkspace": row["workspace"]}[args[1]])

        with patch("burito.desktop.provider", return_value="hyprland"), \
             patch("burito.desktop._hyprctl", side_effect=reply) as ipc:
            snapshot = desktop.list_windows()
            self.assertEqual(snapshot["provider"], "hyprland")
            window = snapshot["windows"][0]
            self.assertTrue(window["active"])
            self.assertTrue(window["onCurrentDesktop"])
            self.assertIsNone(window["minimized"])
            self.assertEqual(desktop.focus_window("hyprland:42")["window"], window)
            calls = ipc.call_count
            with self.assertRaises(WindowBridgeError):
                desktop.focus_window('hyprland:42"); fake("')
            self.assertEqual(ipc.call_count, calls)

    def test_kwin_fallback_keeps_existing_window_contract(self):
        expected = {"windows": [{"internalId": "a" * 36}]}
        with patch("burito.desktop.provider", return_value="kwin"), \
             patch("burito.windows.list_windows", return_value=expected), \
             patch("burito.windows.focus_window", return_value={"status": "focused"}) as focus:
            self.assertEqual(desktop.list_windows(), {**expected, "provider": "kwin"})
            self.assertEqual(desktop.focus_window("a" * 36), {"status": "focused"})
            focus.assert_called_once_with("a" * 36)


class BrainMountTests(unittest.TestCase):
    def test_web_cli_passes_only_explicit_cognitive_scopes(self):
        with patch("burito.web.serve") as serve:
            from burito.__main__ import main
            self.assertEqual(main(["web", "--model", "synthetic-model", "--context-tokens", "8192",
                                   "--temporary-data", "--include-project", "--include-experiences",
                                   "--include-academy"]), 0)
        options = serve.call_args.kwargs
        self.assertTrue(options["include_project"])
        self.assertTrue(options["include_experiences"])
        self.assertTrue(options["include_academy"])
        self.assertFalse(options["include_personal"])

    def test_web_opens_the_verified_memory_directory_not_a_parallel_database(self):
        class ReachedMemory(Exception):
            pass

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "checkout"
            eve = root / "runtime/node_modules/.bin/eve"
            eve.parent.mkdir(parents=True)
            eve.touch()
            transcripts = Path(temporary) / "transcripts"
            def memory_path(path):
                self.assertEqual(path, web.BRAIN_DATA)
                raise ReachedMemory

            with patch.object(web, "ROOT", root), \
                 patch.object(web, "brain_available", return_value=True), \
                 patch.object(web.shutil, "which", return_value="/usr/bin/node"), \
                 patch.object(web, "acquire_runtime_lock", return_value=os.open("/dev/null", os.O_RDONLY)), \
                 patch.object(web, "Memory", side_effect=memory_path):
                with self.assertRaises(ReachedMemory):
                    web.serve("synthetic-model", 8192, conversation_dir=str(transcripts))

    def test_web_storage_requires_verified_ext4_uuid(self):
        from burito import memory

        with tempfile.TemporaryDirectory() as temporary:
            mount = Path(temporary) / "brain"
            data = mount / "data"
            data.mkdir(parents=True)
            with patch.object(memory, "BRAIN_MOUNT", mount), patch.object(memory, "BRAIN_DATA", data), \
                 patch.object(memory, "BRAIN_UUID", "expected"), patch.object(memory.subprocess, "run") as probe:
                probe.return_value.stdout = "different-volume ext4 rw,noatime\n"
                self.assertFalse(web.brain_available())
                probe.return_value.stdout = "expected ext4 rw,noatime\n"
                self.assertTrue(web.brain_available())


class DefaultBrainSafetyTests(unittest.TestCase):
    def test_missing_or_wrong_brain_never_creates_placeholder_database(self):
        from burito import memory

        with tempfile.TemporaryDirectory() as temporary:
            mount = Path(temporary) / "brain"
            data = mount / "data"
            env = {"PATH": os.environ["PATH"]}
            with patch.dict(os.environ, env, clear=True), \
                 patch.object(memory, "BRAIN_MOUNT", mount), patch.object(memory, "BRAIN_DATA", data), \
                 patch.object(memory.subprocess, "run", side_effect=FileNotFoundError):
                self.assertEqual(memory.data_directory(), data)
                with self.assertRaisesRegex(ValueError, "no fallback database"):
                    memory.Memory().list()
                self.assertFalse(mount.exists())

    def test_approved_launch_is_blocked_without_auditable_brain(self):
        from burito import memory

        with tempfile.TemporaryDirectory() as temporary:
            mount = Path(temporary) / "brain"
            with patch.dict(os.environ, {"BURITO_APPROVED_APP_LAUNCH": "1"}, clear=True), \
                 patch.object(memory, "BRAIN_MOUNT", mount), patch.object(memory, "BRAIN_DATA", mount / "data"), \
                 patch.object(memory, "brain_available", return_value=False), \
                 patch("burito.access.launch_application") as launch:
                with self.assertRaisesRegex(ValueError, "no fallback database"):
                    from burito.access import dispatch
                    dispatch({"action": "launch", "app_id": "test:app.desktop", "sha256": "a" * 64})
            launch.assert_not_called()
            self.assertFalse(mount.exists())

    def test_doctor_does_not_report_internal_free_space_as_brain_capacity(self):
        with patch.dict(os.environ, {"PATH": os.environ["PATH"]}, clear=True), \
             patch("burito.doctor.brain_status", return_value="unavailable"), \
             patch("burito.doctor.probe", return_value={"ok": False, "detail": "not found"}), \
             patch("burito.doctor.shutil.disk_usage") as disk_usage:
            result = doctor.report()
        self.assertIs(result["brain_available"], False)
        self.assertIsNone(result["storage_free_gib"])
        self.assertIsNone(result["storage_total_gib"])
        disk_usage.assert_not_called()

    def test_read_only_brain_is_reported_and_rejected_before_database_creation(self):
        from burito import memory

        with tempfile.TemporaryDirectory() as temporary:
            mount = Path(temporary) / "brain"
            data = mount / "memory"
            data.mkdir(parents=True)
            result = type("Result", (), {"stdout": "expected ext4 ro,nosuid,noatime"})()
            with patch.object(memory, "BRAIN_MOUNT", mount), patch.object(memory, "BRAIN_DATA", data), \
                 patch.object(memory, "BRAIN_UUID", "expected"), \
                 patch.object(memory.subprocess, "run", return_value=result):
                self.assertEqual(memory.brain_status(), "read_only")
                with self.assertRaisesRegex(ValueError, "no fallback database"):
                    memory.Memory().initialize()
            self.assertFalse((data / "memory.sqlite3").exists())

    def test_full_brain_is_rejected_before_database_creation(self):
        from burito import memory

        with tempfile.TemporaryDirectory() as temporary:
            mount = Path(temporary) / "brain"
            data = mount / "memory"
            data.mkdir(parents=True)
            result = type("Result", (), {"stdout": "expected ext4 rw,noatime"})()
            no_space = type("Usage", (), {"free": 0})()
            with patch.object(memory, "BRAIN_MOUNT", mount), patch.object(memory, "BRAIN_DATA", data), \
                 patch.object(memory, "BRAIN_UUID", "expected"), \
                 patch.object(memory.subprocess, "run", return_value=result), \
                 patch.object(memory.shutil, "disk_usage", return_value=no_space):
                self.assertEqual(memory.brain_status(), "full")
                with self.assertRaisesRegex(ValueError, "no fallback database"):
                    memory.Memory().initialize()
            self.assertFalse((data / "memory.sqlite3").exists())


class WebIntegrationTests(unittest.TestCase):
    def setUp(self):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", 0), web.BuritoHandler)
        except PermissionError:
            self.skipTest("Loopback listener unavailable")
        server.endpoint = urlsplit("http://127.0.0.1:11434/v1")
        server.model, server.token, server.notify = "test-model", "test-token", True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.port = server.server_port

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        try:
            connection.request(method, path, body, headers or {})
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def test_exited_owned_eve_is_unready_even_when_health_endpoint_answers(self):
        from unittest.mock import Mock
        with patch("burito.web.runtime_request", return_value=(200, {"status": "ready", "models": []})) as request:
            result = web.local_status(urlsplit("http://127.0.0.1:11434/v1"), "demo", "test-token",
                                      eve_port=23456, eve_process=Mock(poll=Mock(return_value=1)))
        self.assertFalse(result["eve"])
        self.assertTrue(all(call.args[0] != 23456 for call in request.call_args_list))

    def test_readiness_requires_installed_model_and_both_runtime_processes(self):
        def runtime(port, path, **kwargs):
            if path == "/api/tags":
                return 200, {"models": [{"name": "test-model:latest"}]}
            return 200, {"status": "ready"}

        with patch("burito.web.runtime_request", side_effect=runtime):
            status, data = self.request("GET", "/api/status")
            self.assertEqual((status, data["status"]), (200, "ready"))
        with patch("burito.web.runtime_request", return_value=(200, {"status": "ready", "models": []})):
            status, data = self.request("GET", "/api/status")
            self.assertEqual((status, data["modelInstalled"]), (503, False))

    def test_chat_rejects_external_origin_and_forwards_only_chat(self):
        received = queue.SimpleQueue()

        def runtime(port, path, **kwargs):
            received.put((port, path, json.loads(kwargs["body"]), kwargs["token"]))
            return 200, {"status": "completed", "reply": "ready"}

        body = '{"message":"ready"}'
        headers = {"Content-Type": "application/json"}
        with patch("burito.web.runtime_request", side_effect=runtime), \
             patch("burito.web.notify_chat_complete", return_value=True):
            self.assertEqual(self.request("POST", "/api/chat", body, {
                **headers, "Origin": "https://external.example",
            })[0], 403)
            self.assertEqual(self.request("POST", "/api/chat", body, {
                **headers, "Host": "external.example",
            })[0], 403)
            self.assertEqual(self.request("POST", "/eve/v1/session", body, headers)[0], 404)
            self.assertEqual(self.request("POST", "/api/chat", "x" * 20_001, headers)[0], 413)
            status, reply = self.request("POST", "/api/chat", body, headers)
        self.assertEqual((status, reply["reply"], reply["notificationAccepted"]), (200, "ready", True))
        self.assertEqual(received.get_nowait(), (web.BRIDGE_PORT, "/chat", {"message": "ready"}, "test-token"))
        self.assertTrue(received.empty())
