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

## Latest host findings — 2026-11-26

- Ryoku CachyOS/Arch, Hyprland, x86_64; i9-14900K and 32 GB RAM.
- RTX 5070, driver 620.70.06. Host `nvidia-smi` passed. A local response from
  `burito-local:latest` ran with 100% GPU allocation, 8,192 context and 6.3 GB
  Ollama-reported model memory. Do not reinstall the working driver or model.
- Transcend StoreJet 25H3 with WDC WD40NPJZ-00CCDT0, ext4 UUID
  `9428a980-24a6-45b2-a0a6-5e057c819406`, mounted read/write at
  `/mnt/burito-brain`. `findmnt --verify` passed; root is mode 700 and about
  3.6 TiB is free. SMART remains owner-reported because this session lacks the
  sudo password needed to query it.
- A synthetic write/read/fsync/checksum passed. A v1 brain manifest and empty
  v1 SQLite memory database passed synthetic persistence, correction, deletion,
  integrity and temporary backup/restore checks.
- The Codex sandbox sees the mount read-only and cannot access GPU devices or
  host loopback. Host checks were run in the normal execution context; these
  sandbox restrictions are not host failures.

Do not modify the Windows partitions, Ryoku Btrfs layout or the existing fstab
entry. Physical reboot persistence and a durable independent backup remain
unverified.

## GPU and storage gate

For future changes, use read-only `nvidia-smi`, `lsblk -f`, `findmnt`, and `df`
checks first. The current driver and brain mount are verified; do not reinstall
them or duplicate the existing fstab entry. Keep backups on a different physical
device; another folder on the brain disk is not an independent backup.

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

Installation completed successfully from the normal desktop terminal. This
restricted shell still cannot resolve download hosts or access GPU devices;
those are session limitations, not diagnoses of the desktop connection or driver.
The installed eve APIs and agent discovery were checked locally. Discovery
reports zero errors and only the explicitly authored PC tools. The owner completed a first local
model exchange; answer quality, GPU placement, and offline behavior need further
verification.

For a fresh runtime check after installation, run `npm run check:discovery`,
then `npm test` inside `runtime/` with the selected Node version on PATH.
Discovery uses the public eve CLI, and the tests inspect its fresh output.

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
