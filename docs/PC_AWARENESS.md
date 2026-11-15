# Local PC awareness

Burito can inventory the computer and compare later snapshots. This is distinct
from permission to execute commands, administer the OS, or watch the screen.
No root permissions, password access, keylogging, screen capture, or file-content
indexing are added by this milestone.

## Collect and inspect

```bash
cd ~/Burito
python3 -m burito pc scan
python3 -m burito pc status
python3 -m burito pc changes
```

The first scan establishes a baseline. Subsequent scans record added, modified,
and removed items. Moving a file can appear as removal plus addition. Changes
that appear and disappear entirely between scans can be missed.

## Current scope

- OS, kernel, CPU, RAM, and display devices exposed to the running process.
- Block devices, filesystems, and mount points exposed by `lsblk`.
- Installed Debian packages and versions, visible snap package files, Flatpak
  applications when its CLI is installed, desktop launchers, and local binaries.
- USB product names exposed through sysfs, without collecting device serials.
- Non-hidden home-folder file paths, sizes, and modification times. File
  contents are never opened by this collector. Directory symlinks and separate
  mounted filesystems are not traversed. Hidden paths and dependency folders
  such as `node_modules` are excluded.

The home scan is capped at 20,000 entries and 40 directory levels. Permission
errors and caps are reported as partial coverage. Missing items in an incomplete
scan are not declared deleted. If a category cannot be read, its previous
snapshot remains with its previous timestamp. Counts may therefore include
last-known entries. This does not detect every possible system modification,
portable application, network device, or software installed by every manager.

The inventory describes what the collecting process can see. Run a scan in
Konsole to establish a desktop-session baseline; the development sandbox can
have a restricted device, filesystem, and socket view. A user timer runs with
the normal user service manager's permissions, not the assistant's sandbox.

## Monitor after login

```bash
python3 -m burito pc enable
python3 -m burito pc monitor-status
```

This writes `burito-awareness.service` and `burito-awareness.timer` under
`$XDG_CONFIG_HOME/systemd/user` or `~/.config/systemd/user`, reloads the user
manager, and enables its timer. No sudo is required. Scans begin about 30 seconds
after user-manager startup and repeat about 60 seconds after each scan finishes.
The service has a 90-second timeout. It runs independently of AI chat.

The user manager normally starts at login; if lingering is already enabled it
may also run without a logged-in desktop. This command does not enable lingering.
Service activation cannot be completed from the restricted development session;
run the command in Konsole. An error means activation was not verified even if
unit files were successfully prepared.

Pause both future scans and any current scan:

```bash
python3 -m burito pc pause
```

Inspect failures with `journalctl --user -u burito-awareness.service -n 30`.
Changing the code directory, Python location, or memory location requires running
`pc enable` again to update the unit. Turning monitoring off keeps existing data.

## Local chat integration

Local chat receives a bounded inventory summary with collection timestamps,
coverage problems, counts, and at most five recent changes. It does not receive
the full file or package list. The initial baseline is not converted into
personal facts. The agent must not claim the snapshot is a live view.

Use `--no-system` with `chat` or `context` to exclude the inventory from that
request. This does not pause the collector or erase previous session messages.
Personal facts continue to require the separate `--include-personal` option.
Cloud model routing remains disabled. Future cloud support must explicitly
decide what PC information can leave the machine.

Snapshots and the newest 2,000 change events live in the private local SQLite
database outside the repository. The newest 30 scan results are retained.
Existing database backups include this inventory. It is not encrypted by Burito,
and filenames can themselves be private. No inventory, change log, or collected
hardware report is committed to GitHub; only source and synthetic tests belong there.

## Next layers

Selected document-content search, active-window observation, and scoped computer
actions are separate future integrations. This inventory alone cannot answer
questions about a file's contents or perform arbitrary tasks on the PC.
