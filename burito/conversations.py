"""Private web conversation storage and bounded context construction."""

from contextlib import closing, contextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import threading
import uuid

MAX_MESSAGE_BYTES = 2400
OPTIONS = {
    "tone": ("adaptive", "warm", "direct", "neutral"),
    "length": ("adaptive", "brief", "detailed"),
    "formality": ("adaptive", "casual", "formal"),
    "depth": ("adaptive", "introductory", "technical"),
    "humor": ("off", "light"),
    "style": ("natural", "structured", "coaching"),
}
DEFAULTS = {name: values[0] for name, values in OPTIONS.items()}


class Conflict(ValueError):
    pass


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{32}", value):
        raise ValueError("Invalid conversation or request ID.")
    return value


def profile(value):
    if not isinstance(value, dict) or set(value) - DEFAULTS.keys():
        raise ValueError("Invalid personality configuration.")
    for name, option in value.items():
        if option not in OPTIONS[name]:
            raise ValueError(f"Invalid {name} setting.")
    return {**DEFAULTS, **value}


def default_directory():
    root = Path(os.environ.get("XDG_STATE_HOME") or (Path.home() / ".local/state"))
    return root / "burito" / "conversations"


def _git_checkout(directory):
    metadata = directory / ".git"
    return metadata.is_file() or (metadata / "HEAD").is_file()


@contextmanager
def open_store(directory, checkout):
    directory = Path(directory)
    destination = directory.resolve()
    if (not directory.is_absolute() or destination.is_relative_to(checkout.resolve())
            or any(_git_checkout(parent) for parent in (destination, *destination.parents))):
        raise ValueError("Conversation data requires an absolute directory outside the checkout.")
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if directory.is_symlink() or directory.stat().st_uid != os.getuid() or directory.stat().st_mode & 0o077:
        raise ValueError("Conversation directory must be a private, owned directory (mode 700).")
    fd = os.open(directory / ".burito-conversations.lock", os.O_CREAT | os.O_NOFOLLOW | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError("This conversation directory is already in use.") from error
        yield Conversations(directory)
    finally:
        os.close(fd)


class Conversations:
    def __init__(self, directory):
        self._abandoned = set()
        self._recovery_lock = threading.Lock()
        self.path = Path(directory) / "conversations.sqlite3"
        fd = os.open(self.path, os.O_CREAT | os.O_NOFOLLOW | os.O_RDWR, 0o600)
        try:
            info = os.fstat(fd)
            if info.st_uid != os.getuid() or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise ValueError("Invalid conversation database file.")
            os.fchmod(fd, 0o600)
        finally:
            os.close(fd)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY, title TEXT NOT NULL,
                    updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS turns (
                    seq INTEGER PRIMARY KEY, id TEXT NOT NULL UNIQUE,
                    conversation TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    message TEXT NOT NULL, reply TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL, metrics TEXT,
                    active_request TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS turns_by_conversation ON turns(conversation, seq);
                CREATE UNIQUE INDEX IF NOT EXISTS one_active_turn ON turns((1)) WHERE status = 'running';
                CREATE TABLE IF NOT EXISTS requests (
                    id TEXT PRIMARY KEY, turn_id TEXT NOT NULL REFERENCES turns(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS preferences (id INTEGER PRIMARY KEY CHECK(id=1), value TEXT NOT NULL);
            """)
            db.execute("UPDATE turns SET status='interrupted' WHERE status='running'")

    @contextmanager
    def connect(self):
        with closing(sqlite3.connect(self.path, timeout=5)) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("PRAGMA secure_delete=ON")
            with db:
                yield db

    def _require(self, db, conversation):
        row = db.execute("SELECT * FROM conversations WHERE id=?", (identifier(conversation),)).fetchone()
        if row is None:
            raise LookupError("Conversation not found.")
        return dict(row)

    def create(self):
        conversation = uuid.uuid4().hex
        with self.connect() as db:
            db.execute("INSERT INTO conversations(id,title) VALUES(?,?)", (conversation, "New chat"))
            return self._require(db, conversation)

    def list(self, query="", offset=0):
        if len(query) > 120:
            raise ValueError("Search is too long.")
        with self.connect() as db:
            return [dict(row) for row in db.execute("""
                SELECT c.* FROM conversations c WHERE instr(lower(c.title), lower(?)) > 0
                   OR EXISTS (SELECT 1 FROM turns t WHERE t.conversation=c.id
                              AND (instr(lower(t.message), lower(?)) > 0 OR instr(lower(t.reply), lower(?)) > 0))
                ORDER BY c.updated DESC, c.rowid DESC LIMIT 51 OFFSET ?
            """, (query, query, query, offset))]

    def get(self, conversation, before=None):
        self.recover_abandoned()
        with self.connect() as db:
            result = self._require(db, conversation)
            rows = db.execute("""
                SELECT seq,id,message,reply,status,metrics,active_request AS requestId FROM turns
                WHERE conversation=? AND (? IS NULL OR seq < ?) ORDER BY seq DESC LIMIT 51
            """, (conversation, before, before)).fetchall()
            result["before"] = rows[49]["seq"] if len(rows) > 50 else None
            result["turns"] = [dict(row) for row in reversed(rows[:50])]
            for turn in result["turns"]:
                turn["metrics"] = json.loads(turn["metrics"]) if turn["metrics"] else None
            return result

    def rename(self, conversation, title):
        if not isinstance(title, str) or not 0 < len(title.strip()) <= 100:
            raise ValueError("Use a title of up to 100 characters.")
        with self.connect() as db:
            self._require(db, conversation)
            db.execute("UPDATE conversations SET title=? WHERE id=?", (title.strip(), conversation))
            return self._require(db, conversation)

    def delete(self, conversation):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._require(db, conversation)
            if db.execute("SELECT 1 FROM turns WHERE conversation=? AND status='running'", (conversation,)).fetchone():
                raise Conflict("Stop this reply before deleting the conversation.")
            db.execute("DELETE FROM conversations WHERE id=?", (conversation,))

    def settings(self, value=None):
        with self.connect() as db:
            if value is not None:
                settings = profile(value)
                db.execute("INSERT OR REPLACE INTO preferences VALUES(1,?)", (json.dumps(settings),))
                return settings
            row = db.execute("SELECT value FROM preferences WHERE id=1").fetchone()
            return json.loads(row[0]) if row else DEFAULTS.copy()

    def abandon(self, request_id):
        with self._recovery_lock:
            self._abandoned.add(request_id)

    def recover_abandoned(self):
        with self._recovery_lock:
            for request_id in tuple(self._abandoned):
                with self.connect() as db:
                    db.execute("UPDATE turns SET status='failed' WHERE active_request=? AND status='running'",
                               (request_id,))
                self._abandoned.remove(request_id)

    def begin(self, conversation, request_id, message, retry=None):
        identifier(request_id)
        self.recover_abandoned()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            chat = self._require(db, conversation)
            duplicate = db.execute("""
                SELECT t.id, t.status, t.conversation FROM requests r JOIN turns t ON t.id=r.turn_id WHERE r.id=?
            """, (request_id,)).fetchone()
            if duplicate:
                if duplicate["conversation"] != conversation:
                    raise Conflict("Request ID belongs to another conversation.")
                return duplicate["id"], None
            if db.execute("SELECT 1 FROM turns WHERE status='running'").fetchone():
                raise Conflict("A reply is already running. Wait or stop it first.")
            last = db.execute("SELECT * FROM turns WHERE conversation=? ORDER BY seq DESC LIMIT 1", (conversation,)).fetchone()
            if retry is not None:
                if not last or last["id"] != retry or last["status"] not in {"failed", "cancelled", "interrupted"}:
                    raise Conflict("Only the latest failed or stopped turn can be retried.")
                turn_id, message = last["id"], last["message"]
                db.execute("UPDATE turns SET reply='',status='running',metrics=NULL,active_request=? WHERE id=?",
                           (request_id, turn_id))
            else:
                if not isinstance(message, str) or not message.strip() or len(message.encode()) > MAX_MESSAGE_BYTES:
                    raise ValueError("Enter a message of up to 2,400 UTF-8 bytes.")
                turn_id, message = uuid.uuid4().hex, message.strip()
                db.execute("INSERT INTO turns(id,conversation,message,status,active_request) VALUES(?,?,?,'running',?)",
                           (turn_id, conversation, message, request_id))
                if not last and chat["title"] == "New chat":
                    title = " ".join(message.split())
                    title = title[:59].rstrip() + "…" if len(title) > 60 else title
                    db.execute("UPDATE conversations SET title=? WHERE id=?", (title, conversation))
            db.execute("INSERT INTO requests VALUES(?,?)", (request_id, turn_id))
            db.execute("UPDATE conversations SET updated=CURRENT_TIMESTAMP WHERE id=?", (conversation,))
            return turn_id, message

    def running_request(self, conversation):
        with self.connect() as db:
            self._require(db, conversation)
            row = db.execute("SELECT active_request FROM turns WHERE conversation=? AND status='running'",
                             (conversation,)).fetchone()
            return row[0] if row else None

    def record(self, request_id, reply, status="running", metrics=None):
        with self.connect() as db:
            db.execute("UPDATE turns SET reply=?,status=?,metrics=? WHERE active_request=? AND status='running'",
                       (reply, status, json.dumps(metrics) if metrics else None, request_id))

    def context(self, conversation, message, context_tokens):
        with self.connect() as db:
            rows = db.execute("""
                SELECT message,reply FROM turns WHERE conversation=? AND status='completed'
                ORDER BY seq DESC LIMIT 120
            """, (conversation,)).fetchall()
        return bounded_context(rows, message, context_tokens)


def bounded_context(rows, message, context_tokens):
    """Keep recent exchanges and quoted relevant older turns within a byte budget."""
    budget = min(2500, max(450, context_tokens // 3 - len(message.encode()) // 3))
    words = set(re.findall(r"\w{4,}", message.casefold()))
    recent, earlier = [], []
    for row in rows[:4]:
        recent.append({"user": row["message"][:240], "assistant": row["reply"][:340]})
    ranked = sorted(
        rows[4:], key=lambda row: -len(words & set(re.findall(r"\w{4,}", (row["message"] + " " + row["reply"]).casefold())))
    )
    def excerpt(value, limit):
        for match in re.finditer(r"\w{4,}", value):
            if match[0].casefold() in words:
                start = max(0, match.start() - limit // 3)
                return value[start:start + limit]
        return value[:limit]

    for row in ranked[:3]:
        earlier.append({"user_quote": excerpt(row["message"], 100),
                        "assistant_quote": excerpt(row["reply"], 140)})
    data = {"recent": list(reversed(recent)), "earlier_excerpts": earlier}
    while len(json.dumps(data, ensure_ascii=False).encode()) > budget:
        if len(data["earlier_excerpts"]) > 1:
            data["earlier_excerpts"].pop()
        elif len(data["recent"]) > 1:
            data["recent"].pop(0)
        elif data["earlier_excerpts"]:
            data["earlier_excerpts"].pop()
        else:
            data["recent"].pop(0)
    return data, budget
