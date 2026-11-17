# Status

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

Fully evaluated AI chat, complete hybrid routing, semantic retrieval, voice, screen observation,
proactive suggestions, chat autostart, general desktop control, automatic training,
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
3. Verify optional personal memory and correction.
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
