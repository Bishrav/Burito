# Burito environment on Ryoku and CachyOS

Audit performed on 2026-11-25 against GitHub HEAD `35d7f6b`. The setup commands below run from the checkout with the existing shell and toolchain.

## Reproduce the setup

Run `python3 scripts/check-source-integrity.py` with Node 26 on PATH before installing dependencies. The failure notes below describe the original audit of `35d7f6b`. See the recovery report for the corrected tree.

```bash
bash scripts/setup-environment.sh --check
bash scripts/setup-environment.sh --python
uv pip check --python .venv/bin/python
bash scripts/setup-environment.sh --runtime
```

The first command validates interpreter versions and parses the tracked npm manifests. The Python command creates a checkout-local environment with pip seeded by the installed interpreter. The runtime command installs from the checked-in npm lockfile and runs eve discovery and the Node test suite with discovery telemetry disabled. These commands can be run separately.

On this revision, `--check` and `--runtime` stop at the invalid npm manifest. Direct `npm ci` also rejects the lockfile. The Python foundation has no third-party dependencies, but its current suite reports 25 test entries with four import errors and one skip. Multiple tracked files contain invalid UTF-8 across Python, the runtime, and the browser extension. The manifest fetched directly from GitHub hashes to the same blob as the local manifest. The most recent fully readable revision is `c6ec1a5`, three commits before HEAD. In a temporary checkout, it passed 56 Python tests and locked npm installation. Eve discovery ran and two of six Node tests failed on desktop-tool registration and the application execution handler. For an earlier baseline, `9a53881` passed all 23 Python tests and all four Node tests. Compare with these revisions during recovery. Recover the corresponding current files from a healthy source or backup before proceeding with Burito development.

## Toolchain and host checks

| Component | Verified version or result | Role or remaining work |
| --- | --- | --- |
| Git and GitHub CLI | Git 2.56.1, gh 2.103.3, remote HEAD reachable | Source control and repository operations. gh authentication is absent. CLI login is needed for account actions. |
| Python, pip, uv | Python 3.14.9, pip 26.2.2, uv 0.13.7 | Python 3.11 and 3.14 are tested in CI. The isolated environment passes pip and uv dependency checks. |
| Node and npm | Node 26.13.1, npm 12.2.2 | Eve requires Node 24+. CI uses Node 26. npm is the lockfile owner. pnpm and a standalone TypeScript compiler are absent and unneeded for the current eve path. |
| Build tools | GCC 16.2.1, Clang 23.1.4, Make 4.4.1, pkgconf 3.0.10, glibc 2.44, base-devel present | Native builds if required later. pkg-config resolves both SQLite and PipeWire headers. CMake is absent and has no current build target. |
| Rust | rustc 1.99.1 and Cargo 1.99.1 | Available for future native tooling, with rustfmt and Clippy installed. Burito currently has no Cargo build. |
| Docker | 29.9.3 client, daemon socket absent, Compose absent | The checkout has no container or Compose definitions. |
| SQLite | CLI and Python both report 3.54.1 | Local memory database and inspection. |
| CLI utilities | rg 15.2.0, fd 10.5.0, jq 1.8.2, fzf 0.74.5, curl 8.23.0 | Search, JSON, selection, and HTTP. tree and wget are absent. eza and curl cover the current workflow. |
| Tests and debugging | unittest, Node test runner, GDB 18.1 | Unit tests and native debugging. No Ruff, pytest, or ShellCheck configuration or dependency is declared. |
| Media | FFmpeg 9.0.2, PulseAudio, ALSA, and V4L2 support | Synthetic audio processing passed. PipeWire default sink resolves. No default capture source resolved during this audit. |
| Graphics | RTX 5070, 12,227 MiB VRAM, NVIDIA 620.70.06, CUDA UMD 13.5 | Host `nvidia-smi` passed. Ollama detects Blackwell compute capability 12.0 through CUDA. |
| Compositor and app launch | Hyprland 0.57.2, working `hyprctl -j clients`, `gtk-launch`, `xdg-open`, `wl-copy` | Current Burito window integration was written for KWin. A Hyprland provider is later application work. |
| Desktop IPC and services | PipeWire 1.6.11, WirePlumber 0.5.19, D-Bus 1.16.2, systemd 262.2 | Host user bus and audio services respond. Portal 1.22.1 and Hyprland backend 1.5.0 are active. |
| Screen capture and notifications | grim 1.5.0, slurp 1.5.0, notify-send 0.8.9 | Tools present. Use the portal ScreenCast interface for user-authorized streaming, and grim with slurp for still capture. No screen or microphone content was recorded. |
| Remote and mobile | OpenSSH 10.6p1 client, sshd inactive, KVM accessible, WireGuard kernel module available | Flutter, Dart, Android SDK/adb, Java, Tailscale and WireGuard userspace tools are absent. |

Pacman has 824 candidate updates according to the cached sync databases. Project setup used no system package transaction. For future native packages, review a full Arch/CachyOS upgrade through the normal Ryoku update flow and obtain approval before any system transaction. The packaged `ollama-cuda` depends on the full `cuda` toolkit (about 5.36 GiB installed before other dependencies). This setup uses the official Ollama archive with bundled runtime libraries and the working host driver. [Arch system maintenance](https://wiki.archlinux.org/title/System_maintenance#Partial_upgrades_are_unsupported) · [NVIDIA CUDA driver compatibility](https://docs.nvidia.com/cuda/cuda-toolkit-release-notes/)

## Ollama and storage

The only visible physical drive was the 1.8 TiB NVMe. The checkout resolves to Btrfs on `/dev/nvme0n1p8`, with about 82 GiB reported available before setup. The intended 4 TB drive was absent from the host block-device listing. Confirm its identity, mounted filesystem, writable project directory, and free space before placing private data there.

```bash
bash scripts/setup-environment.sh --install-ollama
bash scripts/setup-environment.sh --serve
```

In a second terminal:

```bash
bash scripts/setup-environment.sh --ollama pull qwen3:8b
bash scripts/setup-environment.sh --ollama create burito-local -f config/ollama/Modelfile
bash scripts/setup-environment.sh --ollama show burito-local
python3 scripts/benchmark-ollama.py
```

The installer pins Ollama 0.40.18 and checks the official release asset SHA-256. It reuses an Ollama already on PATH. The x86-64 Linux archive is 1.65 GB compressed and occupies about 2.5 GiB extracted. The server listens at `127.0.0.1:11434`, disables cloud inference, uses one concurrent runner slot, and writes model blobs under the ignored `models/ollama` directory. This endpoint is available to processes on the host. The audit launched it as transient user unit `burito-ollama.service`. Use `systemctl --user stop burito-ollama` to stop that instance.

The existing Modelfile sets an 8,192-token context on Qwen3 8B. Its Q4_K_M weights require a 5.2 GB download, with additional GPU space for inference buffers and the context cache. Keep 8K as the initial setting for the 12 GB card. The model advertises a 40K context. Actual usable context depends on offload, KV cache, desktop VRAM usage, concurrency, and workload. [Ollama Qwen3 tags](https://ollama.com/library/qwen3/tags) · [Official Ollama release](https://github.com/ollama/ollama/releases/tag/v0.40.18)

The benchmark uses a cold load, three warm generation samples, and a synthetic long-prompt recall check at 4K, 8K, and 16K. It prints actual prompt tokens, recall, median generation tokens/sec, sampled system RAM and GPU VRAM, and Ollama's model placement. Host RAM and GPU samples include desktop and background processes. The benchmark unloads the tested model after each context size. Use an idle desktop and avoid concurrent inference for comparable results.

Measured on the RTX 5070 with Ollama 0.40.18 and the Q4_K_M model. Short-prompt generation is the median of three runs. The long prompt tests capacity and instruction following separately.

| Allocated context | Long prompt tokens | Generation tok/s | GPU offload | Peak host RAM MiB | Peak GPU VRAM MiB |
| ---: | ---: | ---: | --- | ---: | ---: |
| 4,096 | 3,623 | 97.9 | Full | 6,538 | 6,207 |
| 8,192 | 7,719 | 97.5 | Full | 6,569 | 6,905 |
| 16,384 | 15,911 | 97.5 | Full | 6,596 | 8,075 |
| 32,768 | 32,295 | 97.3 | Full | 6,723 | 10,854 |
| 40,960 | 40,487 | 50.0 | Partial | 7,535 | 10,656 |

Every reply contained the code word. Only 4K followed the exact one-word format. The larger windows returned extra prose or reasoning text, so the results support retaining 8K for capacity and GPU headroom while checking structured output separately. The first model load took 20.85 seconds. Subsequent loads after unloading the runner took 2.17–2.46 seconds in the sweep. The raw sweep is in the local ignored `reports/ollama-context-sweep.jsonl` file. Reproduce it with `python3 scripts/benchmark-ollama.py --contexts 4096 8192 16384 32768 40960`.

Once the runtime is recovered, set `BURITO_LOCAL_MODEL=burito-local` and `BURITO_LOCAL_URL=http://127.0.0.1:11434/v1`. The Burito runtime should continue to use the loopback endpoint.

## Later feature dependencies

| Feature | Local approach and verification |
| --- | --- |
| Embeddings | Start with Ollama `/api/embed` and a dedicated embedding model when search needs it. Keep vectors and source IDs in SQLite initially. Record the model digest and vector dimension and reindex when either changes. |
| Speech recognition | Evaluate whisper.cpp or faster-whisper using a short, consented audio fixture. Compile whisper.cpp only when needed, or pin faster-whisper in a separate uv environment with wheel support verified for its Python version and CTranslate2 backend. |
| Speech synthesis | Evaluate Piper with a locally stored voice and its license. Verify real-time factor on CPU and play a synthetic fixture through the existing PipeWire stack. |
| Vision | Evaluate a small quantized multimodal Ollama model separately. Use user-authorized portal capture and keep model concurrency low to stay within the shared VRAM budget. |
| Android | When a Flutter client exists, use the official Flutter SDK with its bundled Dart, the Android SDK and JDK required by that project's Gradle tooling. Check `flutter doctor -v` and `adb devices`. Host KVM is accessible for eventual emulator use. iOS building and signing belongs on the Apple Silicon MacBook with Xcode. [Flutter Android setup](https://docs.flutter.dev/platform-integration/android/setup) |
| REST and WebSocket | The installed Node runtime and curl are enough for local REST and WebSocket development. Node has a WebSocket client. Review the recovered runtime before selecting a server dependency. |
| Private remote access | A future device can use an authenticated application API over Tailscale or WireGuard, or an SSH local port forward. Keep direct Ollama access bound to loopback. Approve any host service, VPN enrollment, or remote access change separately. |


## Phase 1 web console

From the Phase 1 worktree with Ollama already running, install the locked
runtime, then start an isolated web session.

```bash
bash scripts/setup-environment.sh --runtime
python3 -m burito web --temporary-data --model burito-local --context-tokens 8192
```

Open `http://127.0.0.1:8765/` directly. The console checks Eve, its chat bridge
and the selected model before enabling the composer. Add `--notify` to request
a generic desktop notification on completed replies. Each temporary run creates
its own lesson database. Normal startup expects the mounted brain drive and
does not fall back to an internal database. For the desktop launcher, set
`BURITO_WEB_MODEL=burito-local` if that is the installed alias.

CLI sessions with `--enable-desktop-control` can list Hyprland 0.57+ windows and
request approval to focus a stable window ID. KWin keeps its existing listing
and focus implementation. OCR and native-field insertion retain their existing
KDE-specific requirements. Window captions are transient and excluded from
host access audit records.
