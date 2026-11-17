"""Owner-confirmed terminology stored privately alongside Burito memory."""

from datetime import datetime, timezone
import re
import uuid

from .memory import Memory


def _key(term):
    return " ".join(re.findall(r"[^\W_]+", term.casefold(), flags=re.UNICODE))


class Glossary:
    def __init__(self, memory=None):
        self.memory = memory or Memory()

    def _connect(self):
        connection = self.memory._connect()
        connection.execute("""CREATE TABLE IF NOT EXISTS glossary_terms (
            id TEXT PRIMARY KEY, term_key TEXT NOT NULL UNIQUE, term TEXT NOT NULL,
            definition TEXT NOT NULL, source TEXT NOT NULL, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""")
        return connection

    def define(self, term, definition, source="owner"):
        term, definition, source = term.strip(), definition.strip(), source.strip()
        if not term or len(term) > 160 or not definition or len(definition) > 4000:
            raise ValueError("Term must be 1-160 characters and definition 1-4000 characters")
        if not source or len(source) > 200:
            raise ValueError("Definition source must be 1-200 characters")
        key = _key(term)
        if not key:
            raise ValueError("Term must contain letters or numbers")
        now, identifier = datetime.now(timezone.utc).isoformat(), str(uuid.uuid4())
        connection = self._connect()
        try:
            old = connection.execute("SELECT id,definition FROM glossary_terms WHERE term_key=?", (key,)).fetchone()
            if old and old["definition"] == definition:
                return {"id": old["id"], "term": term, "duplicate": True}
            if old:
                with connection:
                    connection.execute("UPDATE glossary_terms SET term=?, definition=?, source=?, updated_at=? WHERE id=?",
                                       (term, definition, source, now, old["id"]))
                return {"id": old["id"], "term": term, "updated": True}
            with connection:
                connection.execute("INSERT INTO glossary_terms VALUES (?, ?, ?, ?, ?, ?, ?)",
                                   (identifier, key, term, definition, source, now, now))
            return {"id": identifier, "term": term, "duplicate": False}
        finally:
            connection.close()

    def list(self):
        connection = self._connect()
        try:
            return [dict(row) for row in connection.execute(
                "SELECT id,term,definition,source,created_at,updated_at FROM glossary_terms ORDER BY term_key")]
        finally:
            connection.close()

    def search(self, query, limit=8):
        terms = set(_key(query).split())
        if not terms:
            return []
        connection = self._connect()
        try:
            rows = [dict(row) for row in connection.execute(
                "SELECT id,term,definition,source FROM glossary_terms")]
            ranked = []
            for row in rows:
                corpus = set(_key(row["term"] + " " + row["definition"]).split())
                overlap = len(terms & corpus)
                if overlap:
                    ranked.append((overlap, row))
            ranked.sort(key=lambda item: (-item[0], item[1]["term"].casefold()))
            return [row for _, row in ranked[:max(1, min(limit, 12))]]
        finally:
            connection.close()

    def forget(self, identifier):
        connection = self._connect()
        try:
            with connection:
                return connection.execute("DELETE FROM glossary_terms WHERE id=?", (identifier,)).rowcount == 1
        finally:
            connection.close()
