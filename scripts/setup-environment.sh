#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
version=0.40.18
ollama_dir="$PWD/.tools/ollama-$version"
export OLLAMA_HOST=127.0.0.1:11434
export OLLAMA_NO_CLOUD=1
export OLLAMA_NUM_PARALLEL=1
export OLLAMA_MODELS="$PWD/models/ollama"

case "${1:---check}" in
    --check)
        python3 --version
        node --version
        npm --version
        python3 -c 'import sqlite3, sys; assert sys.version_info >= (3, 11); print("Python SQLite", sqlite3.sqlite_version)'
        node -e 'if (+process.versions.node.split(".")[0] < 24) process.exit(1)'
        python3 - <<'PY'
import json
from pathlib import Path
import sys

failed = False
for name in ("runtime/package.json", "runtime/package-lock.json"):
    try:
        json.loads(Path(name).read_text(encoding="utf-8"))
    except (UnicodeError, ValueError) as exc:
        print(f"{name}: invalid UTF-8 JSON ({exc})", file=sys.stderr)
        failed = True
sys.exit(failed)
PY
        ;;
    --python)
        python3 -m venv .venv
        .venv/bin/python -m pip --no-cache-dir check
        ;;
    --runtime)
        bash scripts/setup-environment.sh --check
        npm --prefix runtime ci --cache "$PWD/.tools/npm-cache" --no-audit --no-fund
        export EVE_TELEMETRY_DISABLED=1 EVE_TRACES_CONTENT=off
        npm --prefix runtime run check:discovery
        npm --prefix runtime test
        ;;
    --install-ollama)
        if command -v ollama >/dev/null || [[ -x "$ollama_dir/bin/ollama" ]]; then
            echo 'Ollama already installed.'
            exit 0
        fi
        [[ "$(uname -s):$(uname -m)" == Linux:x86_64 ]]
        mkdir -p .tools
        staging=$(mktemp -d "$PWD/.tools/ollama-install.XXXXXXXX")
        trap 'rm -rf -- "$staging"' EXIT
        asset=ollama-linux-amd64.tar.zst
        curl --fail --silent --show-error --location --proto '=https' --proto-redir '=https' --retry 2 \
            "https://github.com/ollama/ollama/releases/download/v$version/$asset" -o "$staging/$asset"
        printf '%s  %s\n' b82649006cb5b54ed1237fa2d1a26a7f939a4fd03150033759acbff7ff315adf "$staging/$asset" | sha256sum -c -
        mkdir "$staging/install"
        tar --zstd --extract --file "$staging/$asset" --directory "$staging/install" --no-same-owner --no-same-permissions
        test -x "$staging/install/bin/ollama"
        mv -nT -- "$staging/install" "$ollama_dir"
        ;;
    --serve|--ollama)
        mode=$1
        shift
        ollama_bin=$(command -v ollama || printf '%s\n' "$ollama_dir/bin/ollama")
        if [[ "$mode" == --serve ]]; then
            umask 077
            mkdir -p "$OLLAMA_MODELS"
            exec "$ollama_bin" serve
        fi
        exec "$ollama_bin" "$@"
        ;;
    *)
        echo 'Usage: setup-environment.sh [--check|--python|--runtime|--install-ollama|--serve|--ollama COMMAND]' >&2
        exit 2
        ;;
esac
