"""Evaluate Phase 2 against a local Ollama daemon using synthetic chats only."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import signal
import socket
import statistics
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener
import uuid

HTTP = build_opener(ProxyHandler({}))
ROOT = Path(__file__).resolve().parent.parent
PROMPT = "List exactly twelve common kitchen items, one per line. No introduction."


class Evaluation:
    def __init__(self, port, model):
        self.base = f"http://127.0.0.1:{port}"
        self.port, self.model = port, model
        self.failures = []

    def send(self, path, body=None, method=None):
        payload = None if body is None else json.dumps(body).encode()
        request = Request(self.base + path, payload, method=method,
                          headers={"Content-Type": "application/json"} if payload else {})
        try:
            return HTTP.open(request, timeout=145)
        except HTTPError as error:
            return error

    def api(self, path, body=None, method=None, expected=200):
        with self.send(path, body, method) as response:
            result = json.load(response)
            if response.status != expected:
                raise RuntimeError(f"{path} returned {response.status}, expected {expected}")
            return result

    @contextmanager
    def server(self, root, state=None, ollama_url="http://127.0.0.1:11434/v1", expected=200):
        command = [sys.executable, "-m", "burito", "web", "--temporary-data",
                   "--model", self.model, "--context-tokens", "8192", "--port", str(self.port)]
        if state is not None:
            command += ["--conversation-dir", str(state)]
        with tempfile.TemporaryFile() as output:
            process = subprocess.Popen(
                command, cwd=root, stdout=output, stderr=output,
                env={**os.environ, "BURITO_LOCAL_URL": ollama_url, "PYTHONDONTWRITEBYTECODE": "1"},
            )
            try:
                for _ in range(100):
                    if process.poll() is not None:
                        raise RuntimeError(f"Temporary web server exited {process.returncode}. Check for port use.")
                    try:
                        data = self.api("/api/status", expected=expected)
                        if data["eve"] and data["bridge"]:
                            break
                    except (URLError, RuntimeError, ConnectionError):
                        pass
                    time.sleep(0.15)
                else:
                    raise RuntimeError("Temporary web server did not reach expected readiness.")
                yield process
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=30)

    def conversation(self):
        return self.api("/api/conversations", method="POST", expected=201)["id"]

    def turn(self, conversation, message=None, retry=None, request_id=None, on_delta=None):
        payload = {"conversation": conversation, "requestId": request_id or uuid.uuid4().hex}
        payload["retry" if retry is not None else "message"] = retry if retry is not None else message
        start = time.perf_counter()
        first = final = accepted = None
        with self.send("/api/turns", payload) as response:
            if response.status != 200:
                raise RuntimeError(f"Turn failed to start: HTTP {response.status} {json.load(response).get('error')}")
            if not response.headers.get_content_type() == "application/x-ndjson":
                outcome = json.load(response)
                if outcome.get("restricted"):
                    return outcome
                raise RuntimeError("Unexpected turn response")
            for raw in response:
                event = json.loads(raw)
                if event["type"] == "start":
                    accepted = event
                if event["type"] == "delta" and first is None:
                    first = (time.perf_counter() - start) * 1000
                    if on_delta:
                        on_delta()
                if event["type"] in {"tool", "approval"}:
                    raise AssertionError("Unexpected tool or approval event in the read-only web runtime.")
                if event["type"] == "done":
                    final = event
        if not final:
            raise RuntimeError("The turn closed without a result.")
        final["visibleMs"] = round(first) if first is not None else None
        final["clientTotalMs"] = round((time.perf_counter() - start) * 1000)
        final["contextBytes"] = accepted["contextBytes"]
        return final

    def scenario(self, name, check):
        if not check:
            self.failures.append(name)
        print(json.dumps({"scenario": name, "passed": bool(check)}), flush=True)


def evaluate(evaluation, state, iterations):
    with evaluation.server(ROOT, state):
        performance = []
        for _ in range(iterations):
            sample = evaluation.turn(evaluation.conversation(), PROMPT)
            assert sample["status"] == "completed" and sample["visibleMs"] < sample["clientTotalMs"]
            performance.append({**sample["metrics"], "visibleMs": sample["visibleMs"],
                                "clientTotalMs": sample["clientTotalMs"]})
        print(json.dumps({"phase": 2, "performance": performance,
                          "medianVisibleMs": statistics.median(row["visibleMs"] for row in performance)}), flush=True)

        chat = evaluation.conversation()
        request_id = uuid.uuid4().hex
        assert evaluation.turn(chat, "The synthetic festival is called Mimosa. Acknowledge briefly.",
                               request_id=request_id)["status"] == "completed"
        repeated = evaluation.api("/api/turns", {"conversation": chat, "requestId": request_id, "message": "duplicate"})
        evaluation.scenario("duplicate request", repeated["duplicate"] and len(evaluation.api(f"/api/conversations/{chat}")["turns"]) == 1)
        reply = evaluation.turn(chat, "What is it called? Answer with the name only.")["reply"]
        evaluation.scenario("follow-up reference", "mimosa" in reply.casefold())
        assert evaluation.turn(chat, "Correction: the festival is now called Juniper. Acknowledge briefly.")["status"] == "completed"
        reply = evaluation.turn(chat, "What is its current name? Answer with the name only.")["reply"]
        evaluation.scenario("user correction", "juniper" in reply.casefold() and "mimosa" not in reply.casefold())
        reply = evaluation.turn(evaluation.conversation(), "Move it there.")["reply"]
        evaluation.scenario("ambiguous request", "?" in reply)
        action = evaluation.turn(evaluation.conversation(), "Open the calculator on my desktop now. Do it, then report success.")
        reply = action["reply"].casefold()
        clear_limit = any(phrase in reply for phrase in ("can't", "cannot", "can’t", "unable", "don't have", "do not have"))
        evaluation.scenario("no unsupported action claim", action["status"] == "completed" and clear_limit and action.get("restricted"))
        if not clear_limit:
            print(json.dumps({"synthetic_action_status": action["status"], "synthetic_reply": action["reply"]}), flush=True)


        stop_chat = evaluation.conversation()
        stop_request = uuid.uuid4().hex

        def stop():
            evaluation.api("/api/stop", {"conversation": stop_chat, "requestId": stop_request}, expected=202)
        stopped = evaluation.turn(stop_chat, "Write an ordered list of 80 synthetic city names. Use one line per name.",
                                  request_id=stop_request, on_delta=stop)
        evaluation.scenario("live cancellation", stopped["status"] == "cancelled")
        active = evaluation.api(f"/api/conversations/{stop_chat}")["turns"]
        retried = evaluation.turn(stop_chat, retry=active[0]["id"])
        if retried["status"] != "completed":
            print(json.dumps({"synthetic_retry_status": retried["status"], "detail": retried.get("detail")}), flush=True)
        evaluation.scenario("retry without duplicate", retried["status"] == "completed"
                            and len(evaluation.api(f"/api/conversations/{stop_chat}")["turns"]) == 1)

        detached_chat = evaluation.conversation()
        body = {"conversation": detached_chat, "requestId": uuid.uuid4().hex,
                "message": "Reply with the word hello."}
        with evaluation.send("/api/turns", body) as response:
            assert json.loads(response.readline())["type"] == "start"
        for _ in range(80):
            row = evaluation.api(f"/api/conversations/{detached_chat}")["turns"][0]
            if row["status"] != "running":
                break
            time.sleep(0.25)
        evaluation.scenario("browser disconnection", row["status"] == "completed")

        interrupted_chat = evaluation.conversation()
        interrupted_response = evaluation.send("/api/turns", {
            "conversation": interrupted_chat, "requestId": uuid.uuid4().hex,
            "message": "Write a lengthy list of 12 invented machine names, one per line."
        })
        assert json.loads(interrupted_response.readline())["type"] == "start"
    interrupted_response.close()

    from burito.conversations import open_store
    with open_store(state, ROOT) as store:
        long_chat = store.create()["id"]
        initial = uuid.uuid4().hex
        store.begin(long_chat, initial, "We think the synthetic calibration label is Goldfinch, but it is unverified.")
        store.record(initial, "Goldfinch is an unverified label.", "completed")
        for index in range(60):
            request = uuid.uuid4().hex
            store.begin(long_chat, request, f"Unrelated fixture {index}. " + "Quiet. " * 260)
            store.record(request, "Acknowledged. " * 100, "completed")

    with evaluation.server(ROOT, state) as process:
        reply = evaluation.turn(chat, "After reopening this chat, what is the festival's current name?")["reply"]
        evaluation.scenario("application restart", "juniper" in reply.casefold())
        interrupted = evaluation.api(f"/api/conversations/{interrupted_chat}")["turns"]
        evaluation.scenario("interrupted turn restored after restart",
                            len(interrupted) == 1 and interrupted[0]["status"] in {"failed", "interrupted"})
        recovered = evaluation.turn(interrupted_chat, retry=interrupted[0]["id"])
        evaluation.scenario("interrupted turn retry", recovered["status"] == "completed")
        sample = evaluation.turn(long_chat, "What is the Goldfinch calibration label and is it verified?")
        evaluation.scenario("bounded long context", sample["status"] == "completed" and sample["contextBytes"] <= 2500
                            and sample["metrics"]["inputTokens"] < 8192 and "goldfinch" in sample["reply"].casefold())
        children_path = Path(f"/proc/{process.pid}/task/{process.pid}/children")
        eve = next(int(pid) for pid in children_path.read_text().split()
                   if b"/node_modules/.bin/eve\0" in Path(f"/proc/{pid}/cmdline").read_bytes())
        os.kill(eve, signal.SIGTERM)
        for _ in range(30):
            with evaluation.send("/api/status") as response:
                status = json.load(response)
                if response.status == 503 and not status["eve"]:
                    break
            time.sleep(0.15)
        evaluation.scenario("Eve failure reported", not status["eve"])

    with evaluation.server(ROOT, state, ollama_url="http://127.0.0.1:19876/v1", expected=503):
        status = evaluation.api("/api/status", expected=503)
        evaluation.scenario("Ollama unavailability reported", not status["ollama"] and status["eve"])
    with evaluation.server(ROOT, state):
        status = evaluation.api("/api/status")
        evaluation.scenario("runtime recovery", status["status"] == "ready")
        evaluation.scenario("local-only evaluation transport", evaluation.base.startswith("http://127.0.0.1:"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="burito-local")
    parser.add_argument("--port", type=int, default=18765)
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--offline-smoke", action="store_true", help="Require a network namespace exposing only loopback.")
    parser.add_argument("--phase1-root", type=Path, help="Prepared Phase 1 checkout for the optional comparison.")
    args = parser.parse_args()
    if not 1 <= args.iterations <= 10:
        parser.error("Choose 1 to 10 iterations.")
    evaluation = Evaluation(args.port, args.model)
    if args.offline_smoke:
        if {name for _, name in socket.if_nameindex()} != {"lo"}:
            parser.error("Run this check in a network namespace exposing only loopback.")
        with tempfile.TemporaryDirectory(prefix="burito-conversation-offline-") as directory:
            with evaluation.server(ROOT, Path(directory)):
                result = evaluation.turn(evaluation.conversation(), "Reply with exactly the word ready.")
                evaluation.scenario("offline live stream", result["status"] == "completed"
                                    and result["visibleMs"] is not None and "ready" in result["reply"].casefold())
        return int(bool(evaluation.failures))
    if args.phase1_root:
        with evaluation.server(args.phase1_root.resolve()):
            baseline = []
            for _ in range(args.iterations):
                start = time.perf_counter()
                result = evaluation.api("/api/chat", {"message": PROMPT})
                assert result["status"] == "completed"
                baseline.append(round((time.perf_counter() - start) * 1000))
            print(json.dumps({"phase": 1, "visibleAndTotalMs": baseline,
                              "medianVisibleMs": statistics.median(baseline)}), flush=True)
    with tempfile.TemporaryDirectory(prefix="burito-conversation-eval-") as directory:
        sys.path.insert(0, str(ROOT))
        evaluate(evaluation, Path(directory), args.iterations)
    if evaluation.failures:
        raise SystemExit("Failed scenarios: " + ", ".join(evaluation.failures))


if __name__ == "__main__":
    sys.exit(main())
