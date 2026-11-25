"""Mutual exclusion for Burito entry points that share eve runtime state."""

import fcntl
import os
from pathlib import Path
from datetime import datetime, timezone


def acquire_runtime_lock(runtime):
    """Acquire the per-runtime exclusive lock and return its open descriptor."""
    runtime = Path(runtime)
    state_directory = runtime / ".eve"
    state_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if state_directory.is_symlink() or state_directory.stat().st_uid != os.getuid():
        raise ValueError("eve state directory must be owned by you and not a symlink")
    state_directory.chmod(0o700)
    lock_path = state_directory / "burito-runtime.lock"
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as error:
        os.close(lock_fd)
        raise ValueError(
            "Another Burito/Eve runtime is already using this project state. "
            "Close its chat or web console before starting another."
        ) from error
    return lock_fd


def archive_workflow_data(runtime):
    """Preserve prior Eve dev queues so deliveries signed by an old run secret aren't replayed."""
    state_directory = Path(runtime) / ".eve"
    workflow_data = state_directory / ".workflow-data"
    try:
        info = workflow_data.lstat()
    except FileNotFoundError:
        return None
    if (workflow_data.is_symlink() or not workflow_data.is_dir()
            or info.st_uid != os.getuid()):
        raise ValueError("Eve workflow data must be an owned directory, not a symlink")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    archived = state_directory / f".workflow-data.backup-{stamp}"
    os.replace(workflow_data, archived)
    return archived