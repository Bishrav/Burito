"""Versioned, owner-private identity record for the mounted brain volume."""

from datetime import datetime, timezone
import json
import os
import stat
import uuid

NAME = "brain.json"
VERSION = 1
DATABASE_SCHEMA_VERSION = 2


def ensure(root_fd, filesystem_uuid, database_exists):
    try:
        directory_fd = os.open("manifest", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                               dir_fd=root_fd)
    except FileNotFoundError:
        try:
            os.mkdir("manifest", 0o700, dir_fd=root_fd)
        except FileExistsError:
            pass
        os.fsync(root_fd)
        directory_fd = os.open("manifest", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                               dir_fd=root_fd)
    try:
        if os.fstat(directory_fd).st_uid != os.getuid():
            raise ValueError("Brain manifest directory must be owned by you")
        try:
            return _read(directory_fd, filesystem_uuid)
        except FileNotFoundError:
            if database_exists:
                raise ValueError("Memory database exists without a brain manifest; verify before adopting it")

        manifest = {
            "format": "burito-brain",
            "manifest_version": VERSION,
            "brain_id": str(uuid.uuid4()),
            "filesystem": {"uuid": filesystem_uuid, "type": "ext4"},
            "storage_schema_version": 1,
            "database_schema_versions": {"memory.sqlite3": DATABASE_SCHEMA_VERSION},
            "runtime_compatibility": {"minimum": "0.1.0"},
            "models": [], "datasets": [], "migration_history": [],
            "integrity": {"algorithm": "sha256", "checked_at": None},
            "backup": {"independent_verified_at": None},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        payload = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
        temporary = ".brain.json." + uuid.uuid4().hex + ".tmp"
        fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
                     0o600, dir_fd=directory_fd)
        try:
            view = memoryview(payload)
            while view:
                view = view[os.write(fd, view):]
            os.fsync(fd)
        finally:
            os.close(fd)
        try:
            os.link(temporary, NAME, src_dir_fd=directory_fd, dst_dir_fd=directory_fd,
                    follow_symlinks=False)
        except FileExistsError:
            pass
        finally:
            os.unlink(temporary, dir_fd=directory_fd)
        os.fsync(directory_fd)
        return _read(directory_fd, filesystem_uuid)
    finally:
        os.close(directory_fd)


def _read(directory_fd, filesystem_uuid):
    fd = os.open(NAME, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory_fd)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077 or info.st_size > 16384):
            raise ValueError("Brain manifest must be a small, owner-private regular file")
        with os.fdopen(fd, "rb", closefd=False) as source:
            manifest = json.loads(source.read(16385))
    finally:
        os.close(fd)
    try:
        database_schema = manifest["database_schema_versions"]["memory.sqlite3"]
        valid_id = uuid.UUID(manifest["brain_id"])
        valid = (manifest["format"] == "burito-brain"
                 and type(manifest["manifest_version"]) is int
                 and manifest["manifest_version"] == VERSION
                 and manifest["filesystem"] == {"uuid": filesystem_uuid, "type": "ext4"}
                 and type(database_schema) is int
                 and database_schema in (1, DATABASE_SCHEMA_VERSION))
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Brain manifest is invalid or unsupported") from error
    if not valid or valid_id.version != 4:
        raise ValueError("Brain manifest identity or version does not match this volume")
    return manifest


def record_database_schema(root_fd, filesystem_uuid, version):
    if version != DATABASE_SCHEMA_VERSION:
        raise ValueError("Unsupported memory database schema version")
    directory_fd = os.open("manifest", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                           dir_fd=root_fd)
    try:
        if os.fstat(directory_fd).st_uid != os.getuid():
            raise ValueError("Brain manifest directory must be owned by you")
        manifest = _read(directory_fd, filesystem_uuid)
        schemas = manifest["database_schema_versions"]
        previous = schemas["memory.sqlite3"]
        if previous == version:
            return manifest
        manifest["database_schema_versions"]["memory.sqlite3"] = version
        manifest["migration_history"].append({
            "component": "memory.sqlite3", "from": previous, "to": version,
            "at": datetime.now(timezone.utc).isoformat(),
        })
        payload = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
        temporary = ".brain.json." + uuid.uuid4().hex + ".tmp"
        fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
                     0o600, dir_fd=directory_fd)
        try:
            view = memoryview(payload)
            while view:
                view = view[os.write(fd, view):]
            os.fsync(fd)
        finally:
            os.close(fd)
        try:
            os.replace(temporary, NAME, src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
        finally:
            try:
                os.unlink(temporary, dir_fd=directory_fd)
            except FileNotFoundError:
                pass
        os.fsync(directory_fd)
        return _read(directory_fd, filesystem_uuid)
    finally:
        os.close(directory_fd)
