"""Desktop provider selection and one-shot Hyprland IPC."""

import json
import os
import re
import subprocess
import time

from . import windows as kwin

HYPRLAND_ID = re.compile(r"hyprland:[1-9][0-9]{0,18}")


def provider():
    if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
        return "hyprland"
    return "kwin"


def _hyprctl(*args):
    try:
        result = subprocess.run(
            ["hyprctl", *args], capture_output=True, text=True, timeout=3, check=True
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise kwin.WindowBridgeError("Hyprland IPC is unavailable.") from error
    if len(result.stdout) > kwin.MAX_REPORT_BYTES:
        raise kwin.WindowBridgeError("Hyprland window response exceeds the size limit.")
    return result.stdout


def _hypr_json(command, expected):
    try:
        result = json.loads(_hyprctl("-j", command))
    except ValueError as error:
        if isinstance(error, kwin.WindowBridgeError):
            raise
        raise kwin.WindowBridgeError("Hyprland returned invalid window data.") from error
    if not isinstance(result, expected):
        raise kwin.WindowBridgeError("Hyprland returned unexpected window data.")
    return result


def _hyprland_row(client, active_id, workspace_id):
    stable_id = str(client.get("stableId"))
    internal_id = f"hyprland:{stable_id}"
    if not HYPRLAND_ID.fullmatch(internal_id):
        return None
    workspace = client.get("workspace") or {}
    return {
        "internalId": internal_id,
        "resourceClass": str(client.get("class") or "")[:220],
        "caption": str(client.get("title") or "")[:300],
        "desktop": workspace.get("name"),
        "minimized": None,
        "active": stable_id == str(active_id),
        "onCurrentDesktop": workspace.get("id") == workspace_id,
    }


def list_windows():
    if provider() == "kwin":
        return {**kwin.list_windows(), "provider": "kwin"}
    clients = _hypr_json("clients", list)
    active = _hypr_json("activewindow", dict)
    workspace = _hypr_json("activeworkspace", dict)
    windows = []
    for client in clients[:100]:
        if isinstance(client, dict) and client.get("mapped") is True:
            row = _hyprland_row(client, active.get("stableId"), workspace.get("id"))
            if row is not None:
                windows.append(row)
    return {
        "provider": "hyprland", "windows": windows,
        "scope": "Current Hyprland-managed windows with stable IDs.",
        "note": "An absent window does not establish that its process has stopped.",
    }


def focus_window(internal_id):
    if provider() == "kwin":
        return kwin.focus_window(internal_id)
    if not isinstance(internal_id, str) or not HYPRLAND_ID.fullmatch(internal_id):
        raise kwin.WindowBridgeError("Invalid Hyprland window ID; list windows again.")
    if not any(row["internalId"] == internal_id for row in list_windows()["windows"]):
        raise kwin.WindowBridgeError("Hyprland window no longer exists; list windows again.")
    stable_id = internal_id.split(":")[1]
    answer = _hyprctl("eval", f'hl.dispatch(hl.dsp.focus({{ window = "stableid:{stable_id}" }}))')
    if answer.strip().lower() != "ok":
        raise kwin.WindowBridgeError("Hyprland did not accept the focus request.")
    for _ in range(5):
        active = _hypr_json("activewindow", dict)
        if str(active.get("stableId")) == stable_id:
            workspace = active.get("workspace") or {}
            row = _hyprland_row(active, active["stableId"], workspace.get("id"))
            return {"status": "focused", "window": row}
        time.sleep(0.1)
    raise kwin.WindowBridgeError("Hyprland did not confirm the window became active.")
