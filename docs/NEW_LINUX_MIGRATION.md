# Move Burito to another Linux machine

This guide moves the local Burito checkout and its private data to another
Linux computer. The code and the memory database are separate: the code is in
`~/Burito`; personal memory, glossary entries, and knowledge records live in
`/mnt/burito-brain/data` on the external `BURITO_BRAIN` drive.

**Never format or repartition the existing brain drive during migration.** It is
already ext4 and contains the Burito data directory. The existing drive UUID is
`ce024ab9-6884-4482-afdd-edbe189ebcf2`; confirm it with `blkid` on the target
machine before using it.

## 1. Prepare the old machine

Stop Burito with `Ctrl+C`. Confirm the source tree is clean and that the brain
drive is mounted:

```bash
cd ~/Burito
git status --short
findmnt -T /mnt/burito-brain -o TARGET,SOURCE,FSTYPE,OPTIONS
```

The current development code is on GitHub, so a bundle is not needed for this
migration. If you later have local commits that are not pushed, a Git bundle
preserves them and the full Git history on the external drive:

```bash
git bundle create /mnt/burito-brain/Burito.bundle --all
ls -lh /mnt/burito-brain/Burito.bundle
```

If `git status --short` lists source changes, review and commit them before
creating a bundle. The bundle contains source history, not model weights,
runtime `node_modules`, Eve's temporary session state, browser profiles, or
private Burito data. The private data already resides at
`/mnt/burito-brain/data` on the same drive.

Keep an independent backup of `/mnt/burito-brain/data` on a different physical
device. Moving a single drive is not a backup.

## 2. Attach and mount the existing drive

On the new Linux computer, inspect devices first:

```bash
lsblk -f
sudo blkid
```

Find the partition labelled `BURITO_BRAIN` and verify that its UUID is the
expected one above and filesystem is ext4. If the desktop has already mounted
it, inspect the actual mount:

```bash
findmnt -T /mnt/burito-brain -o TARGET,SOURCE,FSTYPE,OPTIONS
```

If the partition is not mounted, create the mount point and mount the verified
UUID (do not substitute another disk):

```bash
sudo mkdir -p /mnt/burito-brain
sudo mount UUID=ce024ab9-6884-4482-afdd-edbe189ebcf2 /mnt/burito-brain
```

Verify it is the expected external ext4 disk, mounted read/write, and contains
the existing `data` directory:

```bash
findmnt -T /mnt/burito-brain -o TARGET,SOURCE,FSTYPE,OPTIONS
ls -ld /mnt/burito-brain/data
```

If the drive does not appear at `/mnt/burito-brain` automatically, add the UUID
to `/etc/fstab` only after checking that no entry for it already exists. The
recommended entry is:

```text
UUID=ce024ab9-6884-4482-afdd-edbe189ebcf2 /mnt/burito-brain ext4 defaults,nofail,x-systemd.device-timeout=10s 0 2
```

Then run `sudo mount -a` and check `findmnt` again. Do not run filesystem repair
or formatting commands as part of routine setup.

The data directory is private (mode `700`). If the account UID differs between
machines, inspect ownership with `id -u` and `stat -c '%u %a %n'` before
changing anything. Only correct ownership after confirming the mounted device
is the expected `BURITO_BRAIN` disk; never recursively change permissions on
an unverified mount.

## 3. Restore the project source

Clone the current code from GitHub:

```bash
git clone https://github.com/Bishrav/Burito.git ~/Burito
cd ~/Burito
git log -1 --oneline
```

If future local commits have not been pushed and a bundle was created on the old
machine, clone that bundle instead:

```bash
git clone /mnt/burito-brain/Burito.bundle ~/Burito
```

Choose one method; do not clone over an existing `~/Burito` directory. Compare
the latest commit with the old machine before relying on the GitHub clone.

## 4. Install runtime and local model

The project setup script installs the locked Eve/AI runtime dependencies and
downloads a verified checkout-local Node version if system Node 24+ is absent.
Run it from the cloned repository:

```bash
cd ~/Burito
bash scripts/setup-runtime.sh
```

Install Ollama using its current official Linux instructions if it is absent.
Then check the new machine's GPU/VRAM and install the local model. The checked-in
Modelfile uses `qwen3:8b` and an 8192-token context:

```bash
ollama pull qwen3:8b
ollama create burito-local:8b -f config/ollama/Modelfile
ollama list
```

Model weights are not included in the Git bundle or brain data directory. The
download needs internet and several gigabytes of free storage. The model and
context must fit the new machine; if they do not, select a compatible local
model and update the launch configuration deliberately. Burito's regular
launcher makes no automatic cloud fallback.

Check or install the education lessons in the migrated data directory:

```bash
BURITO_DATA_DIR=/mnt/burito-brain/data python3 -m burito school list
```

If `home.honesty` is missing, install lessons:

```bash
BURITO_DATA_DIR=/mnt/burito-brain/data python3 -m burito school install
```

## 5. Set up Brave and desktop tools

Brave browser permissions and extension installation are local to each machine.
Use [PC access setup](PC_ACCESS.md):

1. In Brave, open `brave://extensions`, turn on Developer mode, and choose
   **Load unpacked** for `~/Burito/runtime/browser-extension`.
2. Copy the extension ID displayed by Brave.
3. Install the native messaging host for this machine:

   ```bash
   bash ~/Burito/scripts/install-brave-tab-host.sh YOUR_EXTENSION_ID
   ```

4. Restart Brave Origin. From the Burito extension popup, grant tab-label and
   page access as needed. “Enable all websites” covers regular HTTP/HTTPS sites;
   the browser's permission prompt still applies. Burito separately asks before
   each page read and browser action.
5. KWin window listing/focus requires KDE Plasma Wayland. Screen OCR is separate
   and still asks approval for each capture. Other desktop environments may not
   support KWin tools.

## 6. Start and verify

The all-tools launcher selects `/mnt/burito-brain/data`, the local model, and an
8192-token context. It refuses to start if the expected brain drive is absent:

```bash
cd ~/Burito
./scripts/start-chat.sh
```

Start with simple checks: ask for the installed lesson, read a harmless public
webpage after granting that site access, and test window listing if this is KDE
Wayland. Approve only the operation you requested. Add `--include-personal`
explicitly if you want personal facts included for a chat. Stop with `Ctrl+C`.

## Ready-to-paste prompt for Codex on the new Linux machine

```text
Set up my existing Burito project on this Linux machine using the repository in
~/Burito and the external BURITO_BRAIN drive. Work in small steps and verify
each result. Begin with read-only checks: inspect the OS, Python, Node, GPU,
storage devices, filesystem UUIDs, mounts, and ~/Burito Git status. The existing
brain drive is ext4 with UUID ce024ab9-6884-4482-afdd-edbe189ebcf2, label
BURITO_BRAIN. Its private Burito data is /mnt/burito-brain/data. Never format,
repartition, erase, or run filesystem repair on any drive. Verify the UUID and
label before mounting; stop if they do not match. If a required privileged change
or ownership repair is needed, explain the exact change and why before doing it.

If ~/Burito is absent, clone the current project from
https://github.com/Bishrav/Burito.git. If GitHub is unavailable and
/mnt/burito-brain/Burito.bundle exists, clone that bundle instead to preserve
any unpushed work. Do not overwrite an existing checkout or discard local
changes. Keep personal data, browser
profiles, credentials, and the SQLite database out of Git.

Once the disk is correctly mounted at /mnt/burito-brain and the checkout is
verified, install the pinned runtime using bash scripts/setup-runtime.sh. Check
GPU/VRAM before downloading model weights. The repository Modelfile uses
qwen3:8b with an 8192-token context; install/create burito-local:8b only if it
fits this machine. Do not configure cloud fallback. Verify the existing
/mnt/burito-brain/data remains in use and is writable by my account without
changing unrelated permissions. Check whether home.honesty is installed and
install lessons only if it is missing.

Set up the Brave extension and native messaging host following docs/PC_ACCESS.md.
Use the extension ID shown on this machine. Do not read passwords or expose
private browser content. Grant all-website permission only if I choose it; keep
per-action approvals enabled. KWin window controls require KDE Plasma Wayland.

Finish by running the Burito diagnostics and confirming the model is available.
Start ./scripts/start-chat.sh only after the storage, model, and extension setup
is ready. Do not push to GitHub, change system drivers, remove data, or weaken
approval gates unless I explicitly ask. Report what you verified and anything
that needs my decision. Never claim live desktop/browser behavior was tested
unless you actually observed that result.
```

## Troubleshooting pointers

- **Brain drive missing/read-only:** stop Burito; verify the UUID, mount source,
  filesystem, mount options, and ownership before changing permissions.
- **Eve runtime missing:** rerun `bash scripts/setup-runtime.sh` from `~/Burito`.
- **Local model unavailable:** check `ollama list`, the Ollama service, and
  `config/ollama/Modelfile`.
- **Brave tools unavailable:** check the extension is loaded, the native host
  was installed with the correct ID, Brave was restarted, and site permissions
  were granted.
- **Window list/focus unavailable:** confirm KDE Plasma Wayland and KWin
  scripting. Screen OCR is a separate tool and does not replace window listing.
