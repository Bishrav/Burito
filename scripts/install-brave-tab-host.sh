#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || ! "$1" =~ ^[a-p]{32}$ ]]; then
  echo "Usage: $0 <32-character-extension-id>" >&2
  exit 2
fi

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXTENSION_ID="$1"
HOST_PATH="$PROJECT_ROOT/scripts/brave-tab-host.py"
HOST_NAME="com.burito.brave_tabs"
chmod +x "$HOST_PATH"

for BROWSER_DIR in "$HOME/.config/BraveSoftware/Brave-Origin/NativeMessagingHosts"; do
  mkdir -p "$BROWSER_DIR"
  python3 - "$BROWSER_DIR/$HOST_NAME.json" "$HOST_PATH" "$EXTENSION_ID" <<'PY'
import json
import os
import sys

path, host_path, extension_id = sys.argv[1:]
temporary = path + '.tmp'
with open(temporary, 'w', encoding='utf-8') as output:
    json.dump({
        'name': 'com.burito.brave_tabs',
        'description': 'Shares only the Brave tab count with Burito',
        'path': host_path,
        'type': 'stdio',
        'allowed_origins': [f'chrome-extension://{extension_id}/'],
    }, output, separators=(',', ':'))
    output.write('\n')
os.chmod(temporary, 0o600)
os.replace(temporary, path)
PY
done

echo "Installed the local tab-count host for Brave Origin."
echo "It stores only a short-lived count in XDG_RUNTIME_DIR, never tab titles or URLs."