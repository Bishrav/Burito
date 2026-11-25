"""Loopback-only web console and Eve API bridge."""

import http.client
import os
from pathlib import Path
import shutil
import subprocess
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from .chat import ROOT
from .runtime_lock import acquire_runtime_lock, archive_workflow_data


class BuritoHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    eve_port = 2000

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "ui"), **kwargs)

    def do_GET(self):
        if self.path.startswith("/eve/v1/"):
            return self.proxy()
        if self.path == "/" or self.path == "/index.html":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        if self.path == "/api/chat":
            self.proxy(port=2001, path="/chat")
        elif self.path.startswith("/eve/v1/"):
            self.proxy()
        else:
            self.send_error(404)

    def proxy(self, port=None, path=None):
        connection = http.client.HTTPConnection("127.0.0.1", port or self.eve_port, timeout=3600)
        headers = {key: value for key, value in self.headers.items()
                   if key.lower() not in {"host", "connection", "accept-encoding"}}
        headers["Host"] = f"127.0.0.1:{self.eve_port}"
        body = self.rfile.read(int(self.headers.get("Content-Length", "0"))) if self.command == "POST" else None
        try:
            connection.request(self.command, path or self.path, body=body, headers=headers)
            response = connection.getresponse()
            self.send_response(response.status, response.reason)
            for key, value in response.getheaders():
                if key.lower() not in {"connection", "transfer-encoding", "content-length", "content-encoding"}:
                    self.send_header(key, value)
            self.send_header("Transfer-Encoding", "chunked")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            while True:
                # read1 returns an available upstream chunk immediately. read(8192)
                # can buffer the live token stream until the model turn finishes.
                chunk = response.read1(8192)
                if not chunk:
                    break
                self.wfile.write(f"{len(chunk):X}\r\n".encode() + chunk + b"\r\n")
                self.wfile.flush()
            self.wfile.write(b"0\r\n\r\n")
        except (OSError, http.client.HTTPException) as error:
            if not self.wfile.closed:
                try:
                    self.send_error(502, f"Local Eve runtime unavailable: {error}")
                except (BrokenPipeError, ConnectionResetError):
                    pass
        finally:
            connection.close()

    def log_message(self, format, *args):
        print("Burito UI:", format % args)


def serve(model, context_tokens, port=8765, lesson="home.honesty", include_personal=False,
          include_system=False, include_activity=False, include_feedback=False,
          include_project=False, include_suggestions=False):
    from .context import build_context
    build_context(lesson, include_personal, include_system=include_system,
                  include_activity=include_activity, include_feedback=include_feedback,
                  include_project=include_project, include_suggestions=include_suggestions)
    brain_mount = Path("/mnt/burito-brain")
    if not brain_mount.is_mount():
        raise ValueError("Burito Brain drive is not mounted at /mnt/burito-brain; refusing to start with local fallback storage")
    runtime = ROOT / "runtime"
    env = os.environ.copy()
    for key in ("WORKFLOW_LOCAL_BASE_URL", "EVE_DEV_WORKFLOW_TRANSPORT_SECRET", "EVE_DEV_WORKER_APP_ROOT"):
        env.pop(key, None)
    node_dirs = sorted((ROOT / ".tools").glob("node-*/bin"), reverse=True)
    if node_dirs:
        env["PATH"] = os.pathsep.join([str(node_dirs[0]), env.get("PATH", "")])
    node = shutil.which("node", path=env.get("PATH"))
    eve = runtime / "node_modules/.bin/eve"
    if not node or not eve.exists():
        raise ValueError("Runtime is missing; run bash scripts/setup-runtime.sh")
    env.update({"BURITO_MODE": "local", "BURITO_LOCAL_MODEL": model,
                "BURITO_CONTEXT_TOKENS": str(context_tokens), "BURITO_LESSON_ID": lesson,
                "BURITO_INCLUDE_PERSONAL_MEMORY": "1" if include_personal else "0",
                "BURITO_INCLUDE_SYSTEM": "1" if include_system else "0",
                "BURITO_INCLUDE_ACTIVITY": "1" if include_activity else "0",
                "BURITO_INCLUDE_FEEDBACK": "1" if include_feedback else "0",
                "BURITO_INCLUDE_PROJECT": "1" if include_project else "0",
                "BURITO_INCLUDE_SUGGESTIONS": "1" if include_suggestions else "0",
                "BURITO_INCLUDE_KNOWLEDGE": "1",
                "BURITO_DATA_DIR": str(brain_mount / "data"),
                "BURITO_PC_ACCESS": "0", "BURITO_PROJECT_ROOT": str(ROOT),
                "BURITO_PYTHON": sys.executable, "EVE_TELEMETRY_DISABLED": "1",
                "EVE_TRACES_CONTENT": "off", "EVE_SCHEDULES_DISABLED": "1"})
    print(f"Starting Burito web console at http://127.0.0.1:{port}")
    print("Local model only. PC tools disabled. Press Ctrl+C to stop.", flush=True)
    lock_fd = acquire_runtime_lock(runtime)
    try:
        archived = archive_workflow_data(runtime)
        if archived:
            print(f"Archived prior Eve workflow state at {archived}; local Burito memory is unchanged.")
        process = subprocess.Popen([node, str(eve), "dev", "--host", "127.0.0.1", "--port", "2000",
                                    "--no-ui", "--no-default-extensions"], cwd=runtime, env=env)
        bridge = subprocess.Popen([node, str(runtime / "lib/web-bridge.mjs")], cwd=runtime, env=env)
        BuritoHandler.eve_port = 2000
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), BuritoHandler)
            with server:
                server.serve_forever()
        finally:
            bridge.terminate()
            bridge.wait(timeout=15)
            process.terminate()
            process.wait(timeout=15)
    finally:
        os.close(lock_fd)
