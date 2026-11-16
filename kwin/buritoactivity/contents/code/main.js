// Records only the foreground application's desktop ID. Never inspect titles,
// window contents, input, or process command lines.
function appId(window) {
    if (!window || window.specialWindow) {
        return "idle";
    }
    let id = String(window.desktopFileName || "");
    if (!id) {
        return "idle";
    }
    id = id.split("/").pop();
    if (id.toLowerCase().endsWith(".desktop")) {
        id = id.slice(0, -8);
    }
    if (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(id)) {
        return "idle";
    }
    if (/(screen.?locker|screen.?saver|screenlock|lockscreen|greeter)/i.test(id)) {
        return "idle";
    }
    return id;
}

function recordForeground(window) {
    print("BURITO_ACTIVITY:" + appId(window));
}

workspace.windowActivated.connect(recordForeground);
recordForeground(workspace.activeWindow);
