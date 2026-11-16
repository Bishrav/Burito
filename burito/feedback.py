"""Explicit owner feedback for improving future Burito conversations."""

from datetime import datetime, timezone
import uuid

from .memory import Memory


RATINGS = ("useful", "correction", "not_useful")


class Feedback:
    def __init__(self, memory=None):
        self.memory = memory if memory is not None else Memory()

    def _connect(self):
        connection = self.memory._connect()
        connection.execute("""CREATE TABLE IF NOT EXISTS owner_feedback (
            id TEXT PRIMARY KEY,
            rating TEXT NOT NULL CHECK(rating IN ('useful', 'correction', 'not_useful')),
            note TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""")
        return connection

    def add(self, rating, note):
        if rating not in RATINGS:
            raise ValueError("Choose useful, correction, or not_useful")
        note = note.strip()
        if not note or len(note) > 2000:
            raise ValueError("Feedback note must contain 1 to 2000 characters")
        identifier = str(uuid.uuid4())
        connection = self._connect()
        try:
            with connection:
                connection.execute(
                    "INSERT INTO owner_feedback VALUES (?, ?, ?, ?)",
                    (identifier, rating, note, datetime.now(timezone.utc).isoformat()),
                )
        finally:
            connection.close()
        return identifier

    def list(self, limit=50):
        connection = self._connect()
        try:
            return [dict(row) for row in connection.execute(
                "SELECT * FROM owner_feedback ORDER BY created_at DESC, id DESC LIMIT ?",
                (limit,),
            )]
        finally:
            connection.close()

    def forget(self, identifier):
        connection = self._connect()
        try:
            with connection:
                connection.execute("PRAGMA secure_delete = ON")
                return connection.execute(
                    "DELETE FROM owner_feedback WHERE id = ?", (identifier,)
                ).rowcount == 1
        finally:
            connection.close()
