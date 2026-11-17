#!/usr/bin/env bash
set -euo pipefail

repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
expected="$(realpath -- "$HOME/Burito")"
[[ "$repo" == "$expected" ]] || {
  printf 'Expected Burito checkout at %s, found %s\n' "$expected" "$repo" >&2
  exit 1
}
[[ -d "$repo/.git" ]] || { printf 'This is not a Git checkout: %s\n' "$repo" >&2; exit 1; }

unit_dir="$HOME/.config/systemd/user"
mkdir -p "$unit_dir"
install -m 0644 "$repo/systemd/burito-auto-update.service" "$unit_dir/burito-auto-update.service"
install -m 0644 "$repo/systemd/burito-auto-update.timer" "$unit_dir/burito-auto-update.timer"
chmod 0755 "$repo/scripts/auto-update.sh"

systemctl --user daemon-reload
systemctl --user enable --now burito-auto-update.timer
systemctl --user start burito-auto-update.service
systemctl --user status burito-auto-update.timer --no-pager
