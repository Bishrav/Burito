"""Local machine inventory and bounded metadata change detection."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

from .memory import Memory


ROOT = Path(__file__).resolve().parent.parent
EXCLUDED = {"node_modules", "venv", "__pycache__", "lost+found"}


def command(arguments):
    if shutil.which(arguments[0]) is None:
        return None, f"{arguments[0]} is not installed"
    try:
        result = subprocess.run(arguments, capture_output=True, text=True, timeout=8, check=False)
        if result.returncode:
            return None, (result.stderr.strip() or "command failed")[:300]
        return result.stdout, None
    except (OSError, subprocess.TimeoutExpired) as error:
        return None, str(error)[:300]


def files(root, limit=20000):
    """Never open file contents, follow symlinks, or cross filesystem boundaries."""
    root = Path(root)
    entries, errors = {}, []
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        root_fd = os.open(root, flags)
        device = os.fstat(root_fd).st_dev
    except OSError as error:
        return {}, [str(error)[:300]]

    def visit(directory_fd, prefix=Path(), depth=0):
        try:
            with os.scandir(directory_fd) as children:
                for child in children:
                    if child.name.startswith(".") or child.name in EXCLUDED:
                        continue
                    if len(entries) >= limit:
                        errors.append(f"Metadata limit reached ({limit} entries)")
                        return False
                    try:
                        info = child.stat(follow_symlinks=False)
                        relative = str(prefix / child.name)
                        is_directory = child.is_dir(follow_symlinks=False)
                        kind = "symlink" if child.is_symlink() else "directory" if is_directory else "file"
                        record = {"kind": kind}
                        # Directory mtime changes during unrelated writes are not file edits.
                        if kind != "directory":
                            record.update(size=info.st_size, mtime_ns=info.st_mtime_ns)
                        entries[relative] = record
                        if is_directory and info.st_dev == device:
                            if depth >= 40:
                                errors.append(f"Directory depth limit reached at {relative}")
                                continue
                            # Relative descriptor opens prevent symlink replacement races.
                            child_fd = os.open(child.name, flags, dir_fd=directory_fd)
                            try:
                                if os.fstat(child_fd).st_dev == device:
                                    if not visit(child_fd, prefix / child.name, depth + 1):
                                        return False
                            finally:
                                os.close(child_fd)
                    except OSError as error:
                        errors.append(str(error)[:300])
        except OSError as error:
            errors.append(str(error)[:300])
        return True

    try:
        visit(root_fd)
    finally:
        os.close(root_fd)
    return entries, errors


def collect(home=None):
    home = Path.home() if home is None else Path(home)
    categories, problems = {}, {}
    hardware = {"os": platform.system(), "kernel": platform.release(),
                "architecture": platform.machine()}
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                hardware["cpu"] = line.split(":", 1)[1].strip()
                break
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                hardware["ram_kib"] = int(line.split()[1])
                break
        os_values = {}
        for line in Path("/etc/os-release").read_text().splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                os_values[key] = value.strip('"')
        hardware["distribution"] = os_values.get("PRETTY_NAME", "unknown")
    except OSError as error:
        problems["hardware"] = [str(error)[:300]]
    pci, error = command(["lspci", "-mm"])
    if pci is not None:
        hardware["display_devices"] = [line for line in pci.splitlines()
                                        if any(word in line for word in ("VGA", "3D controller", "Display controller"))]
    else:
        problems.setdefault("hardware", []).append(error)
    categories["hardware"] = hardware

    disks, error = command(["lsblk", "-J", "-o", "NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS"])
    if disks is not None:
        try:
            categories["storage"] = {item["name"]: item for item in json.loads(disks)["blockdevices"]
                                     if item.get("type") != "loop"}
        except (ValueError, KeyError, TypeError) as error:
            problems["storage"] = [str(error)[:300]]
    else:
        problems["storage"] = [error]

    packages, error = command(["dpkg-query", "-W", "-f=${binary:Package}\t${Version}\t${db:Status-Status}\n"])
    if packages is not None:
        categories["packages"] = {}
        for line in packages.splitlines():
            parts = line.split("\t")
            if len(parts) == 3 and parts[2] == "installed":
                categories["packages"][parts[0]] = parts[1]
    else:
        problems["packages"] = [error]

    # Read snap manifests on disk rather than depending on access to snapd's bus.
    for name, location in (("snap_manifests", Path("/var/lib/snapd/snaps")),
                           ("local_programs", Path("/usr/local/bin")),
                           ("user_programs", home / ".local/bin"),
                           ("desktop_apps", Path("/usr/share/applications"))):
        try:
            categories[name] = {}
            if location.exists():
                for item in location.iterdir():
                    if name == "snap_manifests" and item.suffix != ".snap":
                        continue
                    if name == "desktop_apps" and item.suffix != ".desktop":
                        continue
                    info = item.lstat()
                    categories[name][item.name] = {"size": info.st_size, "mtime_ns": info.st_mtime_ns}
        except OSError as error:
            problems[name] = [str(error)[:300]]
    if shutil.which("flatpak"):
        apps, error = command(["flatpak", "list", "--app", "--columns=application,version"])
        if apps is not None:
            categories["flatpak_apps"] = dict(line.split("\t", 1) if "\t" in line else (line, "unknown")
                                               for line in apps.splitlines() if line)
        else:
            problems["flatpak_apps"] = [error]

    categories["usb"] = {}
    for product in Path("/sys/bus/usb/devices").glob("*/product"):
        try:
            categories["usb"][product.parent.name] = product.read_text().strip()
        except OSError as error:
            problems.setdefault("usb", []).append(str(error)[:300])
    categories["home_files"], errors = files(home)
    if errors:
        problems["home_files"] = errors[:20]
    return categories, problems


class Awareness:
    def __init__(self, memory=None):
        self.memory = memory if memory is not None else Memory()

    def _connect(self):
        connection = self.memory._connect()
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS pc_snapshots (
                category TEXT PRIMARY KEY, payload TEXT NOT NULL, observed_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS pc_events (
                id INTEGER PRIMARY KEY, observed_at TEXT NOT NULL, category TEXT NOT NULL,
                kind TEXT NOT NULL, name TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS pc_scans (
                id INTEGER PRIMARY KEY, observed_at TEXT NOT NULL, problems TEXT NOT NULL);
        """)
        return connection

    def scan(self, categories=None, problems=None):
        if categories is None:
            categories, problems = collect()
        problems = {} if problems is None else problems
        now = datetime.now(timezone.utc).isoformat()
        connection = self._connect()
        count = 0
        try:
            with connection:
                for category, current in categories.items():
                    row = connection.execute("SELECT payload FROM pc_snapshots WHERE category = ?", (category,)).fetchone()
                    old = json.loads(row["payload"]) if row else None
                    partial = bool(problems.get(category))
                    if old is not None:
                        changes = [("added" if key not in old else "modified", key)
                                   for key in current if key not in old or current[key] != old[key]]
                        if not partial:
                            changes += [("removed", key) for key in old if key not in current]
                        for kind, name in changes:
                            connection.execute("INSERT INTO pc_events(observed_at, category, kind, name) VALUES (?, ?, ?, ?)",
                                               (now, category, kind, name))
                        count += len(changes)
                    # Preserve unvisited entries after an error/cap; do not infer removal.
                    merged = {**(old or {}), **current} if partial else current
                    connection.execute("""INSERT INTO pc_snapshots VALUES (?, ?, ?)
                        ON CONFLICT(category) DO UPDATE SET payload=excluded.payload, observed_at=excluded.observed_at""",
                                       (category, json.dumps(merged), now))
                connection.execute("INSERT INTO pc_scans(observed_at, problems) VALUES (?, ?)",
                                   (now, json.dumps(problems)))
                connection.execute("DELETE FROM pc_events WHERE id NOT IN (SELECT id FROM pc_events ORDER BY id DESC LIMIT 2000)")
                connection.execute("DELETE FROM pc_scans WHERE id NOT IN (SELECT id FROM pc_scans ORDER BY id DESC LIMIT 30)")
        finally:
            connection.close()
        return {"observed_at": now, "changes_detected": count, "categories": len(categories),
                "partial_or_unavailable": problems}

    def changes(self, limit=20):
        connection = self._connect()
        try:
            return [dict(row) for row in connection.execute(
                "SELECT * FROM pc_events ORDER BY id DESC LIMIT ?", (max(1, min(limit, 100)),))]
        finally:
            connection.close()

    def summary(self):
        connection = self._connect()
        try:
            scan = connection.execute("SELECT observed_at, problems FROM pc_scans ORDER BY id DESC LIMIT 1").fetchone()
            if scan is None:
                return {"available": False, "detail": "No PC inventory collected; run 'pc scan'"}
            snapshots = {row["category"]: {"observed_at": row["observed_at"], "data": json.loads(row["payload"])}
                         for row in connection.execute("SELECT * FROM pc_snapshots")}
            hardware = snapshots.get("hardware", {}).get("data", {})
            storage_devices = []
            pending = list(snapshots.get("storage", {}).get("data", {}).values())
            while pending and len(storage_devices) < 16:
                item = pending.pop(0)
                storage_devices.append({key: item.get(key) for key in
                                        ("name", "size", "type", "fstype", "mountpoints")})
                pending.extend(item.get("children", []))
            return {"available": True, "last_scan": scan["observed_at"],
                    "hardware": hardware,
                    "storage_devices": storage_devices,
                    "local_programs_sample": sorted(snapshots.get("local_programs", {}).get("data", {}))[:20],
                    "inventory_counts": {name: len(item["data"]) for name, item in snapshots.items()},
                    "category_observed_at": {name: item["observed_at"] for name, item in snapshots.items()},
                    "partial_or_unavailable": json.loads(scan["problems"]),
                    "recent_changes": self.changes(5),
                    "scope": "Local inventory and home-file metadata; hidden paths and contents excluded",
                    "monitoring_status": "Snapshot only; use pc monitor-status to check the timer"}
        finally:
            connection.close()


def service_directory():
    config_home = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    if not config_home.is_absolute():
        raise ValueError("XDG_CONFIG_HOME must be absolute")
    return config_home / "systemd/user"


def quote_unit(value):
    value = str(value)
    if any(character in value for character in ("\n", "\r", "\0")):
        raise ValueError("Invalid systemd unit path")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%") + '"'


def enable():
    directory = service_directory()
    directory.mkdir(parents=True, exist_ok=True)
    # Pass the current storage destination explicitly; changing data location requires re-enabling.
    environment = quote_unit("BURITO_DATA_DIR=" + str(Memory().directory))
    service = ("[Unit]\nDescription=Burito local PC inventory\n\n[Service]\nType=oneshot\n"
               f"WorkingDirectory={quote_unit(ROOT)}\nEnvironment={environment}\n"
               f"ExecStart={quote_unit(sys.executable)} -m burito pc scan\n"
               "TimeoutStartSec=90\nUMask=0077\nNoNewPrivileges=true\n")
    timer = ("[Unit]\nDescription=Check for PC changes after login\n\n[Timer]\n"
             "OnStartupSec=30\nOnUnitInactiveSec=60\nAccuracySec=5\nUnit=burito-awareness.service\n"
             "\n[Install]\nWantedBy=timers.target\n")
    (directory / "burito-awareness.service").write_text(service)
    (directory / "burito-awareness.timer").write_text(timer)
    for arguments in (["systemctl", "--user", "daemon-reload"],
                      ["systemctl", "--user", "enable", "--now", "burito-awareness.timer"]):
        result = subprocess.run(arguments, capture_output=True, text=True, timeout=15, check=False)
        if result.returncode:
            raise ValueError("Unit files are prepared but enabling failed. Run 'python3 -m burito pc enable' in Konsole. "
                             + result.stderr.strip()[:300])
    return "PC inventory timer enabled for the user session; about one scan per minute."


def pause():
    for unit in ("burito-awareness.timer", "burito-awareness.service"):
        action = ["disable", "--now"] if unit.endswith("timer") else ["stop"]
        result = subprocess.run(["systemctl", "--user", *action, unit], capture_output=True,
                                text=True, timeout=15, check=False)
        if result.returncode:
            raise ValueError("Pause could not be verified; run this command in Konsole. " + result.stderr.strip()[:300])
    return "Inventory polling stopped; existing local records remain."


def monitor_status():
    result = subprocess.run(["systemctl", "--user", "is-active", "burito-awareness.timer"],
                            capture_output=True, text=True, timeout=10, check=False)
    return {"timer_state": result.stdout.strip() or "unknown", "verified_active": result.returncode == 0,
            "detail": result.stderr.strip()[:300]}
