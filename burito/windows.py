"""On-demand KWin window snapshots and approval-gated focus requests."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import uuid


WINDOW_ID = re.compile(r"^[0-9a-fA-F-]{36}$")
MAX_REPORT_BYTES = 256_000
DEFAULT_TIMEOUT = 5.0


class WindowBridgeError(ValueError):
    """A KWin request failed, with its completed stages included in the message."""


class KWinDBusError(WindowBridgeError):
    pass


def _js_string(value):
    return json.dumps(str(value), ensure_ascii=True)


def _kwin_script(action, token, result_service, internal_id=None):
    """Build a one-shot script that reports results through the private D-Bus service."""
    encoded_token = _js_string(token)
    encoded_service = _js_string(result_service)
    script = '''
function report(result) {
  result.token = TOKEN;
  callDBus(SERVICE, "/", "org.burito.Windows", "report", JSON.stringify(result), function() {});
}
function getWindows() {
  if (typeof workspace.windowList === "function") return workspace.windowList();
  if (typeof workspace.clientList === "function") return workspace.clientList();
  throw new Error("KWin exposes neither workspace.windowList() nor clientList().");
}
function row(w) {
  let desktop = null;
  try {
    if (w.desktop) desktop = String(w.desktop.name || w.desktop.id || w.desktop);
  } catch (e) {}
  return {
    internalId: String(w.internalId).replace(/[{}]/g, ""),
    resourceClass: String(w.resourceClass || w.resourceName || ""),
    caption: String(w.caption || "").slice(0, 300),
    desktop: desktop,
    minimized: !!w.minimized,
    onCurrentDesktop: !!w.onCurrentDesktop,
    active: !!w.active
  };
}
const TOKEN = ''' + encoded_token + ''';
const SERVICE = ''' + encoded_service + ''';
try {
'''
    if action == "list":
        script += '''
  const windows = getWindows().filter(w => !!w).map(row);
  report({ok: true, windows: windows.slice(-100)});
'''
    elif action == "focus":
        script += '''
  const targetId = ''' + _js_string(internal_id) + ''';
  const target = getWindows().find(w => w && String(w.internalId).replace(/[{}]/g, "") === targetId);
  if (!target) {
    report({ok: false, error: "Window ID no longer exists."});
  } else {
    if (target.minimized) target.minimized = false;
    workspace.activeWindow = target;
    report({ok: true, window: row(target)});
  }
'''
    else:
        raise ValueError("Unknown KWin window action")
    script += '''
} catch (e) {
  report({ok: false, error: String(e).slice(0, 300)});
}
'''
    return script


class _ReportInbox:
    """Correlate one-shot JSON reports; mismatched tokens are ignored."""

    def __init__(self, token):
        self.token = token
        self.payload = None
        self.ready = False

    def receive(self, raw_payload):
        if not isinstance(raw_payload, str) or len(raw_payload.encode("utf-8")) > MAX_REPORT_BYTES:
            return False
        try:
            payload = json.loads(raw_payload)
        except (json.JSONDecodeError, UnicodeError):
            return False
        if not isinstance(payload, dict) or payload.get("token") != self.token:
            return False
        if not isinstance(payload.get("ok"), bool):
            payload = {"token": self.token, "ok": False, "error": "KWin sent an invalid report."}
        self.payload = payload
        self.ready = True
        return True


class _DBusReportChannel:
    """Short-lived D-Bus service that receives reports while GLib dispatches."""

    def __init__(self, token):
        try:
            import dbus
            import dbus.service
            from dbus.mainloop.glib import DBusGMainLoop
            from gi.repository import GLib
        except ImportError as error:
            raise WindowBridgeError(
                "Python D-Bus and GLib bindings are required for the KWin window bridge."
            ) from error

        DBusGMainLoop(set_as_default=True)
        self._dbus = dbus
        self._glib = GLib
        self.inbox = _ReportInbox(token)
        self.loop = GLib.MainLoop()
        self.service_name = "org.burito.Windows.R" + token
        try:
            self.bus = dbus.SessionBus()
            self.bus_name = dbus.service.BusName(
                self.service_name, bus=self.bus, do_not_queue=True)
        except dbus.DBusException as error:
            raise WindowBridgeError("Could not register Burito's temporary window-result service.") from error

        inbox = self.inbox
        loop = self.loop

        class ResultReceiver(dbus.service.Object):
            @dbus.service.method("org.burito.Windows", in_signature="s", out_signature="")
            def report(self, payload):
                if inbox.receive(str(payload)):
                    loop.quit()

        try:
            self.receiver = ResultReceiver(self.bus_name, "/")
        except Exception:
            self.bus_name.release()
            raise

    def wait(self, timeout):
        if self.inbox.ready:
            return self.inbox.payload
        if timeout <= 0:
            return None

        def on_timeout():
            self.loop.quit()
            return False

        timer_id = self._glib.timeout_add(max(1, int(timeout * 1000)), on_timeout)
        try:
            self.loop.run()
        finally:
            try:
                self._glib.source_remove(timer_id)
            except Exception:
                pass
        return self.inbox.payload if self.inbox.ready else None

    def close(self):
        try:
            self.receiver.remove_from_connection()
        except Exception:
            pass
        try:
            self.bus_name.release()
        except Exception:
            pass
        try:
            self.bus.close()
        except Exception:
            pass


class _KWinDBus:
    def __init__(self, dbus_send):
        self.dbus_send = dbus_send

    def _call(self, path, interface, method, arguments=(), timeout=2.0,
              print_reply=True):
        command = [self.dbus_send, "--session"]
        if print_reply:
            command.append("--print-reply=literal")
        command.extend(["--dest=org.kde.KWin", path, interface + "." + method])
        command.extend("string:" + str(argument) for argument in arguments)
        try:
            result = subprocess.run(command, capture_output=True, text=True,
                                    timeout=max(0.1, timeout), check=False)
        except subprocess.TimeoutExpired as error:
            raise KWinDBusError("D-Bus call to KWin timed out.") from error
        if result.returncode:
            detail = (result.stderr or result.stdout).strip()[:300]
            raise KWinDBusError(detail or "D-Bus call to KWin failed.")
        return result.stdout.strip()

    def unload(self, script_name, timeout=1.0):
        self._call("/Scripting", "org.kde.kwin.Scripting", "unloadScript",
                   (script_name,), timeout=timeout)

    def load(self, script_path, script_name, timeout=2.0):
        reply = self._call("/Scripting", "org.kde.kwin.Scripting", "loadScript",
                           (script_path, script_name), timeout=timeout)
        match = re.search(r"\bint32\s+(-?\d+)", reply)
        if not match:
            match = re.search(r"(?<!\S)(-?\d+)(?!\S)", reply)
        if not match:
            raise KWinDBusError("KWin returned no script ID from loadScript().")
        return int(match.group(1))

    def run(self, script_id, timeout=2.0):
        try:
            self._call(f"/Scripting/Script{script_id}", "org.kde.kwin.Script",
                       "run", timeout=timeout)
            return "plasma6"
        except KWinDBusError as error:
            detail = str(error).casefold()
            if not any(marker in detail for marker in
                       ("unknownobject", "unknown object", "no such object")):
                raise
            self._call(f"/{script_id}", "org.kde.kwin.Script", "run",
                       timeout=timeout)
            return "plasma5-fallback"


def _stage_text(stage):
    return (f"loaded_id={stage['loaded_id']}, run_called={str(stage['run_called']).lower()}, "
            f"report_received={str(stage['report_received']).lower()}")


def _perform_request(action, token, script_name, script_path, transport, channel,
                     internal_id=None, timeout=DEFAULT_TIMEOUT, clock=time.monotonic):
    """Run the lifecycle against injected transport/channel interfaces."""
    deadline = clock() + timeout
    stage = {"loaded_id": None, "run_called": False, "report_received": False}
    primary_error = None
    result = None

    def remaining():
        value = deadline - clock()
        if value <= 0:
            raise WindowBridgeError(f"KWin window request timed out ({_stage_text(stage)}).")
        return value

    try:
        transport.unload(script_name, timeout=min(1.0, remaining()))
        stage["loaded_id"] = transport.load(script_path, script_name, timeout=remaining())
        if stage["loaded_id"] < 0:
            raise WindowBridgeError(
                f"KWin rejected the temporary script with load id {stage['loaded_id']} "
                f"({_stage_text(stage)}).")
        stage["run_called"] = True
        transport.run(stage["loaded_id"], timeout=remaining())

        while True:
            report = channel.wait(remaining())
            if report is None:
                raise WindowBridgeError(f"KWin window request timed out ({_stage_text(stage)}).")
            if not isinstance(report, dict) or report.get("token") != token:
                continue
            stage["report_received"] = True
            result = report
            if not isinstance(report.get("ok"), bool):
                raise WindowBridgeError(
                    f"KWin returned an invalid report ({_stage_text(stage)}).")
            if not report["ok"]:
                detail = str(report.get("error", "KWin script reported failure."))[:300]
                raise WindowBridgeError(f"{detail} ({_stage_text(stage)}).")
            break
    except Exception as error:
        primary_error = error
    finally:
        try:
            transport.unload(script_name, timeout=1.0)
        except Exception as cleanup_error:
            if primary_error is None:
                primary_error = WindowBridgeError(
                    f"KWin returned a result but unloadScript() cleanup failed: {str(cleanup_error)[:300]} "
                    f"({_stage_text(stage)}).")

    if primary_error is not None:
        if isinstance(primary_error, WindowBridgeError):
            raise primary_error
        raise WindowBridgeError(
            f"KWin request failed: {str(primary_error)[:300]} ({_stage_text(stage)})."
        ) from primary_error
    return result


def _request(action, internal_id=None, timeout=DEFAULT_TIMEOUT):
    session_type = os.environ.get("XDG_SESSION_TYPE")
    if session_type and session_type != "wayland":
        raise WindowBridgeError("The KWin window bridge currently requires a KDE Wayland session.")
    dbus_send = shutil.which("dbus-send")
    if not dbus_send:
        raise WindowBridgeError("dbus-send is required for the KDE window bridge.")

    token = uuid.uuid4().hex
    script_name = "burito-once-" + token
    channel = _DBusReportChannel(token)
    try:
        with tempfile.TemporaryDirectory(prefix="burito-kwin-") as directory:
            os.chmod(directory, 0o700)
            script_path = Path(directory) / "main.js"
            script_path.write_text(
                _kwin_script(action, token, channel.service_name, internal_id),
                encoding="utf-8")
            return _perform_request(
                action, token, script_name, str(script_path), _KWinDBus(dbus_send),
                channel, internal_id=internal_id, timeout=timeout)
    finally:
        channel.close()


def list_windows():
    """Return a transient snapshot; captions are not written to logs or storage."""
    result = _request("list")
    windows = result.get("windows")
    if not isinstance(windows, list):
        raise WindowBridgeError("KWin returned a window report without a windows list.")
    return {
        "windows": windows,
        "scope": "Current KWin-managed application windows; captions are returned only for this request.",
        "note": "A missing window can mean the app has no KWin-managed window, including tray-only or background apps; it does not prove the process is stopped.",
    }


def focus_window(internal_id):
    """Focus one exact KWin window. Caller enforces explicit owner approval."""
    if not isinstance(internal_id, str) or not WINDOW_ID.fullmatch(internal_id):
        raise WindowBridgeError("Invalid internal window ID; list windows again.")
    result = _request("focus", internal_id=internal_id)
    window = result.get("window")
    if not isinstance(window, dict) or window.get("internalId") != internal_id:
        raise WindowBridgeError("KWin did not confirm focus for the requested window ID.")
    return {"status": "focused", "window": window}


def focus_and_read_window(internal_id):
    """Focus one approved window, then use the separate approved local OCR path."""
    from .access import read_screen_text
    focused = focus_window(internal_id)
    capture = read_screen_text("active_window")
    return {"status": "focused_and_captured", "window": focused["window"],
            "capture": capture}
