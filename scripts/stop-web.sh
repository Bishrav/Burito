#!/usr/bin/env bash
set -euo pipefail
state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/burito"
pid_file="$state_dir/web.pid"
if [[ ! -s "$pid_file" ]]; then
  echo "No Burito desktop server PID file found."
  exit 0
fi
pid="$(cat "$pid_file")"
if kill -0 "$pid" 2>/dev/null; then
  group="$(ps -o pgid= -p "$pid" | tr -d ' ')"
  if [[ "$group" == "$pid" ]]; then kill -- "-$group"; else kill "$pid"; fi
  echo "Stopped Burito desktop server."
else
  echo "Burito desktop server was already stopped."
fi
rm -f "$pid_file"
