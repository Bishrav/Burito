#!/usr/bin/env bash
# Run in a normal Kubuntu terminal. Installs only into this checkout.
set -euo pipefail
burito_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
burito_node_version="v26.13.1"

if [[ "${1:-}" == "--check" ]]; then
    cd -- "$burito_root"
    exec python3 -m burito doctor
fi
if [[ $# -gt 0 ]]; then
    echo 'Usage: bash scripts/setup-runtime.sh [--check]' >&2
    exit 2
fi

for burito_dependency in curl tar sha256sum python3; do
    if ! command -v "$burito_dependency" >/dev/null 2>&1; then
        echo "Missing required command: $burito_dependency" >&2
        exit 1
    fi
done

burito_use_system_node=false
if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
    if node -e 'process.exit(Number(process.versions.node.split(".")[0]) >= 24 ? 0 : 1)'; then
        burito_use_system_node=true
    fi
fi

if [[ "$burito_use_system_node" != true ]]; then
    case "$(uname -m)" in
        x86_64) burito_arch=x64 ;;
        aarch64) burito_arch=arm64 ;;
        *) echo 'Automatic Node setup supports Linux x86_64 and aarch64 only.' >&2; exit 1 ;;
    esac
    [[ "$(uname -s)" == Linux ]] || { echo 'This installer targets Linux.' >&2; exit 1; }
    burito_archive="node-${burito_node_version}-linux-${burito_arch}.tar.xz"
    burito_node_dir="$burito_root/.tools/node-${burito_node_version}-linux-${burito_arch}"
    if [[ ! -x "$burito_node_dir/bin/node" ]]; then
        burito_temp="$(mktemp -d)"
        trap 'rm -rf -- "$burito_temp"' EXIT
        echo "Downloading Node ${burito_node_version} from nodejs.org; no sudo or system changes."
        if ! curl --fail --show-error --silent --location --proto '=https' --proto-redir '=https' \
            --connect-timeout 10 --max-time 600 \
            "https://nodejs.org/dist/${burito_node_version}/${burito_archive}" \
            -o "$burito_temp/$burito_archive"; then
            echo 'Download failed. Run this command in your normal terminal with internet access.' >&2
            exit 1
        fi
        curl --fail --show-error --silent --location --proto '=https' --proto-redir '=https' \
            --connect-timeout 10 --max-time 60 \
            "https://nodejs.org/dist/${burito_node_version}/SHASUMS256.txt" \
            -o "$burito_temp/SHASUMS256.txt"
        python3 - "$burito_temp" "$burito_archive" <<'PY'
import hashlib
from pathlib import Path
import sys

directory, filename = Path(sys.argv[1]), sys.argv[2]
checksums = {}
for line in (directory / 'SHASUMS256.txt').read_text().splitlines():
    digest, name = line.split()
    checksums[name.lstrip('*')] = digest
with (directory / filename).open('rb') as archive:
    actual = hashlib.file_digest(archive, 'sha256').hexdigest()
if checksums.get(filename) != actual:
    raise SystemExit('Node archive checksum mismatch; nothing was extracted.')
PY
        # Extract a verified official archive into staging before installing it.
        tar --extract --xz --file "$burito_temp/$burito_archive" \
            --directory "$burito_temp" --no-same-owner --no-same-permissions
        mkdir -p -- "$burito_root/.tools"
        if [[ -e "$burito_node_dir" ]]; then
            echo "Incomplete Node destination exists; inspect it before retrying: $burito_node_dir" >&2
            exit 1
        fi
        mv -- "$burito_temp/node-${burito_node_version}-linux-${burito_arch}" "$burito_node_dir"
    fi
    export PATH="$burito_node_dir/bin:$PATH"
fi

cd -- "$burito_root/runtime"
export npm_config_fetch_retries=1
export npm_config_fetch_timeout=60000
if [[ -f package-lock.json ]]; then
    npm ci --no-audit --no-fund
else
    npm install --save-exact --no-audit --no-fund eve@latest ai@latest zod@latest @ai-sdk/openai-compatible@latest
fi
if [[ ! -d node_modules/@ai-sdk/openai-compatible ]]; then
    npm install --save-exact --no-audit --no-fund @ai-sdk/openai-compatible@latest
fi
echo 'Runtime packages installed. No agent or cloud model has been started.'
echo 'Next: inspect runtime/node_modules/eve/docs/README.md and select a model.'
echo 'A local Node installation does not change your shell profile or system Node.'
echo 'Keep runtime/package.json and runtime/package-lock.json for the next development step and commit after review.'
