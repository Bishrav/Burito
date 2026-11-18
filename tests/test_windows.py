import json
from collections import deque
import unittest
from unittest.mock import patch

from burito import windows


class FakeReportChannel:
    def __init__(self, token):
        self.inbox = windows._ReportInbox(token)
        self.pending = deque()

    def send(self, payload):
        self.pending.append(json.dumps(payload))

    def wait(self, timeout):
        while self.pending:
            raw = self.pending.popleft()
            if self.inbox.receive(raw):
                return self.inbox.payload
        return None


class FakeKWin:
    def __init__(self, channel, load_id=7, report=None, run_error=None):
        self.channel = channel
        self.load_id = load_id
        self.report = report
        self.run_error = run_error
        self.calls = []

    def unload(self, script_name, timeout=1.0):
        self.calls.append(("unload", script_name))

    def load(self, script_path, script_name, timeout=2.0):
        self.calls.append(("load", script_path, script_name))
        return self.load_id

    def run(self, script_id, timeout=2.0):
        self.calls.append(("run", script_id))
        if self.run_error:
            raise self.run_error
        if self.report is not None:
            for payload in self.report if isinstance(self.report, list) else [self.report]:
                self.channel.send(payload)


class WindowBridgeTests(unittest.TestCase):
    token = "abc123"
    script_name = "burito-once-abc123"

    def request(self, *, action="list", internal_id=None, load_id=7, report=None,
                run_error=None, timeout=1.0):
        channel = FakeReportChannel(self.token)
        kwin = FakeKWin(channel, load_id=load_id, report=report, run_error=run_error)
        return channel, kwin, lambda: windows._perform_request(
            action, self.token, self.script_name, "/tmp/fake-main.js", kwin,
            channel, internal_id=internal_id, timeout=timeout)

    def test_success_unloads_before_load_and_always_cleans_up(self):
        expected = {"token": self.token, "ok": True, "windows": []}
        channel, kwin, run = self.request(report=expected)
        self.assertEqual(run(), expected)
        self.assertEqual([call[0] for call in kwin.calls], ["unload", "load", "run", "unload"])
        self.assertEqual(kwin.calls[2], ("run", 7))

    def test_negative_load_id_is_explicit_and_still_unloads(self):
        _, kwin, run = self.request(load_id=-1)
        with self.assertRaisesRegex(windows.WindowBridgeError, "load id -1.*run_called=false"):
            run()
        self.assertEqual([call[0] for call in kwin.calls], ["unload", "load", "unload"])

    def test_run_failure_reports_stage_and_still_unloads(self):
        _, kwin, run = self.request(run_error=RuntimeError("synthetic run failure"))
        with self.assertRaisesRegex(windows.WindowBridgeError,
                                    "synthetic run failure.*loaded_id=7, run_called=true, report_received=false"):
            run()
        self.assertEqual(kwin.calls[-1][0], "unload")

    def test_token_mismatch_is_ignored_until_matching_report_arrives(self):
        reports = [
            {"token": "wrong-token", "ok": True, "windows": [{"caption": "ignore"}]},
            {"token": self.token, "ok": True, "windows": []},
        ]
        _, _, run = self.request(report=reports)
        self.assertEqual(run(), reports[1])

    def test_timeout_reports_completed_stages(self):
        _, kwin, run = self.request(timeout=0.05)
        with self.assertRaisesRegex(windows.WindowBridgeError,
                                    "timed out.*loaded_id=7, run_called=true, report_received=false"):
            run()
        self.assertEqual(kwin.calls[-1][0], "unload")

    def test_script_exception_report_is_visible_with_report_stage(self):
        report = {"token": self.token, "ok": False, "error": "synthetic script exception"}
        _, kwin, run = self.request(report=report)
        with self.assertRaisesRegex(windows.WindowBridgeError,
                                    "synthetic script exception.*report_received=true"):
            run()
        self.assertEqual(kwin.calls[-1][0], "unload")

    def test_empty_window_list_is_a_valid_result(self):
        with patch.object(windows, "_request", return_value={"ok": True, "windows": []}):
            self.assertEqual(windows.list_windows()["windows"], [])

    def test_focus_reports_window_disappeared_before_focus(self):
        report = {"token": self.token, "ok": False, "error": "Window ID no longer exists."}
        _, _, run = self.request(action="focus", internal_id="a" * 36, report=report)
        with self.assertRaisesRegex(windows.WindowBridgeError,
                                    "Window ID no longer exists.*report_received=true"):
            run()

    def test_script_uses_window_list_fallback_and_request_result_channel(self):
        script = windows._kwin_script("list", self.token, "org.burito.Windows.Rabc")
        self.assertIn("workspace.windowList()", script)
        self.assertIn("workspace.clientList()", script)
        self.assertIn('"org.burito.Windows", "report"', script)
        self.assertIn('internalId:', script)
        self.assertIn('resourceClass:', script)
        self.assertIn('minimized:', script)

    def test_focus_script_uses_internal_id_and_returns_missing_window_error(self):
        script = windows._kwin_script(
            "focus", self.token, "org.burito.Windows.Rabc", internal_id="a" * 36)
        self.assertIn("workspace.activeWindow = target", script)
        self.assertIn("Window ID no longer exists.", script)

    def test_plasma5_path_is_used_only_when_plasma6_object_is_missing(self):
        transport = windows._KWinDBus("dbus-send")
        calls = []

        def fake_call(path, interface, method, arguments=(), **kwargs):
            calls.append((path, interface, method))
            if path == "/Scripting/Script7":
                raise windows.KWinDBusError("org.freedesktop.DBus.Error.UnknownObject")
            return ""

        with patch.object(transport, "_call", side_effect=fake_call):
            self.assertEqual(transport.run(7), "plasma5-fallback")
        self.assertEqual(calls, [
            ("/Scripting/Script7", "org.kde.kwin.Script", "run"),
            ("/7", "org.kde.kwin.Script", "run"),
        ])

    def test_plasma5_fallback_is_not_used_for_other_run_errors(self):
        transport = windows._KWinDBus("dbus-send")
        calls = []

        def fake_call(path, interface, method, arguments=(), **kwargs):
            calls.append(path)
            raise windows.KWinDBusError("KWin is unavailable")

        with patch.object(transport, "_call", side_effect=fake_call):
            with self.assertRaisesRegex(windows.KWinDBusError, "KWin is unavailable"):
                transport.run(7)
        self.assertEqual(calls, ["/Scripting/Script7"])


if __name__ == "__main__":
    unittest.main()
