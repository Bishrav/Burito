"""Loopback-only web console with a narrow Eve conversation API."""

from contextlib import ExitStack
import http.client
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
from urllib.parse import urlsplit

from .chat import ROOT
from .conversation_api import ConversationAPI
from .conversations import default_directory, open_store
from .memory import BRAIN_DATA, BRAIN_MOUNT, BRAIN_UUID, Memory, brain_available
from .notifications import notify_chat_complete
from .runtime_lock import acquire_runtime_lock

LOOPBACK = "127.0.0.1"
EVE_PORT = 2000
BRIDGE_PORT = 2001
MAX_BODY = 20_000


def runtime_request(port, path, *, body=None, token=None, timeout=2, host=LOOPBACK):
    headers = {"Content-Type": "application/json"} if body is not None else {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    connection = http.client.HTTPConnection(host, port, timeout=timeout)
    try:
        connection.request("POST" if body is not None else "GET", path, body, headers)
        response = connection.getresponse()
        payload = response.read(512_001)
        if len(payload) > 512_000:
            raise ValueError("Local runtime response is too large")
        return response.status, json.loads(payload)
    finally:
        connection.close()


def local_status(endpoint, model, token, eve_port=EVE_PORT, bridge_port=BRIDGE_PORT, eve_process=None):
    def probe(port, path, **kwargs):
        try:
            status, data = runtime_request(port, path, **kwargs)
            return data if status == 200 and isinstance(data, dict) else {}
        except (OSError, ValueError, http.client.HTTPException):
            return {}

    eve = ((eve_process is None or eve_process.poll() is None)
           and probe(eve_port, "/eve/v1/health").get("status") == "ready"
           and (eve_process is None or eve_process.poll() is None))
    bridge = probe(bridge_port, "/health", token=token).get("status") == "ready"
    models = probe(endpoint.port or 80, "/api/tags", host=endpoint.hostname).get("models")
    ollama = isinstance(models, list)
    name = model if ":" in model.rsplit("/", 1)[-1] else model + ":latest"
    installed = ollama and any(
        isinstance(row, dict) and row.get("name") in (model, name) for row in models
    )
    return {
        "status": "ready" if eve and bridge and installed else "unavailable",
        "eve": eve, "bridge": bridge, "ollama": ollama, "modelInstalled": installed,
        "model": model,
    }


class BuritoHandler(ConversationAPI, SimpleHTTPRequestHandler):
    notify_conversation = staticmethod(notify_chat_complete)
    protocol_version = "HTTP/1.1"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "ui"), **kwargs)

    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy",
                         "default-src 'self'; base-uri 'none'; frame-ancestors 'none'; object-src 'none'")
        super().end_headers()

    def send_json(self, status, data):
        payload = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)

    def trusted_request(self):
        host = f"{LOOPBACK}:{self.server.server_port}"
        origins = self.headers.get_all("Origin")
        if self.headers.get_all("Host") == [host] and origins in (None, [f"http://{host}"]):
            return True
        self.close_connection = True
        self.send_json(403, {"error": "Use the Burito loopback address directly."})
        return False

    def do_HEAD(self):
        if self.trusted_request():
            super().do_HEAD()

    def do_GET(self):
        if not self.trusted_request():
            return
        if self.path in ("/api/status", "/eve/v1/health"):
            status = local_status(self.server.endpoint, self.server.model, self.server.token,
                                  getattr(self.server, "eve_port", EVE_PORT),
                                  getattr(self.server, "bridge_port", BRIDGE_PORT),
                                  getattr(self.server, "eve_process", None))
            self.send_json(200 if status["status"] == "ready" else 503, status)
        elif not self.conversation_route("GET"):
            super().do_GET()

    def log_request(self, code="-", size="-"):
        self.log_message("%s %s", self.command, code)

    def do_PATCH(self):
        self.close_connection = True
        if self.trusted_request() and not self.conversation_route("PATCH"):
            self.send_json(404, {"error": "Unknown Burito route."})

    def do_DELETE(self):
        self.close_connection = True
        if self.trusted_request() and not self.conversation_route("DELETE"):
            self.send_json(404, {"error": "Unknown Burito route."})

    def request_body(self):
        if self.headers.get_content_type() != "application/json" or self.headers.get_all("Transfer-Encoding"):
            self.send_json(415, {"error": "Send a bounded JSON request."})
            return
        length = self.headers.get_all("Content-Length") or []
        if len(length) != 1 or not length[0].isascii() or not length[0].isdecimal() or len(length[0]) > 6:
            self.send_json(400, {"error": "Invalid content length."})
            return
        size = int(length[0])
        if not 0 < size <= MAX_BODY:
            self.send_json(413, {"error": "Chat request is too large or empty."})
            return
        try:
            body = self.rfile.read(size)
        except TimeoutError:
            self.send_json(408, {"error": "Timed out reading the chat request."})
            return
        if len(body) != size:
            self.send_json(400, {"error": "Incomplete chat request."})
            return None
        return body

    def json_request(self):
        body = self.request_body()
        if body is None:
            return None
        try:
            value = json.loads(body)
            if not isinstance(value, dict):
                raise ValueError
        except (ValueError, RecursionError):
            self.send_json(400, {"error": "Send a JSON object."})
            return None
        return value

    def bridge_request(self, route, data):
        return runtime_request(getattr(self.server, "bridge_port", BRIDGE_PORT), route, body=json.dumps(data).encode(),
                               token=self.server.token, timeout=8)

    def eve_alive(self):
        process = getattr(self.server, "eve_process", None)
        return process is None or process.poll() is None

    def do_POST(self):
        self.close_connection = True
        if not self.trusted_request() or self.conversation_route("POST"):
            return
        if self.path != "/api/chat":
            self.send_json(404, {"error": "Unknown Burito route."})
            return
        body = self.request_body()
        if body is None:
            return
        if not self.eve_alive():
            self.send_json(503, {"error": "This web session’s Eve process stopped."})
            return
        try:
            status, data = runtime_request(
                getattr(self.server, "bridge_port", BRIDGE_PORT), "/chat", body=body, token=self.server.token, timeout=125
            )
        except (OSError, ValueError, http.client.HTTPException):
            status, data = 502, {"error": "The local Eve conversation bridge is unavailable."}
        if status == 200 and self.server.notify:
            data["notificationAccepted"] = notify_chat_complete()
        self.send_json(status, data)


def _stop_process(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def _terminate_web(_signum, _frame):
    raise SystemExit(0)


def serve(model, context_tokens, port=8765, lesson="home.honesty", include_personal=False,
          include_system=False, include_activity=False, include_feedback=False,
          include_project=False, include_suggestions=False, include_experiences=False,
          include_academy=False, temporary_data=False, notify=False, conversation_dir=None):
    from .context import build_context
    from .school import School

    endpoint = urlsplit(os.environ.get("BURITO_LOCAL_URL") or "http://127.0.0.1:11434/v1")
    if (endpoint.scheme != "http" or endpoint.hostname not in {LOOPBACK, "::1"}
            or endpoint.username or endpoint.password or endpoint.query or endpoint.fragment
            or endpoint.path.rstrip("/") != "/v1"):
        raise ValueError("Web chat requires a local Ollama HTTP endpoint.")
    endpoint.port  # Validate an explicit port before starting the children.
    model = model.strip()
    if not model or not 4096 <= context_tokens <= 131072:
        raise ValueError("Choose an installed local model and a valid context size.")
    if not temporary_data and not brain_available():
        raise ValueError("Burito Brain drive is unavailable. Mount it or use --temporary-data for an isolated session.")
    runtime = ROOT / "runtime"
    env = os.environ.copy()
    for key in ("WORKFLOW_LOCAL_BASE_URL", "EVE_DEV_WORKFLOW_TRANSPORT_SECRET", "EVE_DEV_WORKER_APP_ROOT",
                "AI_GATEWAY_API_KEY", "BURITO_GATEWAY_MODEL", "BURITO_ONLINE_ENABLED",
                "BURITO_MEMORY_WRITES", "BURITO_GLOSSARY_WRITES"):
        env.pop(key, None)
    node_dirs = sorted((ROOT / ".tools").glob("node-*/bin"), reverse=True)
    if node_dirs:
        env["PATH"] = os.pathsep.join([str(node_dirs[0]), env.get("PATH", "")])
    node = shutil.which("node", path=env.get("PATH"))
    eve = runtime / "node_modules/.bin/eve"
    if not node or not eve.exists():
        raise ValueError("Runtime is missing. Run bash scripts/setup-runtime.sh.")

    with ExitStack() as stack:
        lock_fd = acquire_runtime_lock(runtime)
        stack.callback(os.close, lock_fd)
        directory = BRAIN_DATA
        if temporary_data:
            directory = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="burito-web-")))
        if conversation_dir is not None:
            conversation_data = Path(conversation_dir)
        elif temporary_data:
            conversation_data = directory / "transcripts"
        else:
            conversation_data = default_directory()
        if conversation_data.resolve().is_relative_to(BRAIN_MOUNT.resolve()):
            raise ValueError("The brain drive is reserved for existing personal data.")
        # Worktrees share the main repository path; reject storage anywhere in it.
        checkout = ROOT
        while checkout.parent.name == ".tools":
            checkout = checkout.parent.parent
        store = stack.enter_context(open_store(conversation_data, checkout))
        workflow_data = stack.enter_context(tempfile.TemporaryDirectory(prefix="burito-eve-", dir="/tmp"))
        memory = Memory(directory)
        if temporary_data:
            School(memory).install()
        build_context(lesson, include_personal, memory=memory, include_system=include_system,
                      include_activity=include_activity, include_feedback=include_feedback,
                      include_project=include_project, include_suggestions=include_suggestions,
                      include_experiences=include_experiences, include_academy=include_academy,
                      include_knowledge=include_academy)
        env.update({"BURITO_MODE": "local", "BURITO_LOCAL_MODEL": model,
                    "BURITO_CONTEXT_TOKENS": str(context_tokens), "BURITO_LESSON_ID": lesson,
                    "BURITO_INCLUDE_PERSONAL_MEMORY": "1" if include_personal else "0",
                    "BURITO_INCLUDE_SYSTEM": "1" if include_system else "0",
                    "BURITO_INCLUDE_ACTIVITY": "1" if include_activity else "0",
                    "BURITO_INCLUDE_FEEDBACK": "1" if include_feedback else "0",
                    "BURITO_INCLUDE_PROJECT": "1" if include_project else "0",
                    "BURITO_INCLUDE_SUGGESTIONS": "1" if include_suggestions else "0",
                    "BURITO_INCLUDE_EXPERIENCES": "1" if include_experiences else "0",
                    "BURITO_INCLUDE_ACADEMY": "1" if include_academy else "0",
                    "BURITO_INCLUDE_KNOWLEDGE": "1" if include_academy else "0",
                    "BURITO_DATA_DIR": str(directory),
                    "BURITO_PC_ACCESS": "0", "BURITO_WEB_CONVERSATION": "1", "BURITO_PROJECT_ROOT": str(ROOT),
                    "BURITO_PYTHON": sys.executable, "EVE_TELEMETRY_DISABLED": "1",
                    "EVE_TRACES_CONTENT": "off", "EVE_SCHEDULES_DISABLED": "1",
                    "EVE_DEV_STATE_DIR": workflow_data})
        server = stack.enter_context(ThreadingHTTPServer((LOOPBACK, port), BuritoHandler))
        server.endpoint, server.model, server.token = endpoint, model, secrets.token_urlsafe(32)
        server.notify, server.conversations = notify, store
        server.context_tokens = context_tokens
        with socket.socket() as eve_socket, socket.socket() as bridge_socket:
            eve_socket.bind((LOOPBACK, 0))
            bridge_socket.bind((LOOPBACK, 0))
            server.eve_port = eve_socket.getsockname()[1]
            server.bridge_port = bridge_socket.getsockname()[1]
        process = subprocess.Popen([node, str(eve), "dev", "--host", LOOPBACK, "--port", str(server.eve_port),
                                    "--no-ui", "--no-default-extensions"], cwd=runtime, env=env,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        server.eve_process = process
        stack.callback(_stop_process, process)
        bridge = subprocess.Popen([node, str(runtime / "lib/web-bridge.mjs")], cwd=runtime,
                                  env={**env, "BURITO_BRIDGE_TOKEN": server.token,
                                       "BURITO_EVE_PORT": str(server.eve_port),
                                       "BURITO_BRIDGE_PORT": str(server.bridge_port)})
        stack.callback(_stop_process, bridge)
        if threading.current_thread() is threading.main_thread():
            previous_handler = signal.signal(signal.SIGTERM, _terminate_web)
            stack.callback(signal.signal, signal.SIGTERM, previous_handler)
        print(f"Burito web console at http://{LOOPBACK}:{server.server_port}/", flush=True)
        server.serve_forever()
