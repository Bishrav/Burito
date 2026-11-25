# File and application access

Burito now has explicit host tools, in addition to the inventory summary:

| Tool | Capability | Approval |
| --- | --- | --- |
| `files` | Browse folders, read bounded UTF-8 text, search filenames | No extra prompt |
| `applications` | Find registered desktop launchers and their exact IDs/hashes | No extra prompt |
| `open_application` | Submit a launch request for a selected, unchanged launcher | Every launch |
| `desktop_windows` | On-demand snapshot of KWin internal IDs, resource classes, captions, desktop/minimized/active state | No extra prompt; only exposed by `--enable-desktop-control` |
| `focus_window` | Unminimize and focus one exact window by internal ID | Every focus |
| `desktop_insert_text` | Insert exact owner-approved text at the caret in a focused, accessible native text field; does not replace text or access the system clipboard | Requires `--enable-desktop-control`; each insertion shows exact text and destination window for approval |
| `clipboard_write_text` | Write exact owner-approved or OCR-extracted text to the local system clipboard; does not read the clipboard or require Brave | Requires `--enable-desktop-control`, local `wl-copy` or `xclip`, and separate approval showing all text |
| `inspect_window` | After approval, focus one exact window and immediately OCR its active window | One approval covers focus and capture |
| `browser_search` | Search one exact query in the regular Brave profile, then capture its active window once with local OCR | Every search and capture under one explicit approval; query may remain in browser history; opt in with `--enable-browser-search` |
| `browser_navigate` | Open an exact HTTP/HTTPS URL in the active Brave tab | Every navigation requires approval |
| `browser_read_page`, `browser_page_action` | Read and briefly summarize visible text from the active Brave page using the configured local model; click a unique visible label, fill a non-password field, press Enter/Tab/Escape, scroll, or go back/forward | Opt in with `--enable-browser-control`; grant one site or all HTTP/HTTPS sites from the extension popup; every read/action asks approval |
| `browser_copy_text` | Write exact owner-approved text from the owner or current page result to the system clipboard; clipboard reads are not available | Requires `--enable-browser-control`, optional clipboard permission from the extension popup, and a separate approval showing the full text for every copy |
| `browser_tabs` | Read the open-tab count reported by the optional Brave extension | Every read requires approval; extension sends only a count; opt in with `--enable-brave-tabs` |

These run through a local Python bridge using the normal account's permissions.
They are not eve's built-in sandbox file tools. Default shell, file-write, web,
generic agent, and self-modification tools remain disabled.

Brave search sends the exact approved query to Brave Search over the internet;
Brave may make its normal page/resource requests and the query may remain in
browser history. Burito captures only the active Brave window with local OCR.
OCR may misread page text and does not prove result accuracy. It does not click
a result, submit a form, or download a file. Search-page content is untrusted
data.

## Brave tab extension

The optional Manifest V3 extension counts open tabs by default and sends only
the integer count to a local Native Messaging host. Finding a tab requires the
owner to grant the optional `tabs` permission from the extension popup. After
that, an approved lookup sends only titles matching the owner-provided phrase
and temporary tab IDs through a short-lived local command channel. URLs and
page contents are never sent. Switching tabs is a separate approval-gated
action bound to one exact title and ID; stale or renamed tabs are rejected.
The count snapshot is short-lived in `XDG_RUNTIME_DIR`; Burito rejects snapshots
older than 15 seconds. Tab titles are not written to logs or persistent memory.

To install it manually:

1. Open `brave://extensions`, enable Developer mode, choose **Load unpacked**,
   and select `~/Burito/runtime/browser-extension`.
2. Copy the extension ID shown on its card.
3. In Konsole, run `bash ~/Burito/scripts/install-brave-tab-host.sh EXTENSION_ID`,
   replacing `EXTENSION_ID` with that ID.
4. Restart Brave Origin so it connects to the local host. The extension popup
   displays the count it sees.
5. Start Burito with `--enable-brave-tabs` and approve a tab-count read.
6. To locate or switch tabs, open the Burito extension popup and choose
   **Enable tab labels** once. Then Burito asks approval for each title search
   and separately for each tab switch.
7. To read or operate a page, start chat with `--enable-browser-control` and
   open the extension popup. Choose **Enable this site** for one origin or
   **Enable all websites** once for regular HTTP/HTTPS pages. Broad access is
   granted only after the browser's permission prompt. Page text is returned
   only to the local Burito model after approval; each click, text entry, scroll,
   key press, or history navigation also requires its own approval. Password and file fields
   are refused. Submitting, sending, purchasing, publishing, or destructive
   actions need a separate explicit approval at the action prompt.

## Start and test

Exit the current chat with Ctrl+C, then use the all-tools local desktop profile:

```bash
cd ~/Burito
./scripts/start-chat.sh
```

This sets the brain drive, model, and context size, then exposes screen OCR,
KWin desktop controls, Brave tab/page/search tools, and local clipboard writing.
The script checks that `/mnt/burito-brain` is mounted before using it. Newly
added PC capabilities should be added to this one launcher. Each sensitive
read or action still asks for its own approval; this only makes the tools
available in the session. Personal facts remain excluded unless separately
enabled.

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

When the owner says “the page”, “here”, or “what is on screen” without naming
an app, Burito treats that as the visible desktop and uses approved screen OCR,
not Brave page reading. If multiple windows, displays, or OCR regions could be
the source, it asks which one before copying. Named Brave requests use the
Brave tools. Generic screen OCR needs `--enable-screen-read` at chat startup.

Start with `--enable-desktop-control` as well when Burito should locate an app
window and focus it before capturing only the active window. The combined
`inspect_window` approval keeps a second dialog from stealing focus between
activation and capture. KDE's KWin window
snapshot includes captions for the current request only. It is queried on
demand through a temporary KWin script and a private, correlated, one-request
D-Bus service. Captions are returned to local chat history but are not written
to logs, the access audit target, or app activity summaries. The focus tool
rechecks the exact internal ID at execution time, then unminimizes and activates
that window. It may switch virtual desktops; `focus_window` itself cannot click
or type. Visible text OCR remains a separate approved step. With desktop control
enabled, `desktop_insert_text` can place exact approved text at the caret in a
focused AT-SPI editable field. It verifies the destination window is active,
does not replace existing text, and does not read or modify the system clipboard.
For browser-to-native transfer, `browser_copy_text` writes exact text from the
owner or a current page result to the system clipboard after its own approval.
Reload the unpacked extension and grant its optional clipboard-write permission
once; every copy still requires a separate approval showing the full text.
Burito cannot read clipboard contents. A later `desktop_insert_text` places the
same text at the destination field without simulating Ctrl+V; both actions must
report success before Burito claims the transfer completed.
A missing KWin window does not prove the app process is stopped, since tray-only
and background apps may have no managed window. `active_window` OCR reads the
focused window after approval; `full_screen` remains available for desktop-wide
questions. KWin window control is currently scoped to KDE Wayland.
Run the local probe with `bash scripts/probe_kwin_windows.sh`. It prints the
script load ID, run result, whether the D-Bus report arrived, and the raw JSON
payload, then unloads the unique script and removes its temporary source.
Opening an app does not grant access to everything inside it. Native text
insertion only supports a unique focused accessible field; unsupported or
ambiguous fields are rejected. Other app-specific APIs and scoped write actions
are later integrations. Read access does not mean every file has been indexed
or memorized.

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

For the browser action, add `--enable-browser-search` alongside
`--enable-desktop-control --enable-screen-read`. Burito presents the exact query
and one-shot local OCR capture for approval, then opens a fixed
`https://search.brave.com/search` URL in the registered Brave Origin launcher.
Only that query is sent; chat history, memory, files, and inferred context are
not added. KWin identifies the Brave window and local OCR checks its visible
text. OCR can misread text and does not prove result accuracy. The temporary
image is deleted; OCR text may remain in local chat history. This action does
not click results, fill or submit forms, or download files.

Then explicitly ask Burito to read the current screen and approve the exact
capture in the chat. `spectacle` and `tesseract` must already be installed. The
tool is absent by default and unavailable when `--no-files` or `--activity-only`
is used. This is a first desktop-context slice; visual scene understanding and
general desktop typing/clicking remain future integrations.

The backend and compiled tool discovery were tested locally. The restricted
development session cannot reach the model server or launch desktop apps;
model-initiated tool use and actual desktop launching require owner-run testing.