#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

python3 - "${PROJECT_ROOT}" <<'PY'
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import uuid

sys.path.insert(0, sys.argv[1])
from burito.windows import _kwin_script

try:
    import dbus
    import dbus.service
    from dbus.mainloop.glib import DBusGMainLoop
    from gi.repository import GLib
except ImportError as error:
    raise SystemExit(f"Python D-Bus/GLib bindings are required: {error}")

dbus_send = shutil.which("dbus-send")
if not dbus_send:
    raise SystemExit("dbus-send is required.")

DBusGMainLoop(set_as_default=True)
token = uuid.uuid4().hex
script_name = "burito-probe-" + token
service_name = "org.burito.Windows.Probe" + token
bus = dbus.SessionBus()
bus_name = dbus.service.BusName(service_name, bus=bus, do_not_queue=True)
loop = GLib.MainLoop()
received = {"payload": None}


class ProbeReceiver(dbus.service.Object):
    @dbus.service.method("org.burito.Windows", in_signature="s", out_signature="")
    def report(self, payload):
        received["payload"] = str(payload)
        loop.quit()


receiver = ProbeReceiver(bus_name, "/")


def call_kwin(path, interface, method, arguments=(), timeout=5, print_reply=True):
    command = [dbus_send, "--session"]
    if print_reply:
        command.append("--print-reply=literal")
    command.extend(["--dest=org.kde.KWin", path, interface + "." + method])
    command.extend("string:" + str(value) for value in arguments)
    result = subprocess.run(command, capture_output=True, text=True,
                            timeout=timeout, check=False)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout).strip()[:500]
                           or "KWin D-Bus call failed")
    return result.stdout.strip()


def unload():
    try:
        call_kwin("/Scripting", "org.kde.kwin.Scripting", "unloadScript",
                  (script_name,), timeout=2)
    except Exception as error:
        print(f"unload result: failed ({str(error)[:300]})")
    else:
        print("unload result: called")


try:
    run_error = None
    callback_wait = False
    with tempfile.TemporaryDirectory(prefix="burito-kwin-probe-") as directory:
        os.chmod(directory, 0o700)
        script_path = Path(directory) / "main.js"
        script_path.write_text(
            _kwin_script("list", token, service_name), encoding="utf-8")
        unload()
        try:
            reply = call_kwin("/Scripting", "org.kde.kwin.Scripting", "loadScript",
                              (str(script_path), script_name))
        except Exception as error:
            run_error = str(error)[:300]
            print("load id: unavailable")
            print("run result: not attempted (load failed)")
        else:
            match = re.search(r"\bint32\s+(-?\d+)", reply)
            if not match:
                match = re.search(r"(?<!\S)(-?\d+)(?!\S)", reply)
            if not match:
                run_error = "KWin returned no script ID"
                print(f"load id: unavailable (reply: {reply})")
                print("run result: not attempted")
            else:
                script_id = int(match.group(1))
                print(f"load id: {script_id}")
                if script_id < 0:
                    run_error = "KWin returned a negative load id"
                    print("run result: not attempted (KWin rejected the script)")
                else:
                    try:
                        call_kwin(f"/Scripting/Script{script_id}", "org.kde.kwin.Script",
                                  "run", timeout=5)
                    except RuntimeError as error:
                        detail = str(error).casefold()
                        if any(marker in detail for marker in
                               ("unknownobject", "unknown object", "no such object")):
                            try:
                                call_kwin(f"/{script_id}", "org.kde.kwin.Script", "run",
                                          timeout=5)
                            except Exception as fallback_error:
                                run_error = str(fallback_error)[:300]
                                print(f"run result: failed ({run_error})")
                            else:
                                print("run result: success (Plasma 5 fallback path)")
                                callback_wait = True
                        else:
                            run_error = str(error)[:300]
                            print(f"run result: failed ({run_error})")
                    else:
                        print("run result: success (Plasma 6 path)")
                        callback_wait = True

        if callback_wait:
            GLib.timeout_add(5000, lambda: (loop.quit(), False)[1])
            loop.run()
        if received["payload"] is None:
            reason = " (5 second timeout)" if callback_wait else " (run not completed)"
            print("callback arrived: no" + reason)
            print("raw payload: <none>")
        else:
            print("callback arrived: yes")
            print("raw payload: " + received["payload"])
    if run_error:
        raise SystemExit(1)
finally:
    unload()
    try:
        receiver.remove_from_connection()
    except Exception:
        pass
    try:
        bus_name.release()
        bus.close()
    except Exception:
        pass
PY
