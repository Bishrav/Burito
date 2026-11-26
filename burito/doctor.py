"""Bounded, read-only local diagnostics. No network calls."""

import os
import platform
import shutil
import subprocess
from pathlib import Path
from .memory import BRAIN_MOUNT, brain_status, data_directory


def probe(arguments, environment=None):
    search_path = environment.get("PATH") if environment is not None else None
    executable = shutil.which(arguments[0], path=search_path)
    if executable is None:
        return {"available": False, "ok": False, "detail": "not found on PATH"}
    try:
        result = subprocess.run(
            [executable, *arguments[1:]], capture_output=True, text=True,
            timeout=8, check=False, env=environment,
        )
        return {
            "available": True, "ok": result.returncode == 0,
            "detail": (result.stdout + result.stderr).strip()[:3000],
        }
    except (subprocess.TimeoutExpired, OSError) as error:
        return {"available": True, "ok": False, "detail": str(error)[:500]}


def gpu_context(gpu, proc_root=Path("/proc"), dev_root=Path("/dev")):
    """Do not diagnose a broken host driver from an isolated session."""
    version = proc_root / "driver/nvidia/version"
    try:
        loaded = version.is_file()
    except OSError:
        loaded = False
    nodes = sorted(path.name for path in dev_root.glob("nvidia*") if path.is_char_device())
    if gpu["ok"]:
        assessment = "GPU query succeeded in this session"
    elif loaded and not nodes:
        assessment = (
            "NVIDIA kernel driver is loaded, but device files are not visible. "
            "Run nvidia-smi in your normal desktop terminal before changing drivers."
        )
    else:
        assessment = "GPU readiness is unverified; inspect from the desktop terminal"
    return {"kernel_driver_loaded": loaded, "visible_device_nodes": nodes,
            "assessment": assessment}


def report():
    destination = data_directory()
    requires_brain = destination.is_relative_to(BRAIN_MOUNT)
    storage_status = brain_status() if requires_brain else None
    brain_ready = storage_status == "ready" if requires_brain else None
    storage = None
    if storage_status in (None, "ready", "read_only", "not_writable", "full"):
        ancestor = destination
        while not ancestor.exists() and ancestor != ancestor.parent:
            ancestor = ancestor.parent
        storage = shutil.disk_usage(ancestor)
    gpu = probe(["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
                 "--format=csv,noheader"])
    environment = os.environ.copy()
    # The user-local installer intentionally does not change the shell profile.
    tools = Path(__file__).resolve().parent.parent / ".tools"
    candidates = sorted(tools.glob("node-*/bin"), reverse=True)
    if candidates:
        environment["PATH"] = os.pathsep.join([str(candidates[0]), environment.get("PATH", "")])
    node = probe(["node", "--version"], environment)
    try:
        node["supported"] = node["ok"] and int(node["detail"].lstrip("v").split(".")[0]) >= 24
    except ValueError:
        node["supported"] = False
    result = {
        "system": platform.system(), "release": platform.release(),
        "architecture": platform.machine(), "python": platform.python_version(),
        "session": os.environ.get("XDG_SESSION_TYPE", "unknown"),
        "memory_directory": str(destination),
        "brain_available": brain_ready,
        "brain_status": storage_status,
        "storage_free_gib": round(storage.free / 1024**3, 1) if storage else None,
        "storage_total_gib": round(storage.total / 1024**3, 1) if storage else None,
        "gpu": {**gpu, **gpu_context(gpu)},
        "node": node,
        "npm": probe(["npm", "--version"], environment),
        "block_devices": probe(["lsblk", "-o", "NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS"]),
        "observation": "PC metadata collector available; use pc monitor-status. Screen capture is not implemented.",
        "cloud": "not configured; disabled",
    }
    result["next_steps"] = []
    if not gpu["ok"]:
        result["next_steps"].append("Verify nvidia-smi in the normal Ryoku terminal")
    if not node["supported"] or not result["npm"]["ok"]:
        result["next_steps"].append("Run bash scripts/setup-runtime.sh from the repository in the normal terminal")
    if brain_ready is False:
        next_step = {
            "read_only": "Remount BURITO_BRAIN read/write before durable operations",
            "not_writable": "Check ownership and permissions on the brain memory directory",
            "full": "Free space on BURITO_BRAIN before durable operations",
            "data_directory_missing": "Create the brain memory directory only on the verified mounted volume",
            "wrong_identity": "Mount the verified BURITO_BRAIN UUID; no fallback memory database is used",
            "unsupported_filesystem": "Use the verified ext4 brain volume; no fallback memory database is used",
            "wrong_owner": "Correct the memory directory owner only after verifying the brain volume",
            "invalid_data_directory": "Inspect the brain memory path; it must be a real directory",
        }.get(storage_status, "Connect and verify BURITO_BRAIN; no fallback memory database is used")
        result["next_steps"].append(next_step)
    result["next_steps"].append("Confirm available storage before downloading models")
    return result
