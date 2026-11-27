#!/usr/bin/env bash
set -euo pipefail

root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
tools="$root/.tools"
source_dir="$tools/whisper.cpp"
build_env="$tools/phase4-build-env"
mount=/mnt/burito-brain
expected_uuid=9428a980-24a6-45b2-a0a6-5e057c819406
source_commit=79b11911d9d38c4be2fc7dc8b4efeff3324c090f
model_dir="$mount/models/audio"
model="$model_dir/ggml-base.bin"
model_sha1=465707469ff3a37a2b9b8d8f89f2f99de7299dac
model_sha256=60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe

for tool in git curl sha1sum sha256sum findmnt uv; do
  command -v "$tool" >/dev/null || { printf 'Missing required setup tool: %s\n' "$tool" >&2; exit 1; }
done

mount_info="$(findmnt --mountpoint "$mount" --noheadings --output UUID,FSTYPE,OPTIONS)"
read -r actual_uuid filesystem mount_options <<<"$mount_info"
[[ "$actual_uuid" == "$expected_uuid" && "$filesystem" == ext4 && ",${mount_options}," == *,rw,* ]] || {
  printf 'BURITO_BRAIN identity, filesystem, or read/write state is not verified at %s; refusing model writes.\n' "$mount" >&2
  exit 1
}
[[ ! -L "$mount" && ! -L "$mount/models" && ! -L "$model_dir" ]] || {
  printf 'Model directory contains a symlink; refusing to write: %s\n' "$model_dir" >&2
  exit 1
}
mkdir -p -- "$model_dir"
[[ -d "$model_dir" && -w "$model_dir" ]] || {
  printf 'Expected writable model directory is unavailable: %s\n' "$model_dir" >&2
  exit 1
}

mkdir -p -- "$tools"
if [[ ! -e "$source_dir" ]]; then
  git init --quiet "$source_dir"
  git -C "$source_dir" remote add origin https://github.com/ggml-org/whisper.cpp.git
  git -C "$source_dir" fetch --depth=1 origin "$source_commit"
  git -C "$source_dir" checkout --quiet --detach FETCH_HEAD
fi
[[ "$(git -C "$source_dir" rev-parse HEAD)" == "$source_commit" ]] || {
  printf 'Existing whisper.cpp checkout differs from pinned commit; refusing to replace it.\n' >&2
  exit 1
}

if command -v cmake >/dev/null; then
  cmake_bin="$(command -v cmake)"
else
  [[ -x "$build_env/bin/cmake" ]] || {
    uv venv "$build_env" --python 3.11
    uv pip install --python "$build_env/bin/python" cmake==4.4.5
  }
  cmake_bin="$build_env/bin/cmake"
fi

"$cmake_bin" -S "$source_dir" -B "$source_dir/build" \
  -DCMAKE_BUILD_TYPE=Release -DGGML_CUDA=OFF \
  -DWHISPER_BUILD_TESTS=OFF -DWHISPER_BUILD_EXAMPLES=ON -DWHISPER_BUILD_SERVER=OFF
"$cmake_bin" --build "$source_dir/build" --config Release --parallel 8 --target whisper-cli

if [[ -e "$model" ]]; then
  printf '%s  %s\n' "$model_sha1" "$model" | sha1sum --check --status || {
    printf 'Existing model checksum differs; leaving it untouched.\n' >&2
    exit 1
  }
  printf '%s  %s\n' "$model_sha256" "$model" | sha256sum --check --status || {
    printf 'Existing model SHA-256 differs; leaving it untouched.\n' >&2
    exit 1
  }
elif [[ -e "$model.part" ]]; then
  printf 'Partial model file already exists; inspect it before retrying: %s\n' "$model.part" >&2
  exit 1
else
  curl --fail --location --retry 2 --output "$model.part" \
    https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin
  printf '%s  %s\n' "$model_sha1" "$model.part" | sha1sum --check
  printf '%s  %s\n' "$model_sha256" "$model.part" | sha256sum --check
  [[ ! -e "$model" ]] || { printf 'Model appeared during download; refusing to overwrite it.\n' >&2; exit 1; }
  mv --no-clobber -- "$model.part" "$model"
  chmod 600 "$model"
fi

printf 'ASR ready: %s\n' "$source_dir/build/bin/whisper-cli"
printf 'Model: %s\n' "$model"
printf 'Set BURITO_WHISPER_CLI and BURITO_WHISPER_MODEL only to override these defaults.\n'
