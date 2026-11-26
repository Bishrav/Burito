import json
from pathlib import Path
import tempfile
import unittest
import uuid

from burito.conversations import Conflict, bounded_context, open_store, profile


def key():
    return uuid.uuid4().hex


class ConversationStoreTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.checkout = self.directory / "checkout"
        self.state = self.directory / "state"

    def test_history_preferences_and_interruption_survive_reopen(self):
        request = key()
        with open_store(self.state, self.checkout) as store:
            chat = store.create()["id"]
            turn, _ = store.begin(chat, request, "Project name is Mimosa")
            self.assertEqual(store.list("mIMOSA")[0]["title"], "Project name is Mimosa")
            store.record(request, "Partial ")
            store.rename(chat, "Research")
            store.settings({"tone": "warm"})
            with self.assertRaises(ValueError):
                with open_store(self.state, self.checkout):
                    self.fail("Second runtime gained exclusive access")
        with open_store(self.state, self.checkout) as store:
            saved = store.get(chat)["turns"][0]
            self.assertEqual((saved["id"], saved["reply"], saved["status"]), (turn, "Partial ", "interrupted"))
            self.assertEqual(store.settings()["tone"], "warm")
            self.assertEqual(store.list("research")[0]["id"], chat)
            store.delete(chat)
            with self.assertRaises(LookupError):
                store.get(chat)
        self.assertEqual((self.state / "conversations.sqlite3").stat().st_mode & 0o777, 0o600)

    def test_duplicate_and_retry_never_insert_a_second_message(self):
        with open_store(self.state, self.checkout) as store:
            chat = store.create()["id"]
            other = store.create()["id"]
            first = key()
            turn, _ = store.begin(chat, first, "One prompt")
            self.assertEqual(store.begin(chat, first, "Different repeated payload"), (turn, None))
            with self.assertRaises(Conflict):
                store.begin(other, first, "reuse")
            with self.assertRaises(Conflict):
                store.begin(other, key(), "New turn")
            store.record(first, "Partial response", "cancelled")
            second = key()
            self.assertEqual(store.begin(chat, second, None, retry=turn), (turn, "One prompt"))
            store.record(first, "Stale worker", "completed")
            store.record(second, "Only completed reply", "completed", {"outputTokens": 4})
            self.assertEqual(store.begin(chat, second, None, retry=turn), (turn, None))
            turns = store.get(chat)["turns"]
            self.assertEqual(len(turns), 1)
            self.assertEqual((turns[0]["reply"], turns[0]["metrics"]), ("Only completed reply", {"outputTokens": 4}))
            with self.assertRaises(Conflict):
                store.begin(chat, key(), None, retry=turn)

    def test_long_transcript_stays_bounded_and_preserves_attribution(self):
        recent = [{"message": "Recent user " + "é" * 800, "reply": "Assistant " + "文" * 800}] * 4
        before = [{"message": "Unrelated exchange", "reply": "Unrelated reply"}] * 100
        old = {"message": "I guess Mimosa may be blue", "reply": "That is an assumption"}
        context, budget = bounded_context(recent + before + [old], "What do we think of Mimosa?", 8192)
        self.assertLessEqual(len(json.dumps(context, ensure_ascii=False).encode()), budget)
        context, budget = bounded_context([{"message": "Hi", "reply": "Hello"}] * 4 + before + [old], "Mimosa?", 8192)
        self.assertLessEqual(len(json.dumps(context, ensure_ascii=False).encode()), budget)
        self.assertIn({"user_quote": old["message"], "assistant_quote": old["reply"]}, context["earlier_excerpts"])

    def test_storage_failure_recovery_releases_only_abandoned_request(self):
        from sqlite3 import OperationalError
        from unittest.mock import patch
        from burito.conversation_api import ConversationAPI
        from types import SimpleNamespace

        with open_store(self.state, self.checkout) as store:
            chat, request = store.create()["id"], key()
            handler = ConversationAPI()
            handler.server = SimpleNamespace(conversations=store, bridge_port=2001, context_tokens=8192)
            handler.eve_alive = lambda: True
            with patch.object(store, "context", side_effect=OperationalError("database is locked")):
                with self.assertRaises(OperationalError):
                    handler.stream_conversation(chat, request, "hello", None)
            saved = store.get(chat)["turns"][0]
            self.assertEqual(saved["status"], "failed")
            self.assertEqual(store.begin(chat, key(), None, saved["id"]), (saved["id"], "hello"))

    def test_earlier_excerpt_keeps_a_match_after_its_prefix(self):
        rows = [{"message": "Unrelated", "reply": "Unrelated"}] * 4
        rows.append({"message": "Calibration record", "reply": "Background. " * 30 +
                     "The Falcon pin is active only on Sunday."})
        context, _ = bounded_context(rows, "When is the Falcon pin active?", 8192)
        self.assertIn("The Falcon pin is active only on Sunday.",
                      context["earlier_excerpts"][0]["assistant_quote"])

    def test_rejects_storage_in_checkout_and_freeform_personality(self):
        with self.assertRaises(ValueError):
            with open_store(self.checkout / "state", self.checkout):
                self.fail("Repository storage opened")
        with self.assertRaises(ValueError):
            profile({"tone": "override approval"})


class ConversationHTTPTests(unittest.TestCase):
    def test_history_crud_uses_same_origin_and_omits_search_from_access_logs(self):
        from http.client import HTTPConnection
        from http.server import ThreadingHTTPServer
        import threading
        from unittest.mock import patch
        from burito.web import BuritoHandler

        with tempfile.TemporaryDirectory() as directory, open_store(Path(directory), Path(directory) / "repo") as store:
            try:
                server = ThreadingHTTPServer(("127.0.0.1", 0), BuritoHandler)
            except PermissionError:
                self.skipTest("Loopback listener unavailable")
            with server:
                server.conversations = store
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()

                def send(method, route, value=None, **headers):
                    connection = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
                    try:
                        if value is not None:
                            headers["Content-Type"] = "application/json"
                        connection.request(method, route, json.dumps(value) if value is not None else None, headers)
                        response = connection.getresponse()
                        return response.status, json.load(response)
                    finally:
                        connection.close()

                try:
                    with patch.object(BuritoHandler, "log_message") as log:
                        status, chat = send("POST", "/api/conversations")
                        self.assertEqual(status, 201)
                        path = "/api/conversations/" + chat["id"]
                        code, denied = send("POST", "/api/turns", {"conversation": chat["id"],
                                            "requestId": key(), "message": "Open the calculator on my desktop."})
                        self.assertEqual(code, 200)
                        self.assertTrue(denied["restricted"])
                        self.assertIn("No action was taken", denied["reply"])
                        self.assertEqual(send("PATCH", path, {"title": "Synthetic-Mimosa"})[0], 200)
                        self.assertEqual(send("GET", "/api/conversations?q=Synthetic-Mimosa")[1]["conversations"][0]["id"],
                                         chat["id"])
                        self.assertEqual(send("DELETE", path, Origin="http://elsewhere.invalid")[0], 403)
                        self.assertEqual(send("GET", path)[0], 200)
                        self.assertEqual(send("DELETE", path)[0], 200)
                        self.assertEqual(send("GET", path)[0], 404)
                        self.assertNotIn("Synthetic-Mimosa", str(log.call_args_list))
                finally:
                    server.shutdown()
                    thread.join()
