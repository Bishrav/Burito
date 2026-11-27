"""Owner-supplied facts, kept outside the source checkout by default."""

import hashlib
import json
import os
from pathlib import Path
import math
import re
import sqlite3
import stat
import subprocess
import shutil
import uuid
from datetime import datetime, timezone
from .brain_manifest import (DATABASE_SCHEMA_VERSION, ensure as ensure_brain_manifest,
                             record_database_schema)

BRAIN_MOUNT = Path("/mnt/burito-brain")
BRAIN_UUID = "9428a980-24a6-45b2-a0a6-5e057c819406"
BRAIN_DATA = BRAIN_MOUNT / "memory"
MEMORY_CATEGORIES = frozenset({"semantic", "episodic", "procedural", "personal",
                               "preference", "project", "prospective", "experience",
                               "failure", "research"})
VERIFICATION_STATES = frozenset({"owner_statement", "direct_observation",
                                 "external_research", "model_inference",
                                 "independently_verified"})
SEARCH_STOPWORDS = frozenset({"a", "about", "after", "all", "also", "an", "and", "are",
    "as", "at", "be", "because", "before", "but", "by", "can", "could", "did", "do",
    "does", "doing", "for", "from", "had", "has", "have", "how", "i", "if", "in", "into",
    "is", "it", "me", "my", "of", "on", "or", "our", "please", "should", "that",
    "the", "their", "them", "there", "these", "they", "this", "to", "was", "we",
    "were", "what", "when", "where", "which", "who", "why", "will", "with", "would",
    "you", "your"})


class _PinnedConnection(sqlite3.Connection):
    def close(self):
        directory_fd = getattr(self, "directory_fd", None)
        self.directory_fd = None
        try:
            super().close()
        finally:
            if directory_fd is not None:
                os.close(directory_fd)


def brain_status():
    try:
        result = subprocess.run(
            ["findmnt", "--mountpoint", str(BRAIN_MOUNT), "--noheadings", "--output", "UUID,FSTYPE,OPTIONS"],
            capture_output=True, text=True, timeout=3, check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return "unavailable"
    fields = result.stdout.split()
    if len(fields) != 3:
        return "unavailable"
    if fields[0] != BRAIN_UUID:
        return "wrong_identity"
    if fields[1] != "ext4":
        return "unsupported_filesystem"
    if "rw" not in fields[2].split(","):
        return "read_only"
    try:
        data = BRAIN_DATA.lstat()
    except FileNotFoundError:
        return "data_directory_missing"
    except OSError:
        return "unavailable"
    if not stat.S_ISDIR(data.st_mode) or stat.S_ISLNK(data.st_mode):
        return "invalid_data_directory"
    if data.st_uid != os.getuid():
        return "wrong_owner"
    if not os.access(BRAIN_DATA, os.W_OK | os.X_OK):
        return "not_writable"
    try:
        if shutil.disk_usage(BRAIN_MOUNT).free == 0:
            return "full"
    except OSError:
        return "unavailable"
    return "ready"


def brain_available():
    return brain_status() == "ready"


def _normalize(content):
    return " ".join(content.split()).casefold()


def _upgrade_schema(connection):
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    if version not in (0, 1, DATABASE_SCHEMA_VERSION):
        raise ValueError(f"Unsupported memory database schema version: {version}")
    if version == DATABASE_SCHEMA_VERSION:
        return False
    connection.execute("BEGIN IMMEDIATE")
    try:
        if version == 0:
            connection.execute("""CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY, content TEXT NOT NULL, source TEXT NOT NULL,
                created_at TEXT NOT NULL, status TEXT NOT NULL CHECK(status = 'confirmed')
            )""")
            connection.execute("PRAGMA user_version=1")
        connection.execute("""ALTER TABLE memories ADD COLUMN category TEXT NOT NULL
            DEFAULT 'semantic' CHECK(category IN
            ('semantic','episodic','procedural','personal','preference','project',
             'prospective','experience','failure','research'))""")
        connection.execute("ALTER TABLE memories ADD COLUMN confidence REAL DEFAULT NULL CHECK(confidence IS NULL OR (confidence >= 0 AND confidence <= 1))")
        connection.execute("""ALTER TABLE memories ADD COLUMN verification TEXT NOT NULL
            DEFAULT 'owner_statement' CHECK(verification IN
            ('owner_statement','direct_observation','external_research',
             'model_inference','independently_verified'))""")
        connection.execute("ALTER TABLE memories ADD COLUMN claim_key TEXT")
        connection.execute("ALTER TABLE memories ADD COLUMN retention_policy TEXT NOT NULL DEFAULT 'owner_controlled'")
        connection.execute("ALTER TABLE memories ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''")
        connection.execute("ALTER TABLE memories ADD COLUMN active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1))")
        connection.execute("UPDATE memories SET updated_at=created_at WHERE updated_at=''")
        connection.execute("CREATE INDEX memories_category_active ON memories(category,active)")
        connection.execute("""CREATE TABLE memory_revisions (
            id INTEGER PRIMARY KEY, memory_id TEXT NOT NULL, revision INTEGER NOT NULL,
            content TEXT NOT NULL, source TEXT NOT NULL, category TEXT NOT NULL,
            confidence REAL, verification TEXT NOT NULL, claim_key TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL, recorded_at TEXT NOT NULL,
            UNIQUE(memory_id,revision),
            FOREIGN KEY(memory_id) REFERENCES memories(id) ON DELETE CASCADE
        )""")
        connection.execute("""CREATE TABLE memory_conflicts (
            id INTEGER PRIMARY KEY, left_id TEXT NOT NULL, right_id TEXT NOT NULL,
            reason TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN
                ('unresolved','resolved','dismissed','superseded')),
            created_at TEXT NOT NULL, resolved_at TEXT,
            CHECK(left_id <> right_id), UNIQUE(left_id,right_id),
            FOREIGN KEY(left_id) REFERENCES memories(id) ON DELETE CASCADE,
            FOREIGN KEY(right_id) REFERENCES memories(id) ON DELETE CASCADE
        )""")
        connection.execute("CREATE INDEX memory_conflicts_status ON memory_conflicts(status)")
        connection.execute(f"PRAGMA user_version={DATABASE_SCHEMA_VERSION}")
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    return True


def data_directory():
    override = os.environ.get("BURITO_DATA_DIR")
    path = Path(override) if override else BRAIN_DATA
    if not path.is_absolute():
        raise ValueError("Burito data directory must be an absolute path")
    return path


class Memory:
    def __init__(self, directory=None):
        self.directory = Path(directory) if directory is not None else data_directory()
        self.path = self.directory / "memory.sqlite3"

    def _connect(self):
        permanent = self.directory.is_relative_to(BRAIN_MOUNT)
        directory_fd = None
        if permanent:
            relative_directory = self.directory.relative_to(BRAIN_MOUNT)
            if ".." in relative_directory.parts:
                raise ValueError("Burito Brain data path cannot escape its mount")
            if not brain_available():
                raise ValueError("Burito Brain drive is unavailable or has the wrong identity; no fallback database was opened.")
            root_fd = os.open(BRAIN_MOUNT, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            current_fd = root_fd
            try:
                for part in relative_directory.parts:
                    child_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                       dir_fd=current_fd)
                    if current_fd != root_fd:
                        os.close(current_fd)
                    current_fd = child_fd
                directory_fd = current_fd
                current_fd = root_fd
                if os.fstat(directory_fd).st_uid != os.getuid() or not brain_available():
                    os.close(directory_fd)
                    directory_fd = None
                    raise ValueError("Burito Brain drive changed during connection; no fallback database was opened.")
                try:
                    os.stat("memory.sqlite3", dir_fd=directory_fd, follow_symlinks=False)
                    database_exists = True
                except FileNotFoundError:
                    database_exists = False
                ensure_brain_manifest(root_fd, BRAIN_UUID, database_exists)
            except BaseException:
                if current_fd != root_fd:
                    os.close(current_fd)
                if directory_fd is not None:
                    os.close(directory_fd)
                raise
            finally:
                os.close(root_fd)
            database_path = f"/proc/self/fd/{directory_fd}/memory.sqlite3"
        else:
            self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            database_path = self.path
        if not permanent and (self.directory.is_symlink() or self.directory.stat().st_uid != os.getuid()):
            raise ValueError("Memory directory must be owned by you and not a symlink")
        # O_NOFOLLOW rejects a pre-existing symlink at the database path.
        try:
            fd = os.open("memory.sqlite3" if permanent else self.path,
                         os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW,
                         0o600, dir_fd=directory_fd)
            if not stat.S_ISREG(os.fstat(fd).st_mode) or os.fstat(fd).st_uid != os.getuid():
                raise ValueError("Memory database must be owned by you")
            os.fchmod(fd, 0o600)
        except BaseException:
            if directory_fd is not None:
                os.close(directory_fd)
            raise
        finally:
            if "fd" in locals():
                os.close(fd)
        try:
            if permanent:
                connection = sqlite3.connect(database_path, factory=_PinnedConnection)
                connection.directory_fd = directory_fd
                directory_fd = None
            else:
                connection = sqlite3.connect(database_path)
        except BaseException:
            if directory_fd is not None:
                os.close(directory_fd)
            raise
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys=ON")
            _upgrade_schema(connection)
            if permanent:
                root_fd = os.open(BRAIN_MOUNT, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
                try:
                    if not brain_available():
                        raise ValueError("Burito Brain drive changed during schema migration")
                    actual_version = connection.execute("PRAGMA user_version").fetchone()[0]
                    record_database_schema(root_fd, BRAIN_UUID, actual_version)
                finally:
                    os.close(root_fd)
        except BaseException:
            connection.close()
            raise
        return connection

    def initialize(self):
        connection = self._connect()
        connection.close()
        return self.path

    def remember(self, content, source="owner", category="semantic", confidence=None,
                 verification="owner_statement", claim_key=None,
                 retention_policy="owner_controlled"):
        content, source = content.strip(), source.strip()
        if not content or not source:
            raise ValueError("Memory content and source must not be empty")
        if len(content) > 20000 or len(source) > 200:
            raise ValueError("Memory content or source exceeds its size limit")
        if (not isinstance(category, str) or category not in MEMORY_CATEGORIES
                or not isinstance(verification, str) or verification not in VERIFICATION_STATES):
            raise ValueError("Choose a supported memory category and verification state")
        if confidence is not None:
            try:
                confidence = float(confidence)
            except (TypeError, ValueError) as error:
                raise ValueError("Confidence must be between 0 and 1") from error
            if not math.isfinite(confidence) or not 0 <= confidence <= 1:
                raise ValueError("Confidence must be between 0 and 1")
        if claim_key is not None and not isinstance(claim_key, str):
            raise ValueError("Memory claim key must be text")
        claim_key = " ".join(claim_key.split()).casefold() if claim_key else None
        if claim_key is not None and len(claim_key) > 300:
            raise ValueError("Memory claim key exceeds 300 characters")
        if retention_policy != "owner_controlled":
            raise ValueError("Only owner-controlled retention is currently supported")
        identifier = str(uuid.uuid4())
        connection = self._connect()
        try:
            with connection:
                matches = []
                if claim_key:
                    matches = connection.execute(
                        "SELECT id,content FROM memories WHERE active=1 AND category=? AND claim_key=?",
                        (category, claim_key),
                    ).fetchall()
                connection.execute(
                    """INSERT INTO memories
                    (id,content,source,created_at,status,category,confidence,verification,
                     claim_key,retention_policy,updated_at,active)
                    VALUES (?,?,?,?, 'confirmed',?,?,?,?,?,?,1)""",
                    (identifier, content, source, datetime.now(timezone.utc).isoformat(),
                     category, confidence, verification, claim_key, retention_policy,
                     datetime.now(timezone.utc).isoformat()),
                )
                for match in matches:
                    if _normalize(match["content"]) != _normalize(content):
                        connection.execute(
                            """INSERT INTO memory_conflicts
                            (left_id,right_id,reason,status,created_at)
                            VALUES (?,?,?,'unresolved',?)""",
                            (match["id"], identifier, "same category and claim key have different content",
                             datetime.now(timezone.utc).isoformat()),
                        )
        finally:
            connection.close()
        return identifier

    def list(self, include_superseded=False, category=None):
        if category is not None and (not isinstance(category, str)
                                     or category not in MEMORY_CATEGORIES):
            raise ValueError("Choose a supported memory category")
        connection = self._connect()
        try:
            conditions = []
            parameters = []
            if not include_superseded:
                conditions.append("m.active=1")
            if category is not None:
                conditions.append("m.category=?")
                parameters.append(category)
            where = " WHERE " + " AND ".join(conditions) if conditions else ""
            return [dict(row) for row in connection.execute(
                f"""SELECT m.*,
                EXISTS(SELECT 1 FROM memory_conflicts c WHERE c.status='unresolved'
                    AND m.id IN (c.left_id,c.right_id)) AS unresolved_conflict
                FROM memories m {where}
                ORDER BY created_at, id""", parameters
            )]
        finally:
            connection.close()

    def find_duplicates(self, content, category="semantic"):
        if not isinstance(content, str):
            raise ValueError("Duplicate search content must be text")
        if category not in MEMORY_CATEGORIES:
            raise ValueError("Choose a supported memory category")
        normalized = _normalize(content)
        if not normalized:
            return []
        connection = self._connect()
        try:
            return [dict(row) for row in connection.execute(
                "SELECT * FROM memories WHERE active=1 AND category=? ORDER BY created_at,id",
                (category,),
            ) if _normalize(row["content"]) == normalized]
        finally:
            connection.close()

    def conflicts(self, status="unresolved"):
        if status not in {"unresolved", "resolved", "dismissed", "superseded", "all"}:
            raise ValueError("Choose unresolved, resolved, dismissed, superseded, or all")
        connection = self._connect()
        try:
            condition = "" if status == "all" else "WHERE c.status=?"
            parameters = () if status == "all" else (status,)
            return [dict(row) for row in connection.execute(
                f"""SELECT c.*,l.content AS left_content,l.source AS left_source,
                r.content AS right_content,r.source AS right_source
                FROM memory_conflicts c JOIN memories l ON l.id=c.left_id
                JOIN memories r ON r.id=c.right_id {condition} ORDER BY c.id""",
                parameters,
            )]
        finally:
            connection.close()

    def resolve_conflict(self, conflict_id, resolution="resolved", superseded_id=None):
        if resolution not in {"resolved", "dismissed", "superseded"}:
            raise ValueError("Unsupported conflict resolution")
        if (resolution == "superseded") != (superseded_id is not None):
            raise ValueError("Superseding a conflict requires the record to deactivate")
        connection = self._connect()
        try:
            with connection:
                row = connection.execute(
                    "SELECT left_id,right_id,status FROM memory_conflicts WHERE id=?",
                    (conflict_id,),
                ).fetchone()
                if row is None or row["status"] != "unresolved":
                    return False
                if superseded_id is not None:
                    if superseded_id not in (row["left_id"], row["right_id"]):
                        raise ValueError("Superseded record must belong to this conflict")
                    connection.execute("UPDATE memories SET active=0,updated_at=? WHERE id=?",
                                       (datetime.now(timezone.utc).isoformat(), superseded_id))
                    connection.execute(
                        """UPDATE memory_conflicts SET status='superseded',resolved_at=?
                        WHERE status='unresolved' AND (left_id=? OR right_id=?)""",
                        (datetime.now(timezone.utc).isoformat(), superseded_id, superseded_id),
                    )
                    return True
                return connection.execute(
                    "UPDATE memory_conflicts SET status=?,resolved_at=? WHERE id=? AND status='unresolved'",
                    (resolution, datetime.now(timezone.utc).isoformat(), conflict_id),
                ).rowcount == 1
        finally:
            connection.close()

    def search(self, query, limit=5, category=None, categories=None):
        """Rank explicitly stored facts without persisting a second index."""
        if not isinstance(query, str):
            raise ValueError("Search query must be text")
        if category is not None and (not isinstance(category, str)
                                     or category not in MEMORY_CATEGORIES):
            raise ValueError("Choose a supported memory category")
        if categories is not None and (category is not None or not isinstance(categories, (list, tuple, set, frozenset))
                or not categories or any(not isinstance(item, str) or item not in MEMORY_CATEGORIES
                                         for item in categories)):
            raise ValueError("Choose one or more supported memory categories")
        terms = self.query_terms(query)
        if not terms or len(terms) > 16:
            raise ValueError("Use between 1 and 16 useful search terms")
        expression = " OR ".join('"' + term.replace('"', '""') + '"' for term in terms)
        connection = self._connect()
        try:
            # shortcut: rebuild this in-memory index per query for small personal stores; persist it only if benchmarks justify it.
            connection.execute("PRAGMA temp_store=MEMORY")
            connection.execute("""CREATE VIRTUAL TABLE temp.memory_search USING fts5(
                memory_id UNINDEXED, content, source, tokenize='unicode61')""")
            connection.execute("""INSERT INTO temp.memory_search(memory_id,content,source)
                SELECT id,content,source FROM memories""")
            category_clause = ""
            parameters = [expression]
            if category is not None:
                category_clause = " AND m.category=?"
                parameters.append(category)
            elif categories is not None:
                category_clause = " AND m.category IN (" + ",".join("?" for _ in categories) + ")"
                parameters.extend(sorted(categories))
            parameters.append(max(1, min(int(limit), 10)))
            rows = connection.execute("""SELECT m.*,
                EXISTS(SELECT 1 FROM memory_conflicts c WHERE c.status='unresolved'
                    AND m.id IN (c.left_id,c.right_id)) AS unresolved_conflict
                FROM temp.memory_search
                JOIN memories m ON m.id=memory_search.memory_id
                WHERE memory_search MATCH ? AND m.active=1""" + category_clause + """
                ORDER BY bm25(memory_search,0,1,0.4),
                m.created_at DESC LIMIT ?""", tuple(parameters)).fetchall()
            return [dict(row) for row in rows]
        finally:
            connection.close()

    @staticmethod
    def query_terms(query):
        return [term for term in re.findall(r"[^\W_]+", query.casefold(), flags=re.UNICODE)
                if len(term) > 1 and term not in SEARCH_STOPWORDS]

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

    def correct(self, identifier, content, expected_content=None):
        content = content.strip()
        if not content or len(content) > 20000:
            raise ValueError("Corrected memory must contain 1 to 20000 characters")
        if expected_content is not None and (not expected_content or len(expected_content) > 20000):
            raise ValueError("Expected memory content must contain 1 to 20000 characters")
        connection = self._connect()
        try:
            with connection:
                connection.execute("PRAGMA secure_delete = ON")
                current = connection.execute("SELECT * FROM memories WHERE id=? AND active=1",
                                             (identifier,)).fetchone()
                if current is None or (expected_content is not None and current["content"] != expected_content):
                    return False
                if current["content"] == content:
                    return True
                revision = connection.execute(
                    "SELECT COALESCE(MAX(revision),0)+1 FROM memory_revisions WHERE memory_id=?",
                    (identifier,),
                ).fetchone()[0]
                return connection.execute(
                    """INSERT INTO memory_revisions
                    (memory_id,revision,content,source,category,confidence,verification,
                     claim_key,created_at,updated_at,recorded_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (identifier, revision, current["content"], current["source"],
                     current["category"], current["confidence"], current["verification"],
                     current["claim_key"], current["created_at"], current["updated_at"],
                     datetime.now(timezone.utc).isoformat()),
                ).rowcount == 1 and connection.execute(
                    """UPDATE memories SET content=?,source='owner correction',
                    verification='owner_statement',updated_at=? WHERE id=?""",
                    (content, datetime.now(timezone.utc).isoformat(), identifier),
                ).rowcount == 1
        finally:
            connection.close()

    def history(self, identifier):
        connection = self._connect()
        try:
            return [dict(row) for row in connection.execute(
                "SELECT * FROM memory_revisions WHERE memory_id=? ORDER BY revision",
                (identifier,),
            )]
        finally:
            connection.close()

    def backup(self, destination):
        """Write a consistent snapshot and a private, checksummed manifest."""
        destination = Path(destination)
        if not destination.is_absolute():
            raise ValueError("Backup destination must be an absolute path")
        # The parent must already exist: do not create folders on an unmounted disk.
        brain_mount = BRAIN_MOUNT.resolve()
        destination_parent = destination.parent.resolve()
        parent_info = destination_parent.stat()
        if not stat.S_ISDIR(parent_info.st_mode) or parent_info.st_uid != os.getuid():
            raise ValueError("Backup directory must be an existing directory owned by you")
        if (destination.is_relative_to(BRAIN_MOUNT)
                or destination_parent.is_relative_to(brain_mount)
                or (brain_mount.exists() and parent_info.st_dev == brain_mount.stat().st_dev)):
            raise ValueError("Memory backups must be stored outside the brain filesystem")
        if parent_info.st_mode & 0o077:
            raise ValueError("Backup directory must be an existing owner-only directory")
        destination = destination_parent / destination.name
        manifest_path = Path(f"{destination}.manifest.json")
        directory_fd = os.open(destination_parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        temporary = f".{destination.name}.{uuid.uuid4().hex}.tmp"
        temporary_manifest = f"{temporary}.json"
        source = target = None
        published_database = published_manifest = False
        try:
            fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW,
                         0o600, dir_fd=directory_fd)
            os.close(fd)
            source = self._connect()
            target = sqlite3.connect(destination_parent / temporary)
            schema_version = source.execute("PRAGMA user_version").fetchone()[0]
            source.backup(target)
            target.close()
            target = None
            fd = os.open(temporary, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory_fd)
            try:
                digest = hashlib.sha256()
                while chunk := os.read(fd, 1024 * 1024):
                    digest.update(chunk)
                os.fsync(fd)
            finally:
                os.close(fd)

            source_brain = None
            if self.directory.resolve().is_relative_to(brain_mount):
                root_fd = os.open(brain_mount, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
                try:
                    identity = ensure_brain_manifest(root_fd, BRAIN_UUID, True)
                finally:
                    os.close(root_fd)
                source_brain = {"filesystem_uuid": BRAIN_UUID, "brain_id": identity["brain_id"]}
            manifest = {
                "format": "burito-sqlite-backup", "format_version": 1,
                "database": destination.name, "database_schema_version": schema_version,
                "source_brain": source_brain,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "database_sha256": digest.hexdigest(),
                "restore_compatibility": {"minimum_runtime": "0.1.0",
                                           "supported_schema_versions": [1, DATABASE_SCHEMA_VERSION]},
            }
            payload = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
            fd = os.open(temporary_manifest, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
                         0o600, dir_fd=directory_fd)
            try:
                view = memoryview(payload)
                while view:
                    view = view[os.write(fd, view):]
                os.fsync(fd)
            finally:
                os.close(fd)
            os.link(temporary, destination.name, src_dir_fd=directory_fd,
                    dst_dir_fd=directory_fd, follow_symlinks=False)
            published_database = True
            os.link(temporary_manifest, manifest_path.name, src_dir_fd=directory_fd,
                    dst_dir_fd=directory_fd, follow_symlinks=False)
            published_manifest = True
            os.fsync(directory_fd)
        except BaseException:
            if target is not None:
                target.close()
                target = None
            if published_manifest:
                os.unlink(manifest_path.name, dir_fd=directory_fd)
            if published_database:
                os.unlink(destination.name, dir_fd=directory_fd)
            raise
        finally:
            if target is not None:
                target.close()
            if source is not None:
                source.close()
            for name in (temporary, temporary_manifest):
                try:
                    os.unlink(name, dir_fd=directory_fd)
                except FileNotFoundError:
                    pass
            os.close(directory_fd)
        return destination

    def verify_backup(self, destination):
        """Check backup identity, checksum, schema and SQLite integrity read-only."""
        destination = Path(destination)
        if not destination.is_absolute():
            raise ValueError("Backup destination must be an absolute path")
        parent = destination.parent.resolve()
        destination = parent / destination.name
        manifest_path = Path(f"{parent / destination.name}.manifest.json")
        directory_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        database_fd = manifest_fd = None
        try:
            parent_info = os.fstat(directory_fd)
            if parent_info.st_uid != os.getuid() or parent_info.st_mode & 0o077:
                raise ValueError("Backup directory must be owner-only and owned by you")
            database_fd = os.open(destination.name, os.O_RDONLY | os.O_NOFOLLOW,
                                  dir_fd=directory_fd)
            manifest_fd = os.open(manifest_path.name, os.O_RDONLY | os.O_NOFOLLOW,
                                  dir_fd=directory_fd)
            for fd in (database_fd, manifest_fd):
                info = os.fstat(fd)
                if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                        or info.st_mode & 0o077):
                    raise ValueError("Backup files must be owner-private regular files")
            payload = os.read(manifest_fd, 16385)
            if len(payload) > 16384:
                raise ValueError("Backup manifest is too large")
            metadata = json.loads(payload)
            if (not isinstance(metadata, dict)
                    or metadata.get("format") != "burito-sqlite-backup"
                    or type(metadata.get("format_version")) is not int
                    or metadata["format_version"] != 1
                    or metadata.get("database") != destination.name):
                raise ValueError("Backup manifest format or database name is invalid")
            compatibility = metadata.get("restore_compatibility")
            supported_schemas = (compatibility.get("supported_schema_versions")
                                 if isinstance(compatibility, dict) else None)
            source_brain = metadata.get("source_brain")
            checksum = metadata.get("database_sha256")
            if (not isinstance(compatibility, dict)
                    or not isinstance(compatibility.get("minimum_runtime"), str)
                    or not isinstance(supported_schemas, list)
                    or any(type(version) is not int for version in supported_schemas)
                    or not isinstance(metadata.get("created_at"), str)
                    or type(metadata.get("database_schema_version")) is not int
                    or not isinstance(checksum, str) or len(checksum) != 64):
                raise ValueError("Backup restore compatibility metadata is invalid")
            try:
                datetime.fromisoformat(metadata["created_at"])
                if source_brain is not None:
                    uuid.UUID(source_brain["filesystem_uuid"])
                    uuid.UUID(source_brain["brain_id"])
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError("Backup timestamp or source brain identity is invalid") from error
            digest = hashlib.sha256()
            while chunk := os.read(database_fd, 1024 * 1024):
                digest.update(chunk)
            if digest.hexdigest() != checksum:
                raise ValueError("Backup checksum does not match its manifest")
            connection = sqlite3.connect(f"file:/proc/self/fd/{database_fd}?mode=ro", uri=True)
            try:
                schema_version = connection.execute("PRAGMA user_version").fetchone()[0]
                integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            finally:
                connection.close()
        finally:
            if database_fd is not None:
                os.close(database_fd)
            if manifest_fd is not None:
                os.close(manifest_fd)
            os.close(directory_fd)
        if (schema_version != metadata["database_schema_version"]
                or schema_version not in (1, DATABASE_SCHEMA_VERSION)
                or schema_version not in supported_schemas
                or integrity != "ok"):
            raise ValueError("Backup schema or SQLite integrity check failed")
        return metadata
