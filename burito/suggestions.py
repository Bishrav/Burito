"""Private, owner-reviewed suggestions with provenance and duplicate suppression."""

from datetime import datetime, timezone
import hashlib
import unicodedata
import uuid

from .memory import Memory


EVIDENCE_SOURCES = ("owner_statement", "activity_record", "pc_event", "other")
REVIEW_STATES = ("pending", "accepted", "dismissed")


def normalize(text):
    """Normalize whitespace, case, and punctuation for exact duplicate checks."""
    text = unicodedata.normalize("NFKC", text).casefold()
    text = "".join(character if character.isalnum() else " " for character in text)
    return " ".join(text.split())


class Suggestions:
    def __init__(self, memory=None):
        self.memory = memory if memory is not None else Memory()

    def _connect(self):
        connection = self.memory._connect()
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS suggestions (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                normalized_sha256 TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL CHECK(status IN ('pending', 'accepted', 'dismissed')),
                review_note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                reviewed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS suggestion_evidence (
                id TEXT PRIMARY KEY,
                suggestion_id TEXT NOT NULL,
                source TEXT NOT NULL CHECK(source IN ('owner_statement', 'activity_record', 'pc_event', 'other')),
                detail TEXT NOT NULL,
                reference TEXT NOT NULL DEFAULT '',
                added_at TEXT NOT NULL
            );
        """)
        return connection

    @staticmethod
    def _record(connection, row):
        record = dict(row)
        record["evidence"] = [dict(item) for item in connection.execute(
            "SELECT source, detail, reference, added_at FROM suggestion_evidence "
            "WHERE suggestion_id = ? ORDER BY added_at, id", (record["id"],)
        )]
        record.pop("normalized_sha256", None)
        return record

    def add(self, content, source, detail, reference=""):
        content, detail, reference = content.strip(), detail.strip(), reference.strip()
        if not content or len(content) > 4000:
            raise ValueError("Suggestion must contain 1 to 4000 characters")
        if source not in EVIDENCE_SOURCES:
            raise ValueError("Choose owner_statement, activity_record, pc_event, or other")
        if not detail or len(detail) > 2000:
            raise ValueError("Evidence detail must contain 1 to 2000 characters")
        if len(reference) > 500:
            raise ValueError("Evidence reference must be at most 500 characters")
        normalized = normalize(content)
        if not normalized:
            raise ValueError("Suggestion must contain letters or numbers")
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        identifier = str(uuid.uuid4())
        evidence_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        connection = self._connect()
        try:
            with connection:
                connection.execute(
                    "INSERT OR IGNORE INTO suggestions "
                    "(id, content, normalized_sha256, status, created_at) VALUES (?, ?, ?, 'pending', ?)",
                    (identifier, content, digest, now),
                )
                row = connection.execute(
                    "SELECT * FROM suggestions WHERE normalized_sha256 = ?", (digest,)
                ).fetchone()
                connection.execute(
                    "INSERT INTO suggestion_evidence VALUES (?, ?, ?, ?, ?, ?)",
                    (evidence_id, row["id"], source, detail, reference, now),
                )
                result = self._record(connection, row)
                result["duplicate"] = row["id"] != identifier
                return result
        finally:
            connection.close()

    def list(self, status=None, limit=50):
        if status is not None and status not in REVIEW_STATES:
            raise ValueError("Choose pending, accepted, or dismissed")
        connection = self._connect()
        try:
            if status is None:
                rows = connection.execute(
                    "SELECT * FROM suggestions ORDER BY created_at DESC, id DESC LIMIT ?", (limit,)
                )
            else:
                rows = connection.execute(
                    "SELECT * FROM suggestions WHERE status = ? "
                    "ORDER BY created_at DESC, id DESC LIMIT ?", (status, limit)
                )
            return [self._record(connection, row) for row in rows]
        finally:
            connection.close()

    def active(self, limit=5):
        """Return recent pending/accepted records for explicit chat context."""
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM suggestions WHERE status IN ('pending', 'accepted') "
                "ORDER BY created_at DESC, id DESC LIMIT ?", (limit,)
            )
            return [self._record(connection, row) for row in rows]
        finally:
            connection.close()

    def review(self, identifier, status, note=""):
        if status not in REVIEW_STATES:
            raise ValueError("Choose pending, accepted, or dismissed")
        note = note.strip()
        if len(note) > 2000:
            raise ValueError("Review note must be at most 2000 characters")
        connection = self._connect()
        try:
            with connection:
                reviewed_at = None if status == "pending" else datetime.now(timezone.utc).isoformat()
                return connection.execute(
                    "UPDATE suggestions SET status = ?, review_note = ?, reviewed_at = ? WHERE id = ?",
                    (status, note, reviewed_at, identifier),
                ).rowcount == 1
        finally:
            connection.close()

    def forget(self, identifier):
        connection = self._connect()
        try:
            with connection:
                connection.execute("PRAGMA secure_delete = ON")
                connection.execute("DELETE FROM suggestion_evidence WHERE suggestion_id = ?", (identifier,))
                return connection.execute(
                    "DELETE FROM suggestions WHERE id = ?", (identifier,)
                ).rowcount == 1
        finally:
            connection.close()
