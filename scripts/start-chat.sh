#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if [[ -z "${BURITO_DATA_DIR:-}" ]]; then
  export BURITO_DATA_DIR="/mnt/burito-brain/memory"
fi

# Do not silently put Burito's persistent memory on the system disk if the
# dedicated brain drive is disconnected.
if [[ "$BURITO_DATA_DIR" == "/mnt/burito-brain/memory" ]] && ! mountpoint -q /mnt/burito-brain; then
  echo "Burito brain storage is not mounted at /mnt/burito-brain; connect it before starting chat." >&2
  exit 1
fi

exec python3 -m burito chat \
  --model burito-local:latest \
  --context-tokens 8192 \
  --enable-brave-tabs \
  --enable-browser-control \
  --enable-desktop-control \
  --enable-screen-read \
  --enable-browser-search \
  "$@"
