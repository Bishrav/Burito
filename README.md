# Burito

A personal hybrid assistant for Kubuntu: local memory, offline reasoning,
online research, useful suggestions, and progressively verified automation.

**Status: first local text conversation completed; quality checks in progress.**
Screen observation is not implemented. The optional PC inventory timer
collects local metadata when enabled; it does not capture screens or file contents.
The separate runtime installer downloads packages only when explicitly run.

## Start here

Python 3.11+ is sufficient; the foundation uses only the standard library.

```bash
python3 -m burito doctor
python3 -m burito init
python3 -m burito teach
python3 -m burito remember "I prefer short explanations" --source owner
python3 -m burito memories
python3 -m burito correct MEMORY_ID "I prefer detailed explanations"
python3 -m burito forget MEMORY_ID
python3 -m burito feedback add correction "Prefer suggestions grounded in a named project task."
python3 -m burito feedback list
python3 -m burito backup /absolute/path/to/an/existing/folder/burito-backup.sqlite3
python3 -m unittest discover -s tests -v
```

Commands run from this repository. Memory is stored outside the repository,
under `$XDG_DATA_HOME/burito` or `~/.local/share/burito`. Set
`BURITO_DATA_DIR` to an absolute path on your intended storage volume to
use a different location. The directory must be owned by your account.
The current database is local and unencrypted; use OS disk encryption for
at-rest protection. Never commit personal data, hardware reports, or secrets.

`forget` removes an entry from the live database; it does not erase external
backups or guarantee forensic erasure from the storage medium.

Feedback is separate from confirmed personal facts. Add it only after reviewing
a suggestion yourself. A future ordinary chat can use it with
`--include-feedback`; activity-only chats always exclude it. This records owner
guidance locally and does not train model weights.

## Plan

- [Complete roadmap](docs/ROADMAP.md)
- [Architecture and trust boundaries](docs/ARCHITECTURE.md)
- [First milestone and machine setup](docs/SETUP.md)
- [Progress and next work](docs/STATUS.md)
- [Teaching Burito together](docs/LEARNING.md)
- [Local PC inventory and change detection](docs/PC_AWARENESS.md)
- [Using files and applications from chat](docs/PC_ACCESS.md)

To establish a computer inventory and enable periodic metadata checks after login:

```bash
python3 -m burito pc scan
python3 -m burito pc enable
python3 -m burito pc monitor-status
```

These commands collect local inventory and file metadata, not screenshots or
file contents. Run `python3 -m burito pc pause` to stop collection. See the scope
and limits in the PC-awareness guide before treating the inventory as complete.

Start its general education separately from your personal preferences:

```bash
python3 -m burito school install
python3 -m burito school list
python3 -m burito school lesson home.honesty
```

This installs three home-foundation lessons locally. Eleven introductory lessons
are available in total, including IT and health literacy. Sources and review
prompts accompany each lesson. Stored references are not model training or
demonstrated understanding.
The owner completed a first exchange through the chat launcher. The lesson and
personal-memory bridge still need behavioral checks. See [first local conversation](docs/FIRST_CHAT.md) for setup
gates and limitations. Preview the selected lesson with:

```bash
python3 -m burito context --lesson home.honesty
```

The agent runtime preparation uses eve (TypeScript), with a local desktop companion.
This Python foundation checks the machine and stores explicitly supplied
memories while GPU, storage, and model setup are resolved. In a normal Kubuntu
terminal with internet access, install runtime packages with:

```bash
cd ~/Burito
bash scripts/setup-runtime.sh
```

This downloads Node 26.13.1 from nodejs.org if Node 24+ and npm are unavailable,
checks the archive against its HTTPS-served SHA-256 manifest, and installs it
inside `.tools/`. It then installs eve, ai, zod, and the OpenAI-compatible adapter
in `runtime/`, saving exact
versions and a lockfile. This can take several minutes. It does not use sudo,
change drivers, download AI models, start a chat, or enable observation.
The runtime is installed and its generated lockfile is committed. Subsequent
runs use `npm ci` against that lockfile. Installed-version discovery and tests
pass; a first local model exchange completed, with answer-quality issues being retested.

See the [eve setup documentation](https://eve.dev/docs/getting-started).

Learning initially means retrieving knowledge, remembering approved facts,
and testing procedures. Model fine-tuning is a separate later experiment.
Installing this repository does not make a system that can do everything or
improve itself without supervision.
