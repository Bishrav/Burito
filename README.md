# Burito

A personal hybrid assistant for Kubuntu: local memory, offline reasoning,
online research, useful suggestions, and progressively verified automation.

**Status: milestone 0 foundation.** This is not yet a talking AI or a desktop
observer. No background monitoring, network requests, or automatic actions
are enabled by this code.

## Start here

Python 3.11+ is sufficient; the foundation uses only the standard library.

```bash
python3 -m burito doctor
python3 -m burito init
python3 -m burito remember "I prefer short explanations" --source owner
python3 -m burito memories
python3 -m burito forget MEMORY_ID
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

## Plan

- [Complete roadmap](docs/ROADMAP.md)
- [Architecture and trust boundaries](docs/ARCHITECTURE.md)
- [First milestone and machine setup](docs/SETUP.md)
- [Progress and next work](docs/STATUS.md)

The planned agent runtime is eve (TypeScript), with a local desktop companion.
This Python foundation checks the machine and stores explicitly supplied
memories while Node, GPU, storage, and model setup are resolved.
See the [eve setup documentation](https://eve.dev/docs/getting-started).

Learning initially means retrieving knowledge, remembering approved facts,
and testing procedures. Model fine-tuning is a separate later experiment.
Installing this repository does not make a system that can do everything or
improve itself without supervision.
