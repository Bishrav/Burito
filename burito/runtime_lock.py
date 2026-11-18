"""Mutual exclusion for Burito entry points that share eve runtime state."""

import fcntl
import os
from pathlib import Path


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
