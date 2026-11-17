"""Private, searchable library for owner-selected Markdown and plain-text files."""

import hashlib
from pathlib import Path
import re
from datetime import datetime, timezone
import uuid

from .memory import Memory

MAX_FILE_BYTES = 20 * 1024 * 1024
SUPPORTED = {".md", ".markdown", ".txt", ".rst"}
CHUNK_SIZE = 1800
OVERLAP = 240
QUERY_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "according", "about", "by", "cite",
    "do", "does", "for", "from", "how", "i", "in", "is", "it", "me", "my",
    "of", "on", "or", "please", "show", "source", "tell", "that", "the",
    "this", "to", "what", "when", "where", "which", "who", "why", "with",
    "would", "you", "your", "imported",
}


class Knowledge:
    def __init__(self, memory=None):
        self.memory = memory or Memory()

    def _connect(self):
        connection = self.memory._connect()
        connection.execute("""CREATE TABLE IF NOT EXISTS knowledge_documents (
            id TEXT PRIMARY KEY, sha256 TEXT NOT NULL UNIQUE, source_path TEXT NOT NULL,
            title TEXT NOT NULL, imported_at TEXT NOT NULL, byte_size INTEGER NOT NULL
        )""")
        connection.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_chunks USING fts5(
            document_id UNINDEXED, source_path UNINDEXED, chunk_index UNINDEXED,
            content, tokenize='unicode61'
        )""")
        return connection

    @staticmethod
    def _chunks(text):
        text = "\n".join(line.rstrip() for line in text.replace("\x00", "").splitlines()).strip()
        result = []
        start = 0
        while start < len(text):
            end = min(len(text), start + CHUNK_SIZE)
            if end < len(text):
                boundary = text.rfind("\n", start + CHUNK_SIZE // 2, end)
                if boundary > start:
                    end = boundary
            chunk = text[start:end].strip()
            if chunk:
                result.append(chunk)
            if end >= len(text):
                break
            start = max(end - OVERLAP, start + 1)
        return result

    def add(self, source):
        path = Path(source).expanduser()
        if path.is_symlink() or not path.is_file():
            raise ValueError("Choose a regular, non-symlink file")
        if path.suffix.lower() not in SUPPORTED:
            raise ValueError("First library milestone supports .md, .markdown, .txt, and .rst files")
        size = path.stat().st_size
        if size > MAX_FILE_BYTES:
            raise ValueError("File exceeds the 20 MiB import limit")
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        text = raw.decode("utf-8-sig", errors="strict")
        chunks = self._chunks(text)
        if not chunks:
            raise ValueError("File contains no searchable text")
        connection = self._connect()
        try:
            existing = connection.execute("SELECT id, source_path FROM knowledge_documents WHERE sha256=?", (digest,)).fetchone()
            if existing:
                return {"id": existing["id"], "duplicate": True, "source_path": existing["source_path"]}
            identifier = str(uuid.uuid4())
            canonical = str(path.resolve())
            title = next((line.lstrip("# ").strip() for line in text.splitlines()
                          if line.strip() and not line.strip().startswith("<!--")), path.stem)
            with connection:
                connection.execute("INSERT INTO knowledge_documents VALUES (?, ?, ?, ?, ?, ?)",
                                   (identifier, digest, canonical, title[:500], datetime.now(timezone.utc).isoformat(), size))
                connection.executemany("INSERT INTO knowledge_chunks(document_id, source_path, chunk_index, content) VALUES (?, ?, ?, ?)",
                                       [(identifier, canonical, index, chunk) for index, chunk in enumerate(chunks)])
            return {"id": identifier, "duplicate": False, "title": title[:500], "source_path": canonical,
                    "chunks": len(chunks), "bytes": size}
        finally:
            connection.close()

    def list(self):
        connection = self._connect()
        try:
            return [dict(row) for row in connection.execute(
                "SELECT d.id,d.title,d.source_path,d.imported_at,d.byte_size,COUNT(c.rowid) AS chunks "
                "FROM knowledge_documents d LEFT JOIN knowledge_chunks c ON c.document_id=d.id "
                "GROUP BY d.id ORDER BY d.imported_at DESC")]
        finally:
            connection.close()

    def search(self, query, limit=5):
        # Treat natural-language questions as a bag of useful words, not a
        # phrase that must contain every prompt token verbatim.
        terms = [term for term in re.findall(r"[^\W_]+", query.casefold(), flags=re.UNICODE)
                 if len(term) > 1 and term not in QUERY_STOPWORDS]
        if not terms:
            raise ValueError("Enter one or more search terms")
        if len(terms) > 16:
            raise ValueError("Use at most 16 search terms")
        expression = " OR ".join('"' + term.replace('"', '""') + '"' for term in terms)
        connection = self._connect()
        try:
            rows = connection.execute("""SELECT d.title, c.source_path, c.content,
                bm25(knowledge_chunks) AS score
                FROM knowledge_chunks c JOIN knowledge_documents d ON d.id=c.document_id
                WHERE knowledge_chunks MATCH ? ORDER BY score LIMIT ?""", (expression, max(1, min(limit, 10)))).fetchall()
            return [dict(row) for row in rows]
        finally:
            connection.close()

    def forget(self, identifier):
        connection = self._connect()
        try:
            with connection:
                connection.execute("DELETE FROM knowledge_chunks WHERE document_id=?", (identifier,))
                return connection.execute("DELETE FROM knowledge_documents WHERE id=?", (identifier,)).rowcount == 1
        finally:
            connection.close()
