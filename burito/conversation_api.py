"""Narrow loopback API for durable conversation metadata and live replies."""

import http.client
import json
import re
import sqlite3
import time
from urllib.parse import parse_qs, urlsplit

from .conversations import Conflict, OPTIONS, identifier

MAX_REPLY_BYTES = 64_000


DESKTOP_COMMAND = re.compile(
    r"^(?:(?:please|burito)[ ,:]*)?(?:open|launch|start|close|focus|minimize|switch to|install) "
    r"(?:the |my )?(?:calculator|terminal|file manager|browser|desktop app(?:lication)?)(?:[.!?,\s]|$)",
    re.IGNORECASE,
)


def _integer(value):
    if len(value) > 10 or not value.isascii() or not value.isdecimal():
        raise ValueError("Invalid pagination cursor.")
    return int(value)


class ConversationAPI:
    def conversation_route(self, method):
        target = urlsplit(self.path)
        base = "/api/conversations"
        if target.path not in (base, "/api/personality", "/api/turns", "/api/stop") and not target.path.startswith(base + "/"):
            return False
        try:
            store = self.server.conversations
            query = parse_qs(target.query)
            if target.path == base and method == "GET":
                rows = store.list(query.get("q", [""])[0], _integer(query.get("offset", ["0"])[0]))
                self.send_json(200, {"conversations": rows[:50], "more": len(rows) > 50})
            elif target.path == base and method == "POST":
                self.send_json(201, store.create())
            elif target.path.startswith(base + "/"):
                conversation = identifier(target.path[len(base) + 1:])
                if method == "GET":
                    before = _integer(query["before"][0]) if "before" in query else None
                    self.send_json(200, store.get(conversation, before))
                elif method == "PATCH":
                    body = self.json_request()
                    if body is not None:
                        self.send_json(200, store.rename(conversation, body.get("title")))
                elif method == "DELETE":
                    store.delete(conversation)
                    self.send_json(200, {"deleted": True})
                else:
                    self.send_json(405, {"error": "Unsupported conversation method."})
            elif target.path == "/api/personality" and method in ("GET", "POST"):
                body = self.json_request() if method == "POST" else {}
                if body is not None:
                    settings = store.settings(body if method == "POST" else None)
                    self.send_json(200, {"settings": settings, "options": OPTIONS})
            elif method == "POST" and target.path in ("/api/turns", "/api/stop"):
                body = self.json_request()
                if body is not None:
                    conversation = identifier(body.get("conversation"))
                    if target.path == "/api/stop":
                        request_id = identifier(body.get("requestId"))
                        if store.running_request(conversation) != request_id:
                            raise Conflict("There is no active reply to stop.")
                        status, result = self.bridge_request("/cancel", {"requestId": request_id})
                        self.send_json(status, result)
                    else:
                        request_id = identifier(body.get("requestId"))
                        retry = body.get("retry")
                        if retry is not None:
                            identifier(retry)
                        self.stream_conversation(conversation, request_id, body.get("message"), retry)
            else:
                self.send_json(405, {"error": "Unsupported conversation method."})
        except sqlite3.Error:
            self.send_json(503, {"error": "The conversation database is temporarily unavailable."})
        except Conflict as error:
            self.send_json(409, {"error": str(error)})
        except LookupError as error:
            self.send_json(404, {"error": str(error)})
        except (ValueError, UnicodeError) as error:
            self.send_json(400, {"error": str(error)})
        except (OSError, http.client.HTTPException):
            self.send_json(502, {"error": "The local conversation bridge is unavailable."})
        return True

    def stream_conversation(self, conversation, request_id, message, retry):
        store = self.server.conversations
        turn_id, message = store.begin(conversation, request_id, message, retry=retry)
        if message is None:
            self.send_json(200, {"duplicate": True, "turnId": turn_id})
            return

        if DESKTOP_COMMAND.match(message):
            reply = "I can’t control desktop apps from this web chat. No action was taken."
            try:
                store.record(request_id, reply, "completed")
            except sqlite3.Error:
                store.abandon(request_id)
                raise
            self.send_json(200, {"reply": reply, "status": "completed", "turnId": turn_id, "restricted": True})
            return

        reply = ""
        connected = True

        def emit(event):
            nonlocal connected
            if not connected:
                return
            try:
                self.wfile.write(json.dumps(event, ensure_ascii=False).encode() + b"\n")
                self.wfile.flush()
            except OSError:
                connected = False

        final = {"type": "done", "status": "failed", "detail": "The local model or runtime interrupted the reply."}
        headers_sent = False
        upstream = http.client.HTTPConnection("127.0.0.1", self.server.bridge_port, timeout=135)
        try:
            if not self.eve_alive():
                raise OSError("This web session’s Eve process stopped.")
            context, budget = store.context(conversation, message, self.server.context_tokens)
            payload = {"requestId": request_id, "message": message, "context": context, "personality": store.settings()}
            upstream.request("POST", "/stream", json.dumps(payload, ensure_ascii=False).encode(),
                             {"Content-Type": "application/json", "Authorization": f"Bearer {self.server.token}"})
            response = upstream.getresponse()
            if response.status != 200:
                store.record(request_id, "", "failed")
                self.send_json(409 if response.status == 409 else 502,
                               {"error": "Another runtime reply is active." if response.status == 409
                                else "The local runtime could not start the reply."})
                return
            headers_sent = True
            try:
                self.send_response(200)
                self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Connection", "close")
                self.end_headers()
            except OSError:
                connected = False
            emit({"type": "start", "turnId": turn_id, "contextBytes": len(json.dumps(context, ensure_ascii=False).encode()),
                  "contextBudgetBytes": budget})
            last_saved = time.monotonic()
            while line := response.readline(MAX_REPLY_BYTES + 1):
                if len(line) > MAX_REPLY_BYTES:
                    raise ValueError("Local response exceeded its limit.")
                event = json.loads(line)
                if event["type"] == "delta":
                    reply += event["text"]
                    if len(reply.encode()) > MAX_REPLY_BYTES:
                        reply = reply.encode()[:MAX_REPLY_BYTES].decode(errors="ignore")
                        self.bridge_request("/cancel", {"requestId": request_id})
                        break
                    if time.monotonic() - last_saved >= 0.5:
                        store.record(request_id, reply)
                        last_saved = time.monotonic()
                if event["type"] == "done":
                    final = event
                    reply = event.get("reply", reply)
                    break
                emit(event)
        except sqlite3.Error:
            store.abandon(request_id)
            if not headers_sent:
                raise
            emit({"type": "done", "status": "failed", "reply": reply,
                  "detail": "The reply could not be saved to the conversation database."})
            return
        except (OSError, ValueError, KeyError, http.client.HTTPException):
            if not headers_sent:
                try:
                    store.record(request_id, reply, "failed")
                except sqlite3.Error:
                    store.abandon(request_id)
                    raise
                self.send_json(502, {"error": "The local conversation bridge is unavailable."})
                return
        finally:
            upstream.close()

        status = final["status"]
        reply = reply.encode()[:MAX_REPLY_BYTES].decode(errors="ignore")
        try:
            store.record(request_id, reply, status, final.get("metrics"))
        except sqlite3.Error:
            store.abandon(request_id)
            emit({"type": "done", "status": "failed", "reply": reply,
                  "detail": "The reply could not be saved to the conversation database."})
            return
        final["reply"] = reply
        if status == "completed" and self.server.notify:
            final["notificationAccepted"] = self.notify_conversation()
        emit(final)
