# Burito
See the [digital human vision](docs/DIGITAL_HUMAN_VISION.md), [roadmap](docs/ROADMAP.md), and [current status](docs/STATUS.md).

Start with the [Ryoku setup](docs/RYOKU_SETUP.md), [status](docs/STATUS.md),
and [security boundaries](docs/SECURITY.md). See the [recovery report](docs/RECOVERY_REPORT.md)
for the integrity gate and current verification. The migration guide describes
the separate external brain drive and KDE-era desktop setup.
Burito is a local-first personal assistant built around a local language model,
explicit local memory, and owner-approved tools. It can answer from saved
knowledge, remember approved facts and definitions, inspect selected desktop
windows, and work with Brave pages when the required permissions are enabled.

Burito is an evolving project, not a promise of unrestricted or fully reliable
computer control. Every screen/page read and browser or desktop action remains
bounded by the tool and its approval prompt. It does not run arbitrary shell
commands, read the clipboard, or observe the desktop continuously.

## Quick start

The standard local desktop launcher assumes the local model `burito-local:8b`
is already available and the external brain drive is mounted at
`/mnt/burito-brain`:

```bash
cd ~/Burito
./scripts/start-chat.sh
```

Press `Ctrl+C` to leave the chat. The launcher enables the implemented local
desktop and Brave tools. Each sensitive read or action still requires its own
approval. Personal facts are excluded by default; add `--include-personal` to
the launcher command only when you want them included in that chat.

## First-time Linux setup

Read the [first local conversation guide](docs/FIRST_CHAT.md) for runtime,
Ollama, model, and first-chat setup. In short, install the pinned Eve runtime
dependencies in this checkout, install Ollama, obtain a compatible local model,
and create Burito's local Ollama model configuration:

```bash
cd ~/Burito
bash scripts/setup-runtime.sh
ollama pull qwen3:8b
ollama create burito-local:8b -f config/ollama/Modelfile
```

The Ollama model is local to the machine and is not part of the Git repository.
Check GPU memory and the new machine's capabilities before choosing a model.

## Moving Burito to another Linux machine

The brain drive contains persistent local data; the repository contains the
program. The current code is on GitHub. If you later have unpushed local
commits, create a Git bundle on the brain drive to transfer them and their
history:

```bash
cd ~/Burito
git status --short
git bundle create /mnt/burito-brain/Burito.bundle --all
```

On the new machine, mount the existing brain drive without formatting it. For
the current pushed code, clone GitHub; use the bundle only to include future
unpushed commits:

```bash
git clone https://github.com/Bishrav/Burito.git ~/Burito
# To include unpushed commits instead, use:
# git clone /mnt/burito-brain/Burito.bundle ~/Burito
cd ~/Burito
bash scripts/setup-runtime.sh
```

See the complete [new Linux migration guide](docs/NEW_LINUX_MIGRATION.md) for
mounting the disk, setting up the model and Brave extension, and a ready-to-paste
Codex prompt.

## Local memory and storage

Burito stores memories, glossary entries, lessons, and imported knowledge in
its local data directory. The default follows the XDG data location; set
`BURITO_DATA_DIR` to select another absolute path. The desktop launcher uses
`/mnt/burito-brain/data` and refuses to start if the expected drive is not
mounted. Keep this data out of GitHub. Back it up to a separate destination.

The SQLite data is local and unencrypted. Use operating-system disk encryption
to protect it at rest. Deleting a database record does not erase copies in
external backups or guarantee forensic erasure from storage media.

## Brave and desktop access

The optional Brave extension and native messaging host are installed from this
repository. Follow [PC access setup](docs/PC_ACCESS.md) to load the unpacked
extension, install the host for the displayed extension ID, and grant site
permissions. You can grant access to one site or all regular HTTP/HTTPS sites;
the browser still asks separately before page reads and actions. The extension
does not send page contents until an approved read is requested.

KWin window listing and focus require KDE Plasma with Wayland. Screen OCR is a
separate one-shot approved read. OCR may misread text and does not identify
visual objects. A window title identifies metadata, not the page contents.

## Learn more

- [Roadmap](docs/ROADMAP.md)
- [Current status](docs/STATUS.md)
- [Architecture and trust boundaries](docs/ARCHITECTURE.md)
- [First local conversation and model setup](docs/FIRST_CHAT.md)
- [New Linux migration and Codex prompt](docs/NEW_LINUX_MIGRATION.md)
- [PC and Brave tools](docs/PC_ACCESS.md)
- [Local PC inventory](docs/PC_AWARENESS.md)
- [Knowledge library](docs/KNOWLEDGE.md)
- [Glossary](docs/GLOSSARY.md)
- [Owner guidance and feedback](docs/LEARNING.md)
- [Optional online research](docs/ONLINE_RESEARCH.md)
- [Automatic GitHub checkout updates](docs/AUTO_UPDATE.md)

Burito is local-first, but browser search uses the internet when explicitly
requested and approved. Online page content is treated as untrusted reference
data. Cloud model fallback is not enabled by the standard launcher.