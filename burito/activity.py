"""Opt-in local foreground-application activity summaries."""

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from .memory import Memory
from .awareness import quote_unit, working_directory_value


ROOT = Path(__file__).resolve().parent.parent
PLUGIN_ID = "buritoactivity"
UNIT_NAME = "burito-activity.service"
EVENT_PREFIX = "BURITO_ACTIVITY:"
APP_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
MAX_ROWS = 20000
RETENTION_DAYS = 30
MAX_INTERVAL_HOURS = 4


def _connect(memory=None):
    connection = (memory or Memory())._connect()
    connection.execute("""CREATE TABLE IF NOT EXISTS app_activity (
        id INTEGER PRIMARY KEY,
        observed_at TEXT NOT NULL,
        app_id TEXT NOT NULL
    )""")
    connection.execute("CREATE INDEX IF NOT EXISTS app_activity_time ON app_activity(observed_at)")
    return connection


def _timestamp_from_journal(entry):
    raw = entry.get("__REALTIME_TIMESTAMP")
    if raw and str(raw).isdigit():
        return datetime.fromtimestamp(int(raw) / 1_000_000, timezone.utc).isoformat()
    return datetime.now(timezone.utc).isoformat()


def record(app_id, observed_at=None, memory=None):
    """Store one validated desktop application ID; coalesce repeated focus events."""
    app_id = str(app_id).strip()
    if app_id != "idle" and not APP_ID.fullmatch(app_id):
        raise ValueError("Invalid application ID; no activity was stored")
    timestamp = observed_at or datetime.now(timezone.utc).isoformat()
    connection = _connect(memory)
    try:
        with connection:
            previous = connection.execute(
                "SELECT app_id FROM app_activity ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if previous is not None and previous["app_id"] == app_id:
                return False
            connection.execute(
                "INSERT INTO app_activity(observed_at, app_id) VALUES (?, ?)",
                (timestamp, app_id),
            )
            cutoff = (datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)).isoformat()
            connection.execute("DELETE FROM app_activity WHERE observed_at < ?", (cutoff,))
            connection.execute("DELETE FROM app_activity WHERE id NOT IN "
                               "(SELECT id FROM app_activity ORDER BY id DESC LIMIT ?)", (MAX_ROWS,))
        return True
    finally:
        connection.close()


def collect(memory=None):
    """Read Burito's tagged KWin journal lines and persist app IDs locally."""
    journalctl = shutil.which("journalctl")
    if not journalctl:
        raise ValueError("journalctl is required for the KWin activity collector")
    arguments = [journalctl, "--follow", "--since=now", "--output=json",
                 "_COMM=kwin_wayland"]
    process = subprocess.Popen(arguments, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               text=True, encoding="utf-8", errors="replace", bufsize=1)
    if process.stdout is None:
        raise ValueError("Could not open the user journal stream")
    try:
        for line in process.stdout:
            try:
                entry = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                continue
            message = entry.get("MESSAGE", "")
            prefix = "js: " + EVENT_PREFIX
            if not isinstance(message, str) or not message.startswith(prefix):
                continue
            app_id = message[len(prefix):].strip()
            if app_id != "idle" and not APP_ID.fullmatch(app_id):
                continue
            record(app_id, _timestamp_from_journal(entry), memory)
        status = process.wait()
        if status:
            raise ValueError(f"journalctl exited with status {status}")
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def report(days=7, memory=None):
    if not isinstance(days, int) or not 1 <= days <= RETENTION_DAYS:
        raise ValueError(f"Choose a report period from 1 to {RETENTION_DAYS} days")
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)
    connection = _connect(memory)
    try:
        rows = [dict(row) for row in connection.execute(
            "SELECT observed_at, app_id FROM app_activity ORDER BY observed_at, id"
        )]
    finally:
        connection.close()

    totals = {}
    max_interval = timedelta(hours=MAX_INTERVAL_HOURS)
    for index, row in enumerate(rows):
        start = datetime.fromisoformat(row["observed_at"])
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        next_time = now
        if index + 1 < len(rows):
            next_time = datetime.fromisoformat(rows[index + 1]["observed_at"])
            if next_time.tzinfo is None:
                next_time = next_time.replace(tzinfo=timezone.utc)
        end = min(next_time, start + max_interval, now)
        interval_start = max(start, since)
        if row["app_id"] == "idle" or end <= interval_start:
            continue
        totals[row["app_id"]] = totals.get(row["app_id"], 0) + (end - interval_start).total_seconds()
    return {
        "period_days": days,
        "event_count": len(rows),
        "last_observed": rows[-1]["observed_at"] if rows else None,
        "foreground_estimates": [
            {"app_id": app_id, "seconds": round(seconds), "minutes": round(seconds / 60, 1)}
            for app_id, seconds in sorted(totals.items(), key=lambda item: (-item[1], item[0]))
        ],
        "interpretation": "Estimated foreground time from app switches, not proof of active use or interest. "
                          "Each uninterrupted interval is capped at four hours.",
        "scope": "Application desktop IDs only; no titles, screen content, keystrokes, or network upload.",
    }


def clear(memory=None):
    connection = _connect(memory)
    try:
        with connection:
            connection.execute("PRAGMA secure_delete = ON")
            deleted = connection.execute("DELETE FROM app_activity").rowcount
        connection.execute("VACUUM")
        return deleted
    finally:
        connection.close()


def _unit_directory():
    config_home = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    if not config_home.is_absolute():
        raise ValueError("XDG_CONFIG_HOME must be absolute")
    return config_home / "systemd/user"


def _kwin_script_directory():
    data_home = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
    if not data_home.is_absolute():
        raise ValueError("XDG_DATA_HOME must be absolute")
    return data_home / "kwin/scripts" / PLUGIN_ID


def _run(arguments, purpose):
    result = subprocess.run(arguments, capture_output=True, text=True, timeout=20, check=False)
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()[:1000]
        raise ValueError(f"{purpose} failed: {detail or 'command returned an error'}")
    return result.stdout.strip()


def _configure_kwin(enabled):
    kwriteconfig = shutil.which("kwriteconfig6")
    qdbus = shutil.which("qdbus") or shutil.which("qdbus6")
    kpackagetool = shutil.which("kpackagetool6")
    if not kwriteconfig or not qdbus or not kpackagetool:
        missing = [name for name, path in (("kwriteconfig6", kwriteconfig),
                                           ("qdbus/qdbus6", qdbus),
                                           ("kpackagetool6", kpackagetool)) if not path]
        raise ValueError("Missing KDE command(s): " + ", ".join(missing))
    source = ROOT / "kwin" / PLUGIN_ID
    installed = _kwin_script_directory() / "metadata.json"
    if enabled:
        operation = "--upgrade" if installed.is_file() else "--install"
        _run([kpackagetool, "--type=KWin/Script", operation, str(source)], "KWin script installation")
    _run([kwriteconfig, "--file", "kwinrc", "--group", "Plugins",
          "--key", PLUGIN_ID + "Enabled", "true" if enabled else "false"],
         "KWin observer configuration")
    _run([qdbus, "org.kde.KWin", "/KWin", "reconfigure"], "KWin reconfiguration")


def _service_text():
    python = sys.executable
    environment = quote_unit("BURITO_DATA_DIR=" + str(Memory().directory))
    return ("[Unit]\nDescription=Burito local foreground app collector\nAfter=default.target\n\n"
            "[Service]\nType=simple\n"
            f"WorkingDirectory={working_directory_value(ROOT)}\n"
            f"Environment={environment}\n"
            f"ExecStart={quote_unit(python)} -m burito activity collect\n"
            "Restart=on-failure\nRestartSec=5\nUMask=0077\nNoNewPrivileges=true\n\n"
            "[Install]\nWantedBy=default.target\n")


def enable():
    """Install and enable the user's explicit opt-in KWin observer."""
    if os.environ.get("XDG_SESSION_TYPE", "").lower() != "wayland":
        raise ValueError("The activity observer currently requires a Wayland desktop session")
    directory = _unit_directory()
    directory.mkdir(parents=True, exist_ok=True)
    unit = directory / UNIT_NAME
    unit.write_text(_service_text())
    unit.chmod(0o600)
    _run(["systemctl", "--user", "daemon-reload"], "systemd user manager reload")
    _run(["systemctl", "--user", "enable", "--now", UNIT_NAME], "local activity collector start")
    try:
        _configure_kwin(True)
    except Exception:
        subprocess.run(["systemctl", "--user", "disable", "--now", UNIT_NAME],
                       capture_output=True, text=True, timeout=20, check=False)
        raise
    return "Local activity tracking is enabled. It records app IDs and estimated foreground intervals only."


def pause():
    """Disable the KWin observer and stop its local journal collector."""
    _configure_kwin(False)
    _run(["systemctl", "--user", "disable", "--now", UNIT_NAME], "activity collector pause")
    return "Activity recording paused; stored local summaries remain."


def status():
    result = subprocess.run(["systemctl", "--user", "show", UNIT_NAME,
                             "--property=LoadState,ActiveState,SubState,UnitFileState,Result",
                             "--no-pager"], capture_output=True, text=True, timeout=10, check=False)
    fields = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    config = Path.home() / ".config/kwinrc"
    if os.environ.get("XDG_CONFIG_HOME"):
        config = Path(os.environ["XDG_CONFIG_HOME"]) / "kwinrc"
    enabled = False
    try:
        in_plugins = False
        for line in config.read_text().splitlines():
            stripped = line.strip()
            if stripped.startswith("["):
                in_plugins = stripped == "[Plugins]"
            elif in_plugins and stripped.startswith(PLUGIN_ID + "Enabled="):
                enabled = stripped.split("=", 1)[1].strip().lower() in ("true", "1")
    except OSError:
        pass
    return {"kwin_script_enabled": enabled,
            "collector": fields,
            "collector_active": result.returncode == 0 and fields.get("ActiveState") == "active"}
