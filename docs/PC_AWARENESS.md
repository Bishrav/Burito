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
`pc monitor-status` reports both unit load/active states and the service's last
result/exit status, so an enabled timer is not mistaken for a running timer.
The generated `WorkingDirectory` uses a raw absolute path; it must not reuse
the command-argument quoting used by `ExecStart`. Older generated units with
literal path quotes were rejected by systemd. Run `pc enable` after updating
to regenerate them and reload the user manager.
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

The separate tools in PC_ACCESS.md now support bounded text-file reads, filename
search, and approved application-launch requests. This inventory alone does not
perform those operations. Document-content search and general desktop actions
remain future integrations.

## Optional foreground-app activity

Burito includes an opt-in KWin script for Plasma on Wayland. It records only the
active window's desktop application ID and `idle` transitions in Burito's private
SQLite database. It never reads window titles, document names, screen contents,
keystrokes, or process command lines. Local KWin debug logging must be enabled
for the script-to-collector bridge; the collector ignores all journal lines
except its own `BURITO_ACTIVITY:` records. No activity data is sent to chat,
cloud services, or GitHub. KWin's local journal also contains these app IDs;
its retention is controlled by systemd-journald, so `activity clear` deletes
Burito's SQLite records but does not erase journal history.

Enable, inspect, pause, review, and delete activity records with:

```bash
python3 -m burito activity enable
python3 -m burito activity status
python3 -m burito activity report --days 7
python3 -m burito activity label org.kde.konsole "Owner-provided description"
python3 -m burito activity labels
python3 -m burito activity unlabel org.kde.konsole
python3 -m burito activity pause
python3 -m burito activity clear
```

Enable starts a user-level journal collector and installs/enables the KWin
script. Pause disables the script and collector but preserves records. Clear
removes the recorded events. Burito retains at most 30 days and 20,000 events.
App labels are context you provide explicitly; Burito does not infer interests
from app IDs or durations. `activity clear` also removes these local labels.
Reports estimate elapsed foreground time between app switches; they do not
prove keyboard use or personal interest. Long gaps are capped at four hours,
and inactivity away from the computer can still be counted as foreground time.
This observer is not enabled by `pc enable` and does not capture screenshots.
To remove old journal entries, use Kubuntu's journal retention controls; do not
vacuum the journal unless you intend to remove unrelated system logs as well.
