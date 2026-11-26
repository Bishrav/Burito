#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/burito"
mkdir -p "$state_dir"
url="http://127.0.0.1:8765"

if ! curl --silent --fail "$url/api/status" >/dev/null 2>&1; then
  if [[ -s "$state_dir/web.pid" ]] && kill -0 "$(cat "$state_dir/web.pid")" 2>/dev/null; then
    echo "Burito web is starting; waiting for its local health endpoint..."
  else
    echo "Starting Burito’s local model and desktop console..."
    (cd "$repo_root" && nohup setsid python3 -m burito web --model "${BURITO_WEB_MODEL:-burito-local:latest}" --context-tokens 8192 \
      --include-project --include-experiences --include-academy \
      >"$state_dir/web.log" 2>&1 </dev/null & echo $! >"$state_dir/web.pid")
  fi
  for _ in {1..90}; do
    if curl --silent --fail "$url/api/status" >/dev/null 2>&1; then break; fi
    sleep 1
  done
fi

if ! curl --silent --fail "$url/api/status" >/dev/null 2>&1; then
  echo "Burito did not become ready. See $state_dir/web.log" >&2
  exit 1
fi

for browser in brave-browser chromium chromium-browser google-chrome; do
  if command -v "$browser" >/dev/null 2>&1; then
    exec "$browser" --app="$url" --class=Burito
  fi
done
exec xdg-open "$url"
