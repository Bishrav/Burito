"""Owner-supplied facts, kept outside the source checkout by default."""

import os
from pathlib import Path
import sqlite3
import uuid
from datetime import datetime, timezone


def data_directory():
    override = os.environ.get("BURITO_DATA_DIR")
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local/share")
    path = Path(override) if override else Path(base) / "burito"
    if not path.is_absolute():
        raise ValueError("Burito data directory must be an absolute path")
    return path


class Memory:
    def __init__(self, directory=None):
        self.directory = Path(directory) if directory is not None else data_directory()
        self.path = self.directory / "memory.sqlite3"

    def _connect(self):
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.directory.is_symlink() or self.directory.stat().st_uid != os.getuid():
            raise ValueError("Memory directory must be owned by you and not a symlink")
        self.directory.chmod(0o700)
        # O_NOFOLLOW rejects a pre-existing symlink at the database path.
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            if os.fstat(fd).st_uid != os.getuid():
                raise ValueError("Memory database must be owned by you")
            os.fchmod(fd, 0o600)
        finally:
            os.close(fd)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("""CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY, content TEXT NOT NULL, source TEXT NOT NULL,
            created_at TEXT NOT NULL, status TEXT NOT NULL CHECK(status = 'confirmed')
        )""")
        return connection

    def initialize(self):
        connection = self._connect()
        connection.close()
        return self.path

    def remember(self, content, source="owner"):
        content, source = content.strip(), source.strip()
        if not content or not source:
            raise ValueError("Memory content and source must not be empty")
        if len(content) > 20000 or len(source) > 200:
            raise ValueError("Memory content or source exceeds its size limit")
        identifier = str(uuid.uuid4())
        connection = self._connect()
        try:
            with connection:
                connection.execute(
                    "INSERT INTO memories VALUES (?, ?, ?, ?, 'confirmed')",
                    (identifier, content, source, datetime.now(timezone.utc).isoformat()),
                )
        finally:
            connection.close()
        return identifier

    def list(self):
        connection = self._connect()
        try:
            return [dict(row) for row in connection.execute(
                "SELECT * FROM memories ORDER BY created_at, id"
            )]
        finally:
            connection.close()

    def forget(self, identifier):
        connection = self._connect()
        try:
            with connection:
                connection.execute("PRAGMA secure_delete = ON")
                return connection.execute(
                    "DELETE FROM memories WHERE id = ?", (identifier,)
                ).rowcount == 1
        finally:
            connection.close()

    def correct(self, identifier, content):
        content = content.strip()
        if not content or len(content) > 20000:
            raise ValueError("Corrected memory must contain 1 to 20000 characters")
        connection = self._connect()
        try:
            with connection:
                connection.execute("PRAGMA secure_delete = ON")
                return connection.execute(
                    "UPDATE memories SET content = ?, source = 'owner correction' WHERE id = ?",
                    (content, identifier),
                ).rowcount == 1
        finally:
            connection.close()

    def backup(self, destination):
        """Produce a consistent SQLite snapshot; never replace an existing file."""
        destination = Path(destination)
        if not destination.is_absolute():
            raise ValueError("Backup destination must be an absolute path")
        # The parent must already exist: do not create folders on an unmounted disk.
        fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        source = target = None
        try:
            source = self._connect()
            target = sqlite3.connect(destination)
            source.backup(target)
        except BaseException:
            if target is not None:
                target.close()
                target = None
            destination.unlink(missing_ok=True)
            raise
        finally:
            if target is not None:
                target.close()
            if source is not None:
                source.close()
        return destination
