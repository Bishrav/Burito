# Status

## Current verification

### Phase 3 release and Phase 4 planning (2026-11-27)

Phase 3 was merged through PR #4. The owner accepted deferring off-machine
backup and restoration: primary BURITO_BRAIN storage, an independent same-host
NVMe backup and isolated restoration are verified; physical reboot persistence,
synthetic cognitive functionality and local GPU inference passed. The owner
accepts that whole-computer loss could destroy both copies. Off-machine disaster
recovery remains unverified and deferred; it is required before migrating
important or irreplaceable private memories. Live KWin behavior remains
unverified. See the latest [development log](DEVELOPMENT_LOG.md) and
[brain storage](BRAIN_STORAGE.md) evidence.

Phase 4 work is on `feature/phase-4-sensory-intelligence`, based on merged main
at `6dc83b685498c55d2ce62b8bb6b8f0c38a6247f`. The roadmap is
[`PHASE_4_SENSORY_INTELLIGENCE.md`](PHASE_4_SENSORY_INTELLIGENCE.md). Phase 4A
now builds pinned CPU-only whisper.cpp in ignored `.tools`, with one 142 MiB
multilingual base model at `/mnt/burito-brain/models/audio/ggml-base.bin`.
Installation checks the verified brain UUID and refuses to overwrite existing
source/model files. The browser has explicit bounded capture, local
transcription, editable preview and text submission; it never auto-sends.
Qwen3 8B, system packages, drivers and system configuration are unchanged.
The owner verified live speech-to-text in Brave using AirPods. The working
PipeWire default capture source is `bluez_input.98:1C:A2:D6:65:85`; Brave's
microphone selection is **System default**. The owner also verified Cancel,
the 15-second recording limit, a clear denied-permission message, and
acceptable transcription of representative English recordings. Sample count,
accent/noise conditions, and quantitative accuracy are unmeasured; multilingual
accuracy remains unbenchmarked. One 11-second upstream
smoke clip matched its reference exactly (WER/CER 0.0 on one item; 0.649 s,
RTF 0.059, 282 MiB child RSS). This is not representative accuracy evidence.
The conversation system prompt now directs natural casual replies and avoids
repeated stock greetings. Explicit owner name statements are carried only in
that conversation's bounded transcript context, not persistent personal memory.
After prompt refinement, one live synthetic three-turn Qwen conversation gave a
brief greeting, acknowledged the name without a service prompt, and recalled the
name on request; its temporary conversation was deleted. This is a smoke check,
not a guarantee of identical behavior across prompts. Editable ASR transcripts
remain unsent until the owner presses Send.

Phase 0 is merged into main at `cd61b76`. Phase 1 adds a verified
loopback-only web chat path, status reporting, opt-in notifications and a Hyprland
window adapter. The historical records below include prior KDE observations.
See the [development log](DEVELOPMENT_LOG.md) for current host checks and
[Ryoku setup](RYOKU_SETUP.md) for startup instructions.

Synthetic startup against the verified permanent brain has now passed. No
pre-existing private memory database was found or migrated. Live KWin behavior
remains unverified; KWin regression tests passed.

Phase 2 is merged through PR #3 at `6e26054`. It provides live text deltas,
private transcripts, conversation search and management, configurable
personality, bounded context, cancellation and retry. Synthetic application
restart and SQLite recovery passed. Physical reboot remains unverified.
GitHub Actions run `45784416473` passed all four required jobs.

Phase 3 is underway on `feature/phase-3-memory-foundation`. Host inspection
verified the WDC WD40NPJZ-00CCDT0 in the Transcend StoreJet 25H3 enclosure, ext4
UUID `9428a980-24a6-45b2-a0a6-5e057c819406`, mounted read/write at
`/mnt/burito-brain`; `findmnt --verify` passed. A non-overwriting synthetic
write/read/fsync/checksum test passed. The existing `/memory` and `/manifest`
directories are reused. The version-1 manifest records the transactional
SQLite schema migration from v1 to v2. At migration time there were no memory
rows; the database passed `integrity_check`. Six non-personal Academy topic
progress records have since been added and verified after a fresh process.
Synthetic tests cover fresh-process
retrieval, correction history, explicit-key conflicts, deletion and temporary
backup/restore. No private memory content was migrated or inspected.

SMART health remains owner-reported and could not be independently queried
without the owner's sudo password. An earlier USB 2.0 CRC/read failure remains
in the boot log; after moving to SuperSpeed no further read/CRC error was seen,
though setup logged an unsupported discard operation. Reboot persistence and
independent durable backup remain unverified.

Host checks verified NVIDIA 620.70.06 and local Ollama 0.40.18. A live
`burito-local:latest` inference ran on the RTX 5070 at 100% GPU, 8,192 context,
with 6.3 GB reported model memory. No model or driver was installed. Python and
Node regression counts are recorded in the development log. Node 26's test
runner is configured to execute all eight test cases rather than count only
the four test files.

Latest Phase 3 verification: 133 Python tests passed on Python 3.11 and 133 on
Python 3.14; all nine Node test cases, Eve discovery, 153 source-integrity
checks, shell syntax and `git diff --check` passed. The Eve context bridge now
retrieves bounded, query-selected project, experience, Academy and knowledge
records. The desktop web launcher opts into project, experience and Academy
scopes; personal memory remains off. A normal local Eve/Ollama web session
answered four synthetic scenarios for project continuity, experience evidence,
Academy progress and personal-memory opt-out. First-text times were 1695, 211,
220 and 173 ms; total times were 3124, 1368, 1450 and 819 ms. The three
retrieval responses passed expected-term checks; the private marker was not
returned. Three synthetic brain records were deleted afterward.

The live follow-up (“And what is blocking it?”) returned the saved synthetic
blocker in the latest run after fixing project ranking. Two of three recorded
follow-up checks passed an exact expected-term assertion; one earlier response
did not pass that assertion and was not retained, so it may have paraphrased or
missed the record. Reference resolution is demonstrated, but its exact-answer
consistency remains an acceptance gap.

Earlier host verification confirmed `/mnt/burito-brain` as ext4 UUID
`9428a980-24a6-45b2-a0a6-5e057c819406`, mounted read/write, with about 3.6 TiB
free. The latest 2026-11-27 check sees the expected UUID mounted read-only;
`lsblk` identifies the WDC drive, but its device nodes were unavailable to
`smartctl` in this command environment. No remount or write was attempted.
Read-only SQLite integrity is `ok`; six Academy progress rows remain and
no synthetic test markers remain. Three existing home lesson references were
added because permanent web startup otherwise had no selected lesson; repeated
installation is idempotent. Fresh `burito-local:latest` inference succeeded; Ollama reports Qwen3
8B, 100% GPU placement, 6.3 GB model memory and 8192 context on RTX 5070 / driver
620.70.06. Retrieval v2 (1,011 temporary records, 13 cases) measured P@5 0.240,
recall@5 1.000, MRR 0.933, median 1.157 ms and p95 1.204 ms; it is not directly
comparable to v1 because the cases and normalization changed.

Independent backup remains blocked: the current block inventory shows only the
brain HDD and internal NVMe, so no separate physical target was available. The
owner reports successful SMART short and extended tests, but their logs remain
unverified here. Physical reboot remains unverified. No private
memories were read, migrated or altered. Phase 3 is not complete.

### 2026-11-27 release-candidate recheck

The feature commit `ee80d50013ed42ec1dcf357c3ec1290cfe20874f` is on the remote
feature branch; remote `main` remains `59cc670c55759c39e31a3839d9188d0c1e4e02ec`.
No CI statuses or workflow runs were reported for the feature commit. A
read-only integration check found six overlapping README merge regions; do not
merge without resolving them while preserving the research-oriented README.

The brain is currently mounted read-only. Read-only SQLite verification found
schema 2, `integrity_check=ok`, and six Academy records. The proposed independent
backup location is on the separate internal NVMe filesystem with about 67 GiB
free, but does not exist and was not created; `/home` was read-only in this
session and owner approval was requested. Synthetic backup/restore tests passed
in temporary storage; no backup or restoration test on the independent physical
destination has passed.

Current local checks: 137 Python tests passed on Python 3.11 and 137 on 3.14,
including loopback checks with no skips; Eve discovery and all nine Node cases
passed when run sequentially. Source integrity checked 153 files. The new
synthetic SQLite backup-manifest, restoration and tamper-detection tests passed.
NVIDIA 620.70.06 and the RTX
5070 were visible, but Ollama had no running server and no model files were
visible under the default model directory; no fresh inference or multi-trial
language-model cognition evaluation was possible in this session. The FTS5
synthetic suite remained at P@5 0.240, recall@5 1.000 and MRR 0.933; this run's
warm median/p95 were 1.169/1.211 ms. These are local synthetic measurements,
not evidence of broad semantic retrieval.

## Implemented

- Full staged roadmap and architecture decisions.
- Read-only machine diagnostics with bounded command execution.
- Local SQLite memory: explicit creation, listing, deletion, provenance.
- Schema-v2 memory categories and provenance, correction history, exact
  duplicate lookup, explicit-key conflict review and fail-closed migrations.
- Private project continuity with objectives, milestones, tasks, dependencies,
  decisions, blockers, next actions and evidence. Context is opt-in and bounded;
  completed tasks require directly observed or independently verified evidence.
- Structured experiences distinguish attempts from verified successful
  outcomes. Skill proposals cite verified experiences and remain
  non-executable even after owner review.
- Persistent Academy progress events use the private memory store. Tested CPU
  teaching code covers mathematical foundations and several classical ML
  algorithms.
- Synthetic retrieval evaluation and isolated intent classification report
  metrics, latency, baseline comparison and limitations; the ML candidate is
  not integrated into production.
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
- Local chat can opt into owner-maintained project context with `--include-project`;
  matching task experiences with `--include-experiences`; and Academy progress,
  curriculum metadata and local knowledge with `--include-academy`. The desktop
  web launcher enables these bounded scopes. Personal memory remains separate
  and excluded by default. Context grants no file or action permission.
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

## Current Phase 3 boundaries

- Only a synthetic record was written to the new brain database and then
  deleted. No private database or prior conversation was migrated.
- Project, experience, skill proposal and Academy records reuse the memory row
  format as bounded, versioned JSON records rather than separate relational
  tables. General language contradiction detection, automated consolidation,
  duplicate merging and retention expiry are not implemented.
- FTS5 remains lexical. The broadened 13-case synthetic suite reports P@5 0.240,
  recall@5 1.000 and MRR 0.933. One relevant result ranks below first; embeddings
  and calibrated relevance thresholds are not implemented.
- Academy progress and algorithms do not establish course mastery or production
  capability. Intent classification did not outperform the deterministic rule
  baseline and remains isolated. No production LLM weights were changed.
- Skill proposals have no executor. Accepting one grants no permissions.
- An independent NVMe backup and isolated restore passed on 2026-11-27. It is
  on the same computer, so off-machine recovery is still needed before any
  private-memory migration. SMART results remain owner-reported; reboot
  persistence remains unverified.

## Next

1. Independently inspect SMART health and the extended-test result from the
   owner's terminal using a stable device path; no second self-test was started.
2. Establish an off-machine backup and verified restore before migrating any
   private data. The current NVMe copy protects against brain-disk failure, not
   loss of the host.
3. Improve FTS5 precision on a broader owner-approved or licensed evaluation set;
   current metrics use small hand-authored synthetic examples.
4. Expand the Academy curriculum and exercises incrementally; several requested
   algorithms and all production capability evaluations remain unfinished.
5. Verify physical reboot persistence and keep private-memory migration gated.
6. Keep Phase 4 out of scope until Phase 3 acceptance criteria pass.

## 2026-11-27 host-access and live cognition update

The read-only mount/GPU failures observed by the previous Codex process came
from sandbox restrictions. Host-scoped checks confirmed `/home` is writable
Kingston NVMe Btrfs and `/mnt/burito-brain` is writable ext4 on the separate
WDC HDD with the expected UUID. The owner-approved, mode-700 backup directory
was created on NVMe. A 98,304-byte schema-v2 SQLite online backup and manifest
passed checksum, identity and integrity checks. Scratch restore preserved all
six Academy records and passed fresh-process retrieval, synthetic project
continuity, correction and deletion. No personal records were present or
migrated; this is not an off-machine backup.

The installed Ollama 0.40.18 server was inactive, with no duplicate service or
process. One temporary server was bound to `127.0.0.1`, using the existing local
model store. `burito-local:latest` (Qwen3 8B Q4_K_M) returned a real inference;
Ollama reported 100% GPU, 8,192 context, llamacpp runner, and 6.3 GB model
memory. NVIDIA driver 620.70.06 remained unchanged. Temporary servers were
stopped after verification.

A synthetic live evaluation used the actual web/Eve/Ollama streamed runtime,
with two trials each for project follow-up/next action/decision/blocker,
experience lesson, Academy stage, corrected/deleted/conflicting memory,
personal-memory opt-out, unknown information and retrieved prompt injection.
After enabling memory context only for the explicitly opted-in run and adding
deterministic redaction of obvious credential-like values, all assertions
passed in two trials per scenario. The first broad run's corrected/deleted/
conflict assertions correctly failed while personal context was opted out;
they passed with explicit opt-in. Before redaction, the model refused the
injected instruction but echoed its synthetic token; after redaction it withheld
the value in 2/2 live trials. Across 26 requests in the first run, median
latency was 504 ms and p95 1,271 ms. Targeted post-fix injection trials had
median 726 ms. These are small synthetic checks, not a broad generalization
claim.

`README.md` has six overlap regions when comparing feature content with the
research-oriented main revision. No README history was changed. The workflow
uses unfiltered `push` and `pull_request` triggers; GitHub's check-runs API shows
all four jobs on `ee80d500` completed successfully. The earlier zero-run result
came from a connector endpoint that filters to pull-request runs; a push run
did exist. No PR has been created. The connected GitHub integration reported
the feature branch is unprotected; no settings were changed.

After the final context-redaction change, 138 Python tests passed on Python
3.11 and 138 on Python 3.14 with no skips. Eve discovery, all nine Node cases,
153 source-integrity checks, shell syntax, and `git diff --check` passed. The
credential-pattern scan found no matches. The local branch now correctly tracks
`origin/feature/phase-3-memory-foundation`, whose commit matches HEAD.

Still unverified: actual reboot persistence, an off-machine backup/restore,
live KWin behavior and private-memory migration.

### 2026-11-27 Phase 3 integration update

The reviewed eight-file checkpoint was committed as
`aaee19dff61020679308c64fbe5c3d611fce656a`
(`fix: harden cognitive context and verify independent brain recovery`). The
feature branch then merged `origin/main` normally, retaining research README
commit `59cc670c55759c39e31a3839d9188d0c1e4e02ec`. README overlaps were resolved
to reflect verified Phase 3 status, `burito-local:latest`, and
`/mnt/burito-brain/memory`. Merge commit:
`f258efa375395d73152b8a463035e73244470da0`.

PR #4 is open: https://github.com/Bishrav/Burito/pull/4. GitHub Actions run
`45987228199` for merge commit `f258efa` completed successfully: source
integrity, runtime checks, Python 3.11, and Python 3.14 all passed. Local merged
tree verification also passed: 138 Python tests per version with no skips, Eve
discovery, nine Node tests, 153 source-integrity checks, shell syntax and diff
checks. No private database, backup, model weights or credential-like values
were found in the outgoing tracked files. No pull request merge was performed.

Release gates still open: physical reboot and automatic brain-mount persistence,
live KWin behavior, off-machine independent backup/restore, and any private
memory migration. The verified NVMe backup is on the same computer and does not
protect against loss of the host. Labeled-value context redaction is a limited
heuristic, not comprehensive secret or prompt-injection protection.

### 2026-11-27 post-reboot verification

The owner rebooted at 20:07:47. Host-scoped verification after boot confirmed
`/dev/sda1` mounted at `/mnt/burito-brain` as ext4 UUID
`9428a980-24a6-45b2-a0a6-5e057c819406`, with `rw,noatime`. `findmnt --verify
--verbose` passed with zero errors and warnings. `burito doctor` reported the
brain ready, about 3,665 GiB free, and the RTX 5070 visible. The version-1 brain
manifest matched the expected volume and schema 2. The SQLite database is an
owner-private regular file (0600), schema 2, `integrity_check=ok`; an aggregate
query counted all six Academy progress records without returning record text.
The previously created NVMe backup passed `Memory.verify_backup` again,
including SHA-256, schema, integrity and source brain UUID checks. No live
database writes or private-memory reads occurred during these checks.

An isolated synthetic cognitive test used four separate Python processes and a
temporary database: project milestone/blocker/next-action continuity, exact
memory retrieval, correction and revision-history retrieval passed; memory and
project deletion then passed and deleted records were not retrievable in a
subsequent process. The temporary store was removed. The six durable Academy
records were not modified.

Ollama was inactive after boot: no running server or user service was found.
It was started manually, loopback-only, with the existing model store; no
driver, model or weights were installed or changed. The existing
`burito-local:latest` (Qwen3 8B Q4_K_M) returned a synthetic local response.
`ollama ps` reported 100% GPU, 8,192 context and 6.3 GB loaded; `nvidia-smi`
identified RTX 5070 / driver 620.70.06. Burito web then reported Eve, bridge,
Ollama and model ready, and the local conversation endpoint returned a
completed response. Temporary web transcripts and both test runtime processes
were stopped/removed afterward. Automatic Ollama startup is not configured or
verified; this was a manual launch.

PR #4 remains open and mergeable. Latest head `6b6d5e3` passed GitHub Actions
run `45988020128` (source integrity, runtime checks, Python 3.11, Python 3.14).
The owner explicitly accepts deferring off-machine backup/restore for Phase 3
release. The existing internal-NVMe backup is separate from the brain disk but
cannot protect against loss of the computer; the owner accepts the risk that
such a loss could destroy both copies. Off-machine backup and a verified restore
remain required before migrating important or irreplaceable private memories.
This is deferred infrastructure work, not a tested capability or completed
requirement. Live KWin remains unverified. PR #4 is open; no PR merge or new
commit has yet been made at this checkpoint.

### 2026-11-27 owner risk acceptance and release authorization

The owner authorized Phase 3 release integration while explicitly deferring
off-machine backup and restoration. The owner has no additional suitable
storage device and does not wish to use the MacBook or cloud storage. The owner
accepts possible loss of both copies if the whole computer is lost or damaged.
Verified evidence remains: operational 4 TB brain; checksummed backup on the
independent internal NVMe and isolated restore; automatic brain mounting and
database integrity after reboot; six surviving Academy records; synthetic
cognitive tests; and local GPU inference. Off-machine recovery remains
unverified, is not represented as completed, and is a hard precondition for
migration of important or irreplaceable private memories.

The same-host NVMe backup reduces risk from failure of the brain HDD only. No
off-machine copy, private-memory migration, or live KWin test has been done.
The owner authorized committing and pushing final documentation, updating PR
#4, verifying fresh CI, and merging after required checks pass.
