# File and application access

Burito now has explicit host tools, in addition to the inventory summary:

| Tool | Capability | Approval |
| --- | --- | --- |
| `files` | Browse folders, read bounded UTF-8 text, search filenames | No extra prompt |
| `applications` | Find registered desktop launchers and their exact IDs/hashes | No extra prompt |
| `open_application` | Submit a launch request for a selected, unchanged launcher | Every launch |
| `desktop_windows` | On-demand snapshot of KWin internal IDs, resource classes, captions, desktop/minimized/active state | No extra prompt; only exposed by `--enable-desktop-control` |
| `focus_window` | Unminimize and focus one exact window by internal ID | Every focus |
| `inspect_window` | After approval, focus one exact window and immediately OCR its active window | One approval covers focus and capture |

These run through a local Python bridge using the normal account's permissions.
They are not eve's built-in sandbox file tools. Default shell, file-write, web,
generic agent, and self-modification tools remain disabled.

## Start and test

Exit the current chat with Ctrl+C, then restart from the project directory:

```bash
cd ~/Burito
python3 -m burito chat --model burito-local:8b --context-tokens 8192
```

Start a new conversation. Ask:

> Use the files tool to list ~/Documents. Report exact names, not guesses.

Then test a known public source file:

> Use the files tool to read the first five lines of ~/Burito/README.md. State the path you read.

For application discovery:

> Use applications to find Dolphin. Do not launch it yet.

Only after these work, ask Burito to open Dolphin. The launch tool requires an
owner approval in the chat UI. Approve the specific application you requested.
The tool checks the launcher hash and launches a private snapshot of the approved
bytes. A successful request does not verify a visible or usable window.

## What access means

Ordinary directories across `/` can be browsed subject to Linux permissions,
including accessible mounted storage. Symlink targets are checked against the
same policy, and actual path opens reject replaced symlink components.
This does not grant administrator privileges or bypass permission errors.

Common credential stores, key/database files, private Burito storage, browser
profiles, `/proc`, `/sys`, `/dev`, `/run`, and selected system credential folders
are excluded. Directory listings may show a protected entry's name without
granting permission to open it. These exclusions cannot detect every secret in
an arbitrary document; use `--no-files` to disable all file/application tools.

Text reads support regular UTF-8 files up to 256 KiB. Each response returns a
bounded line range and at most 8,000 characters, with the exact path, timestamp,
and content hash. Binary files, images, PDFs, archives, media, and large files
need dedicated readers that are not implemented here. A filename search looks
at names, not contents, skips heavy dependency/cache trees, returns at most
30 matches, and examines at most 20,000 entries. Direct browsing supports paging.

Application discovery covers ordinary `.desktop` files in system, user, Snap,
and Flatpak launcher directories. Symlink launchers and nonregular launchers
are skipped, so this is not a list of every executable or installed package.
Some desktop-launcher behaviors may not work from the private snapshot location.
No executable command line or URL is accepted from the model for launching.

## Boundaries

There is no arbitrary shell execution, file editing/deletion, account access,
or outbound messaging in these tools. Application-window control is a separate
opt-in KWin integration described below.
An optional one-shot screen OCR tool is available only when a chat is started
with `--enable-screen-read` (and without `--no-files`). Each capture requires
approval. KDE Spectacle captures the full screen or active app window to a private temporary folder;
Tesseract reads the image locally, and the image is deleted immediately after
processing. Only bounded recognized text and approximate line coordinates are
returned to help Burito distinguish split-screen regions. OCR can misread text
and does not identify objects or which app owns a region. Returned text may remain
in local Eve session history. No background capture occurs. The approval
reservation and dynamic tool list limit Burito to one attempted capture per
user message; send a new message to request another view.

Start with `--enable-desktop-control` as well when Burito should locate an app
window and focus it before capturing only the active window. The combined
`inspect_window` approval keeps a second dialog from stealing focus between
activation and capture. KDE's KWin window
snapshot includes captions for the current request only. It is queried on
demand through a temporary KWin script and a private, correlated, one-request
D-Bus service. Captions are returned to local chat history but are not written
to logs, the access audit target, or app activity summaries. The focus tool
rechecks the exact internal ID at execution time, then unminimizes and activates
that window. It may switch virtual desktops and cannot click or type. Visible
text OCR remains a separate approved step.
A missing KWin window does not prove the app process is stopped, since tray-only
and background apps may have no managed window. `active_window` OCR reads the
focused window after approval; `full_screen` remains available for desktop-wide
questions. KWin window control is currently scoped to KDE Wayland.
Run the local probe with `bash scripts/probe_kwin_windows.sh`. It prints the
script load ID, run result, whether the D-Bus report arrived, and the raw JSON
payload, then unloads the unique script and removes its temporary source.
Opening an app does not grant access to everything inside it. App-specific APIs,
accessibility controls, document parsers, and scoped write actions are later
integrations. Read access does not mean every file has been indexed or memorized.

The current model configuration is local-only. Requested excerpts enter local
chat/session history; deleting a source file does not delete prior chat content.
Actions are logged locally with action, target, time, and outcome, retaining
the newest 2,000 audit records; file contents are not copied into the audit log.
Approved launcher snapshots are retained under private Burito storage. Source
code and synthetic tests are pushed to GitHub, not file contents, inventory,
application lists, launcher snapshots, or audit records.

To enable the one-shot screen OCR tool for a session:

```bash
cd ~/Burito
python3 -m burito chat --model burito-local:8b --context-tokens 8192 --enable-screen-read
```

For named-app window detection, focus, and active-window OCR, enable both:

```bash
python3 -m burito chat --model burito-local:8b --context-tokens 8192 \
  --enable-screen-read --enable-desktop-control
```

Then explicitly ask Burito to read the current screen and approve the exact
capture in the chat. `spectacle` and `tesseract` must already be installed. The
tool is absent by default and unavailable when `--no-files` or `--activity-only`
is used. This is a first desktop-context slice; visual scene understanding and
typing/clicking controls are separate future integrations.

The backend and compiled tool discovery were tested locally. The restricted
development session cannot reach the model server or launch desktop apps;
model-initiated tool use and actual desktop launching require owner-run testing.
