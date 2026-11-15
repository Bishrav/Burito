"""Bounded, read-only local diagnostics. No network calls."""

import os
import platform
import shutil
import subprocess
from .memory import data_directory


def probe(arguments):
    executable = shutil.which(arguments[0])
    if executable is None:
        return {"available": False, "ok": False, "detail": "not found on PATH"}
    try:
        result = subprocess.run(
            [executable, *arguments[1:]], capture_output=True, text=True,
            timeout=8, check=False,
        )
        return {
            "available": True, "ok": result.returncode == 0,
            "detail": (result.stdout + result.stderr).strip()[:3000],
        }
    except (subprocess.TimeoutExpired, OSError) as error:
        return {"available": True, "ok": False, "detail": str(error)[:500]}


def report():
    destination = data_directory()
    ancestor = destination
    while not ancestor.exists() and ancestor != ancestor.parent:
        ancestor = ancestor.parent
    storage = shutil.disk_usage(ancestor)
    return {
        "system": platform.system(), "release": platform.release(),
        "architecture": platform.machine(), "python": platform.python_version(),
        "session": os.environ.get("XDG_SESSION_TYPE", "unknown"),
        "memory_directory": str(destination),
        "storage_free_gib": round(storage.free / 1024**3, 1),
        "storage_total_gib": round(storage.total / 1024**3, 1),
        "gpu": probe(["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
                      "--format=csv,noheader"]),
        "node": probe(["node", "--version"]),
        "npm": probe(["npm", "--version"]),
        "observation": "not implemented; disabled",
        "cloud": "not configured; disabled",
    }
