#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
applications_dir="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
mkdir -p "$applications_dir"
cat >"$applications_dir/burito.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Burito Assistant
Comment=Start Burito and open its local assistant console
Exec=$repo_root/scripts/open-ui.sh
Icon=applications-internet
Terminal=false
Categories=Utility;System;
StartupNotify=true
EOF
chmod +x "$repo_root/scripts/open-ui.sh" "$repo_root/scripts/stop-web.sh"
echo "Installed Burito Assistant in the application menu. Search for ‘Burito Assistant’ to open it."
