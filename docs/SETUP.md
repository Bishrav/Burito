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
- RTX 5070 is detected through PCI and NVIDIA driver information. The NVIDIA
  kernel module is loaded, but `/dev/nvidia*` is absent in the restricted session.
  `nvidia-smi` here therefore does not establish a broken host driver. Verify it
  in the normal desktop terminal before changing drivers.
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
is documented as a prerequisite. Run the prepared user-local installer from
the normal desktop terminal:

```bash
cd ~/Burito
nvidia-smi
bash scripts/setup-runtime.sh
```

The script uses an existing Node 24+ and npm when available, otherwise installs
official Node 26.13.1 under `.tools/` after verifying its archive checksum against
the official HTTPS-served manifest. This is transport plus checksum verification,
not separate signature verification. No system packages or shell profiles change.
It uses eve's documented manual-install path in `runtime/`, preserving Python
source and memory. The committed instructions are stable identity only.

First installation resolves current eve/ai/zod versions with `--save-exact`;
later installations use the generated lockfile with `npm ci`. Commit the actual
package changes and lockfile after review and a smoke test. No dependency
versions are invented. Read the installed `runtime/node_modules/eve/docs/README.md`
before adding runtime APIs, tools, or model configuration. Do not start the
runtime with its implicit default model: choose and configure the intended
local/cloud model first. Instructions alone are not a permission boundary;
the executor remains a later implementation task.

The installer cannot be completed in this restricted development shell because
nodejs.org cannot be resolved. This is a session limitation, not a diagnosis of
the desktop internet connection. The script's syntax and local failure path
are testable here; package installation and AI conversation are not yet verified.

## Storage override

Before initializing memory, optionally set an absolute destination on the
confirmed storage volume:

```bash
export BURITO_DATA_DIR=/your/confirmed/mount/burito/private
python3 -m burito init
```

No storage migration or backup scheduler is implemented yet. Existing data
does not move when changing this setting. Keep the location stable and back
up the database with the consistent snapshot command:

```bash
python3 -m burito backup /your/existing/backup/folder/burito-snapshot.sqlite3
```

The destination must be a new file in an existing folder. This command never
overwrites a backup. Snapshots are private but unencrypted. A folder on the
same disk is not protection against that disk failing. Deleted or corrected
facts can remain in older backups until you remove those backups.

Use `python3 -m burito teach` for the first local home-education session, then
`memories`, `correct ID "replacement"`, and `forget ID` to manage facts. These
facts are not injected into AI chat yet. Use synthetic examples publicly.
