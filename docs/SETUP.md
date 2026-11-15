# First step: machine readiness

Run from the checkout:

```bash
python3 -m burito doctor
python3 -m unittest discover -s tests -v
python3 -m burito init
```

The doctor is read-only and makes no network requests. It reports selected
hardware/runtime information, not environment secrets. Review any output before
sharing it. An NVIDIA failure is a readiness finding, not proof the card is absent.

## Findings from the development session

- Ubuntu 26.04.1, x86_64; owner reports Kubuntu desktop.
- Intel i9-14900K, approximately 32 GB RAM; Wayland session.
- Owner reports RTX 5070; NVIDIA CLI currently fails to contact its driver.
- Linux partition exposes approximately 76 GB free; intended 4 TB storage is
  not visible in this session. Do not partition, format, or download models
  until the correct physical volume and mount are confirmed.
- Python 3.14 available; Node/npm not found on PATH.
- Shell cannot resolve github.com; connected GitHub tools can access repository.

These observations describe the exposed development environment; it may not
expose every host device or installed program.

## GPU and storage gate

Collect read-only output from `nvidia-smi`, `lspci -nnk`, `lsblk -f`, and
`df -h` on the actual desktop. Confirm driver compatibility using the current
Ubuntu/Kubuntu documentation before making changes. Do not reinstall drivers,
disable Secure Boot, modify partitions, or mount unknown volumes automatically.
Confirm the 4 TB volume, filesystem, ownership, and mount persistence. Keep
models, memory, indexes, and backups in distinct directories; a second folder
on the same disk is not an independent backup.

## Runtime gate

The intended agent runtime is eve. Follow its current
[setup guide](https://eve.dev/docs/getting-started) and read the installed
`node_modules/eve/docs/README.md` before implementing runtime APIs. Node 24+
is documented as a prerequisite. Install a supported Node runtime, initialize
eve in a temporary sibling directory, inspect the generated files, then merge
the scaffold into this repository without overwriting existing work. Commit
the actual dependency lockfile. Do not invent package versions or claim the
agent is runnable before installation and a smoke test.

## Storage override

Before initializing memory, optionally set an absolute destination on the
confirmed storage volume:

```bash
export BURITO_DATA_DIR=/your/confirmed/mount/burito/private
python3 -m burito init
```

No storage migration or backup scheduler is implemented yet. Existing data
does not move when changing this setting. Keep the location stable and back
up the database while Burito is stopped until a consistent backup command is
implemented. Use synthetic text when demonstrating memory commands publicly.
