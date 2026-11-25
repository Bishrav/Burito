# Status

## Current verification

Phase 0 recovery is in the dedicated recovery worktree. The historical records
below include prior KDE observations. Consult the [recovery report](RECOVERY_REPORT.md)
for current checks and [Ryoku setup](RYOKU_SETUP.md) for current host compatibility.
## Implemented

- Full staged roadmap and architecture decisions.
- Read-only machine diagnostics with bounded command execution.
- Local SQLite memory: explicit creation, listing, deletion, provenance.
- Private storage defaults outside Git; no screen capture or inventory uploads.
- Standard-library tests and GitHub Actions test configuration.
- Diagnostics distinguish a loaded NVIDIA driver with hidden device files from
  evidence of a host driver failure.
- Interactive local home education, memory correction, consistent private backups.
- User-local Node/eve installer and initial agent identity instructions.
- Versioned eleven-lesson beginner curriculum, local knowledge installation,
  source provenance, manual review prompts, and separate personal/general stores.
- Bounded, one-lesson context builder; personal facts excluded by default.
- Local machine inventory, bounded home-file metadata change detection, a
  systemd user timer installer, pause/status controls, and bounded local chat
  inventory summaries. Timer activation must be verified in Konsole.
- Explicit host file browsing, bounded UTF-8 reading, filename search, desktop
  application discovery, and approved launch requests. `--no-files` disables
  these tools. The owner verified folder listing, a README excerpt/line count,
  application discovery, and a visible Dolphin launch.
- Fixed the inventory service's quoted WorkingDirectory path, which systemd
  rejected at startup. Status now reports both timer and service details.
  The owner manually corrected the generated unit and confirmed the timer is
  active; its first scan completed and a synthetic file-addition event appeared.
- Opt-in KWin observer records foreground app IDs into the private local
  database. The owner verified Konsole and Dolphin events and confirmed pause
  disables both the KWin script and collector while retaining Burito records.
- App context labels can be added, listed, updated, or removed with provenance
  separating owner-confirmed notes from generic app-role descriptions. Reports
  do not treat either as inferred interests. Activity clear removes the local
  events and labels together.
- Local chat can receive a bounded seven-day activity summary only with the
  explicit `--include-activity` flag. `--activity-only` additionally excludes
  PC inventory, personal facts, and PC tools. Activity remains excluded from
  normal chat.
- Owner feedback can be explicitly recorded, listed, and deleted in the private
  local database. Normal chat receives it only with `--include-feedback`;
  activity-only chat excludes it. Feedback is context, not model-weight training.
- Suggestions can be manually recorded with owner-entered evidence, reviewed
  as pending/accepted/dismissed, listed, and deleted. Exact normalized text
  duplicates reuse the original entry and append evidence. Similar-but-different
  wording is not yet detected; suggestions are not yet generated or surfaced by
  Burito automatically.
- Local chat can optionally receive a curated Burito repository map and current
  milestone with `--include-project`. Activity-only sessions exclude it; the map
  does not grant file access and instructs the model not to invent unlisted paths.
- The chat launcher clears inherited eve development queue-routing variables
  and takes a per-runtime lock so a second Burito chat cannot share the same
  local workflow state concurrently.
- Ordinary local chats can opt in to up to five recent pending or accepted
  suggestions with their evidence using `--include-suggestions`. Dismissed items
  are excluded, activity-only mode forces this off, and the context is not
  permission to act.
- Private owner glossary supports explicit term definitions, retrieval alongside
  personal memory, duplicate detection, update, listing, and deletion. An
  approval-gated Eve tool saves a definition only after the owner confirms both
  the meaning and the save request. The web UI does not yet expose Eve approval
  interactions; use the interactive local Eve chat for this workflow.
- An approval-gated local chat tool can correct an existing owner fact when
  personal memory is explicitly included. It requires an explicit owner request,
  shows the old and replacement text for approval, and checks the original value
  has not changed before writing. New facts are not silently saved. This path
  still needs owner verification in a fresh chat.
- An opt-in, approval-gated screen OCR tool captures one full screen with KDE
  Spectacle and extracts text locally with Tesseract. Images use a private
  temporary directory and are deleted after OCR; OCR text may remain in Eve
  session history. This is not continuous observation or visual scene
  understanding. OCR preserves approximate text
  coordinates for split-screen summaries. A per-turn reservation limits it to
  one attempted capture per user message. It requires owner-run verification.
- An additional opt-in KDE window bridge lists KWin-managed windows on demand,
  including transient captions, resource class, internal ID, desktop and
  minimized/active state. Responses use a short-lived correlated D-Bus service;
  captions are not written to logs or audit targets. Focusing one exact window
  requires approval and revalidates its internal ID before
  unminimizing/activating it. A combined approved inspect
  action focuses the exact window and immediately captures it for local OCR.
  Titles appear in local chat tool results but are not added to the continuous
  activity database. Fake-D-Bus tests cover the bridge; live KWin behavior is
  still unverified. See `docs/PC_ACCESS.md` for the desktop probe.
- Optional Brave Search is exposed only with `--enable-browser-search` and an
  explicit per-query approval. It sends only the exact query to a fixed Brave
  Search URL in the regular Brave profile (Brave may make its normal
  page/resource requests; the query may remain in browser history), then
  captures the active Brave window once with local OCR. It never clicks,
  submits, or downloads. OCR can misread text and does not prove result
  accuracy. This path still needs an owner-run check.
- An optional Brave tab extension counts tabs by default. With optional
  `tabs` permission, it supports approval-gated title matching and switching
  to an exact tab. Titles are transient local response data only; URLs and page
  contents are not collected. The owner must reload the unpacked extension and
  grant tab-label permission from its popup before using find/switch.
- Basic Brave page access is implemented behind `--enable-browser-control`.
  It supports approved visible-text reads, uniquely labeled clicks and
  non-password field entry, Enter/Tab/Escape, scrolling, and back/forward.
  Site origins require a popup permission grant; every read and action asks
  approval. The owner reports successful page reading, phrase lookup, and
  Brave search. Clicks, form entry, and cross-app transfer still need owner
  verification.
- A scoped, approval-gated native text insertion tool focuses one exact
  KWin-managed window and inserts exact text at its focused AT-SPI editable
  field without replacing existing text. It is available only with
  `--enable-desktop-control`, does not touch the system clipboard, and has not
  been verified in the owner's live desktop.
- An optional, approval-gated `browser_copy_text` tool writes exact text to the
  system clipboard through the local Brave extension. The extension requests
  write-only clipboard permission once; each copy still shows the exact text
  for approval. No clipboard read is implemented. Browser-to-native transfer
  can copy then insert the same text, but requires extension reload/permission
  and owner-run checks; it is not a simulated Ctrl+V and has not been verified
  in the owner's live session.
- A separate local `clipboard_write_text` tool can copy exact text taken from
  screen OCR or another approved source without a Brave window, when `wl-copy`
  or `xclip` is installed. It is write-only and requires approval showing all
  text. Screen-source selection rules now default generic “page/here/on screen”
  requests to the visible desktop; ambiguous windows or screen regions require
  clarification. These paths remain unverified on the owner's machine.
- Eve's local dev transport uses a per-process secret. Burito archives the
  previous `.workflow-data` directory before starting chat or web, preventing
  persisted queue deliveries from an earlier process from being retried with a
  stale secret. Archives stay local under `runtime/.eve`; the separate Burito
  memory database is untouched.
- The agent prompt was reduced substantially after an 8K-context session
  failed before its first turn. Large PC inventory data is now omitted unless
  the owner asks about PC details, and retrieved context is capped relative to
  the configured context window. Build succeeds; a live 8K chat turn still
  needs owner verification.
- Optional CLI online research is isolated from the local chat model. It is
  absent unless `--enable-online` is passed, requires an explicit Gateway key
  and answer model, and asks for approval for each exact query. Only that query
  is sent; conversation context is not forwarded. Activity-only chat rejects
  online mode. Live provider success, denial, timeout, and outage paths remain
  unverified; see `docs/ONLINE_RESEARCH.md`.
- Safe checkout auto-update scripts and a per-user systemd timer are prepared.
  They fetch every 15 minutes and fast-forward only a clean `main` tracking
  `origin/main`; they defer while Eve is active, reject divergence, and defer
  dependency-manifest changes. The timer still needs to be enabled from the
  owner's Konsole. See `docs/AUTO_UPDATE.md`.
- Prepared local-model configuration, read-only lesson bridge, and chat launcher.
  Local Python tests cover context selection, correction, and launcher boundaries;
  Installed eve discovery compiles and exposes only the three authored PC tools.
  The owner completed a local model conversation; answer-quality retesting remains.

## Not implemented

Fully evaluated AI chat, complete hybrid routing, semantic retrieval, voice, continuous screen observation,
proactive suggestions, chat autostart, general desktop UI control, automatic training,
encryption, scheduled backups, restore tooling, and autonomous execution.
Automatic interest inference, owner-reviewed suggestions, lock-state handling,
and a visible observer status indicator are still future work. App foreground
time is not treated as proof of active use or interest.
Runtime dependency installation succeeded through the normal desktop terminal.
Node 26.13.1 and eve 1.0.0-rc.18 are installed. Exact package versions and the
generated lockfile are committed. Installed-version documentation was checked;
discovery reports zero errors. The gateway-catalog warning in the restricted
shell does not block this local configuration, which supplies its context size.
The owner completed a first chat with `burito-local:8b` through the launcher.
The answer separated guesses but confused user-reported evidence with direct
observation. Home honesty lesson revision 2 and standing instructions now make
that distinction explicit; revised model behavior awaits an owner-run retest.
Personal-memory retrieval/correction and actual GPU placement remain unverified.
Default model action tools and development extensions are disabled; the authored
application-launch tool requires owner approval. CLI telemetry
and trace content capture are disabled by the launcher.

## Next

Host GPU verification succeeded in the owner's normal terminal: RTX 5070,
12227 MiB VRAM, NVIDIA driver 595.99.02. The restricted session's missing GPU
device files do not require a driver reinstall.

1. Retest the honesty question in a fresh chat after installing lesson revision 2.
   File/application tool calls have passed the initial owner-run checks.
2. Inspect `ollama ps` during an active model session to verify GPU placement;
   measure warm response times separately from the first observed 48-second exchange.
3. Verify personal-memory retrieval and the approval-gated correction tool in a
   fresh chat; confirm the edited fact is used in a later chat and can be
   deleted. New facts are still added through the CLI.
4. Verify project-grounded answers and opt-in suggestion context in Konsole.
   Later add semantic duplicate detection and suggestion generation only with
   explicit evidence and owner review before recurrence.
5. Add the basic desktop interface around working text chat, followed by voice.
6. Verify optional online research approval, query-only context boundaries,
   offline behavior, and failure cases; then add persistent budget limits and
   routing telemetry before considering any cloud chat mode.

The intended 4 TB volume remains unidentified. The current Linux filesystem has
enough free space for this initial small model; use it for the first smoke test,
without repartitioning or changing Windows volumes. Plan large libraries and
model collections only after confirming the intended storage mount.

The owner reports Ollama installed and the `qwen3:8b` pull completed. The
restricted session cannot access loopback sockets to independently verify the
server. The owner started a conversation using `burito-local:8b` with an
8192-token context. Continue with the targeted verification steps above.
