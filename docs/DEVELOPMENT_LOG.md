# Development log

## Phase 0 repository recovery

Recovered 39 text files from their current blobs, including the browser
extension and pinned runtime manifests. Added a source integrity gate and
updated the Eve tests for turn-time tool registration. See the
[recovery report](RECOVERY_REPORT.md) for provenance and verification.

The isolated recovery worktree passed the source gate, both Python versions,
locked npm installation and six Node tests. A real local Eve/Ollama exchange
and synthetic launch denial passed. The GitHub workflow awaits publication
approval. The external drive, browser messaging and compositor integration
remain separate host checks.

## Phase 1 Ryoku integration

Started `feature/phase-1-ryoku` from GitHub main `cd61b76`. Local main
fast-forwarded to the same commit. Preserved the prior three setup artifacts
in the ignored `.tools/pre-phase1-setup` directory. The two colliding scripts
matched the tracked recovery versions.

- Used the installed Qwen3 8B alias to complete a real Eve turn from the web
  endpoint. Ollama reported full GPU placement at 8,192 tokens, with 6,916 MiB
  total GPU memory observed after the reply on the RTX 5070.
- In an isolated headless Brave profile, opened the existing interface,
  verified readiness enabled the composer, submitted a message, and observed
  the rendered reply `ready`. Browser status distinguished an unavailable
  dependency from an available model and runtime in the automated checks.
- Verified the desktop notification service accepted one generic successful
  chat notification. The notification contains no message or reply text.
- Verified the actual Hyprland 0.57.2 IPC snapshot and confirmed focus on the
  already-active window. The live IPC returns stable IDs as strings.
  Existing KWin tests and an adapter fixture cover its fallback.
- Read a scoped synthetic file through the host dispatcher. Rejected an
  unapproved launch, then used the approved dispatcher path to launch a
  temporary desktop entry through real Gio and verified its marker.
- Python loopback tests cover the web status and chat paths, external Host and
  Origin rejection, body limits and notification results. Existing tests
  preserve the KWin and action approval contracts.

Private memory was excluded from these checks. The external brain drive was
absent, so normal private-data startup remains unverified. Live KWin behavior
was unavailable on this Hyprland session. Phase 2 implementation has yet to start.

## Phase 2 natural conversation

Implemented actual Eve text deltas, runtime cancellation, HTTP
loopback APIs, and a private SQLite conversation store. A stored request UUID
prevents duplicate submissions. Retry preserves the original user message.
Conversation history supports titles, search, rename, deletion and restart
recovery. The web UI renders safe Markdown and fenced code, exposes copy controls,
and lets the owner set communication preferences.

The synthetic benchmark used Ollama 0.40.18 and Qwen3 8B at 8,192 context tokens.
The Phase 1 baseline displayed the complete reply at a median 3,468 ms.
Phase 2 displayed its first text at a median 116 ms and completed at a median
688 ms across three matching prompts. Median model rate was 93.2 output tokens/s.
Phase 2 also uses a shorter web prompt, no extended reasoning, and a 2,048-token
output cap, so the difference includes model configuration and transport changes.

The local evaluation passed follow-up reference resolution, name correction,
ambiguity handling, deterministic refusal of an unsupported desktop request,
duplicate prevention, cancellation, retry, client disconnection, application
restart, interrupted-turn recovery, 61 seeded long-history exchanges, Eve and
Ollama failure reporting, and runtime recovery. In Brave, a live partial reply
appeared before completion. Stop and retry preserved one user message and
the completed reply survived a browser reload. A separate real Ollama run streamed
successfully inside a network namespace with loopback as its only interface and
no default route. All 65 tests passed on each supported Python version, plus
eight Node tests, Eve discovery and source integrity.

The physical PC was not rebooted for QA. Web process restart and SQLite reopen
were exercised using a synthetic persistent database. The external brain drive
and live KWin session remained unavailable. The transcript context currently
uses attributed excerpts, and optional conversation branching is deferred.
No Phase 3 memory work was started.

### Master directive and review follow-up

Verified that local and GitHub main still point to `ac52f91`. Continued the
existing Phase 2 worktree, which already contained the uncommitted streaming
and conversation implementation. Recorded the long-term vision, cognitive
capability map, Academy plan and stable-identity storage design in four linked
documents instead of starting new production systems.

Addressed four review findings. The web runtime uses separate per-launch
loopback ports and checks its own Eve process. The transcript store releases
abandoned requests when SQLite becomes available after a failure. The browser
reconciles interrupted request IDs with saved history. Older context excerpts
now include the matched text. Persistent web startup validates the configured
brain filesystem UUID and type before opening its existing data directory.

The revised tree passed 69 Python tests on each of 3.11 and 3.14, eight Node
tests, Eve discovery and source integrity. A live synthetic reply succeeded
while listeners occupied both former fixed ports, without connecting to
either. The browser reconciliation check covered a failed history read followed
by recovery. The live 16-scenario evaluator and the isolated Brave streaming,
Stop, Retry and reload checks passed. For three matched prompts, median Phase 1
complete reply arrival was 3,683 ms; Phase 2 showed first text at 113 ms and
completed at 704 ms, with median model throughput 93.0 tokens/s. Prompt and
reasoning settings differ across phases, so this measures end-to-end behavior.
Physical reboot, private brain use and live KWin remain unverified.

### Phase 2 integration

Committed locally as `4b54fcd`, published as GitHub commit
`484c58d8f46f9e2491e398a5edba08062149fb9c` with an identical tree, and merged
through [PR #3](https://github.com/Bishrav/Burito/pull/3) at `6e26054`. GitHub
Actions run `45784416473` completed successfully: source integrity, runtime
discovery/tests, and Python 3.11/3.14 jobs all passed. Local loopback-enabled
verification passed 69 Python tests per interpreter, eight Node tests, Eve
discovery and the 133-file integrity check. A credential-pattern scan found no
issues across the 32 changed paths. The review also verified the four runtime,
request recovery, browser reconciliation and context-retrieval fixes described
above. Physical reboot was not run; brain-drive startup and live KWin remain
unverified. Benchmark comparisons are end-to-end and use different prompt and
reasoning settings, so they do not isolate a model-speed improvement.

## Phase 3 foundation (feature branch)

After PR #3 merged, created `feature/phase-3-memory-foundation` from the
integrated main. Read-only inspection on 2026-11-26 found a transient Transcend
block device reporting 0 bytes with no partition or filesystem metadata; it
disappeared before `smartctl --scan-open`. `/mnt/burito-brain` is absent. Existing
data, exact drive identity, capacity, health and performance cannot be checked.
No private database or disk content was read or changed. Brain integration,
private-memory migration, backups and persistent-memory schema changes remain
blocked until the stable volume is verified.

Started the Academy track with a standard-library one-variable least-squares
baseline and synthetic held-out tests for fit, metrics, degenerate inputs and
constant-target R². No education materials or datasets were downloaded. This
demonstrates only algorithm implementation and test correctness; it is not model
training, mastery or a production capability improvement. See [AI Academy](AI_ACADEMY.md)
and [brain storage](BRAIN_STORAGE.md).

### Read-only brain recheck and memory retrieval slice

The current recheck identified Transcend StoreJet 25H3 (USB ID `8564:7000`) on
a 480 Mbps USB 2.0 path. `lsblk` exposed a device-reported serial, omitted from
the tracked log because it identifies the physical drive; SMART did not confirm
it. `lsblk` reported 0 bytes/no partitions; kernel logs showed USB disconnect,
failed capacity reads and a not-ready device. The device was absent during
`blkid` inspection. `/mnt/burito-brain` and the conventional
local data directory were absent. A read-only SMART query could not proceed
because sudo requires a password. No drive writes, mounts, database reads or
system changes occurred.

Changed the default private data directory to the expected brain path and
centralized its UUID/filesystem check before any SQLite directory creation.
The doctor output no longer substitutes internal-disk free space for brain
capacity. Added query-focused memory retrieval using the existing records and a
temporary in-memory FTS5 index. Query-selected context retains the stored source;
the existing explicit opt-in for personal memory remains required. Correction
and deletion are reflected by rebuilding the volatile index. No persistent
schema or private DB changed.

On 1,010 synthetic records, a fixed project/storage query returned five relevant
records in the top five. Across 25 warm searches, median latency was 1.190 ms
and p95 was 1.942 ms on Python 3.14; this does not measure HDD performance.
These results do not justify embeddings yet. The isolated linear-regression
Academy slice remains synthetic and CPU-only.

The durable-memory opener now validates the configured brain identity, requires
an existing owned data directory, opens SQLite through a pinned Linux directory
descriptor and closes that descriptor with the connection. Tests verify that
an identity change during open creates no database and that an open database
does not fall through to an unmounted placeholder. This has only been tested
with synthetic filesystems; the Transcend drive is still unreadable and has not
been mounted or written.

The full current tree passed 83 Python tests each on Python 3.11 and 3.14,
including loopback HTTP and native systemd checks when run outside the sandbox.
Node reported four test files, Eve discovery passed, source integrity checked
136 files with zero failures, `git diff --check` passed, and the credential-
pattern scan found no matches. This environment snapshot showed the brain as
unavailable and NVIDIA device nodes hidden; it was an execution-context
limitation, not a fresh host check. See the 2026-11-26 update below.

### 2026-11-26 host activation and Phase 3 verification

The owner-reported USB 3.0 reconnection is reflected in the current host check.
`findmnt` verified UUID `9428a980-24a6-45b2-a0a6-5e057c819406`, ext4, and
read/write at `/mnt/burito-brain`; `lsblk` identified the WDC WD40NPJZ-00CCDT0
in the Transcend StoreJet enclosure. `df` reported 3.6 TiB available, and
`burito doctor` reported `brain_status: ready`. The existing fstab entry was
not changed. A unique 163,840-byte synthetic write/read/fsync/SHA-256 test
passed. The existing `memory/` and `manifest/` directories were reused.
The owner reports a prior 4 GiB sustained read test completed without I/O
errors at about 117 MB/s; it was not repeated during this implementation pass.

A version-1 manifest and SQLite schema-version-1 database were created on the
verified volume. In an isolated synthetic lifecycle, a fresh process retrieved
the sourced record, correction retained the record, deletion removed it from
retrieval, and SQLite integrity and temporary backup/restore passed. The
synthetic row was deleted; a later read-only check found zero memory rows and
`integrity_check` returned `ok`. No private memory was migrated or inspected.
An independent backup target and restore test remain unestablished. The mount
root is mode 700; `memory/` and `manifest/` directories are burito-owned mode
755 beneath that protected root, while the database and manifest files are
mode 600.

Host `nvidia-smi` reported RTX 5070, driver 620.70.06 and 12,227 MiB. A short
request to the installed `burito-local:latest` returned `READY`; `ollama ps`
then showed Qwen3 8B, 100% GPU, 8,192 context and 6.3 GB model memory. No model,
driver, Ollama server or system configuration was installed or changed.
Current sampled GPU use after inference was 4% with 7,044 MiB allocated; this
includes desktop/background use and is not an isolated inference benchmark.

The Python suite now has 87 tests and passed on Python 3.11 and 3.14 with host
loopback and systemd checks enabled. Node investigation found that Node 26's
default test isolation reported the four test files but did not execute their
eight declared cases. The package test command now disables per-file
isolation; all eight cases pass in the shared runner. Node documents this mode
for the supported v24 line ([official CLI reference](https://nodejs.org/download/release/v24.20.0/docs/api/cli.html#--test-isolationmode)). This preserves the Phase
2 test cases and fixes the misleading four-file result. The disk-full case is
also rejected before database creation. Eve discovery, source integrity (137
files), shell syntax, diff whitespace and credential-pattern checks pass. The
earlier retrieval measurement remains a small synthetic fixed-query
baseline (1,010 records, top-five recall 5/5, warm median 1.190 ms, p95
1.942 ms), not broad retrieval validation or an HDD benchmark.

SMART health and the owner-reported extended self-test remain owner-reported;
noninteractive smartctl access was denied and no test was started here. Actual
reboot persistence, independent backup/restore, live KWin and private-memory
migration remain unverified. Earlier USB 2.0 CRC errors are present in the
kernel history; no later read/CRC error was observed after reconnecting at
SuperSpeed, which does not prove long-term reliability.

### 2026-11-26 schema-v2 cognitive memory slice

Fetched `origin/main` at `59cc670` without moving or rebasing the dirty branch.
Integrated its research-oriented README presentation and architecture/research
content, carrying forward the branch's verified `burito-local:latest` alias
and `/mnt/burito-brain/memory` path. The fetched commit changes only README;
the feature branch remains one commit behind until its eventual clean
integration step.

Added a transactional schema-v1-to-v2 migration. Existing memory rows receive
neutral defaults (`semantic`, `owner_statement`, unknown confidence) and retain
their original content/source/timestamp. The manifest records schema migration
history; interrupted manifest update is recoverable because the next open
reconciles its schema version with SQLite. New metadata supports category,
confidence, verification label, owner-defined claim key, retention label,
updated timestamp and active/superseded state. Corrections save a private
revision snapshot; deletion cascades to revision/conflict history. Exact
normalized duplicate lookup does not merge records. Contradiction candidates
are produced only when the owner supplies the same claim key, avoiding an
unsupported general-language contradiction detector. Owner CLI commands show
history and conflicts and support review, dismissal and supersession. Context
includes provenance and unresolved-conflict indicators only when personal
memory is explicitly enabled.

Synthetic migration tests preserve legacy rows, reject unsupported versions,
verify manifest migration metadata, and exercise correction, conflict review,
supersession, search exclusion and deletion. With preflight confirming the
physical database contained zero memory rows and no other app tables, the live
brain was migrated to schema 2. Read-only verification found manifest/SQLite
schema 2, migration 1-to-2, zero memory rows and `integrity_check=ok`; `burito
doctor` still reports the brain ready. This changes schema only and is not a
private memory migration.

Final code review found and fixed a storage-boundary case where a configured
brain data path containing `..` could escape the mount. A regression test now
confirms the database is not created outside the brain.

The fetched README presentation and research content are integrated, with the
branch's verified model alias and brain path retained. Its content diff has
been reviewed; the feature branch remains one commit behind `origin/main` for
clean integration after this dirty work is reviewed. The expanded regression
suite passes 96 Python tests on Python 3.11 and 96 on Python 3.14 with no skips,
eight Node cases, Eve discovery, and 137 source integrity checks. These Python
runs used the host environment so loopback and systemd checks were exercised.
Final secret scan and full diff review are recorded with this batch's report.

### 2026-11-26 continuous Phase 3 implementation

Verified the exact worktree `/home/burito/Burito/.tools/phase-3-intelligence`,
branch `feature/phase-3-memory-foundation`, HEAD `6e26054` and one-commit
distance from `origin/main`. No staged changes were present. Preserved the
existing dirty work.

Resolved the Eve discovery artifact race: the discovery helper now validates
fresh CLI JSON, writes a unique mode-600 temporary file and atomically renames
it. The Node discovery test runs Eve directly rather than reading an artifact
that another test process may be truncating. Two concurrent discovery commands
and all eight Node cases passed together.

Added an owner-maintained project record format on the existing SQLite memory
store. It tracks objective, milestone, tasks, dependencies, decisions, blockers,
next actions, provenance and evidence. Project context remains opt-in and
bounded. A task cannot be marked complete until dependencies are complete and
evidence is explicitly marked direct observation or independently verified.
A synthetic project was created and updated by separate CLI processes; a later
process retrieved its milestone, pending task and next action through the
conversation context builder.

Added structured experience records. A task attempt remains distinct from a
successful outcome; success requires observed results, evidence and a direct or
independent verification label. Explicit skill proposals require verified
successful experiences and include inputs, prerequisites, tools, permissions,
procedure, expected result, verification, failures, recovery, version and
provenance. They remain non-executable before and after owner review.

Added persistent Academy topic progress with source references and event
history. States separate planned/source-verified/registered/retrieved topics,
passed exercises, implementations, reproduced experiments, benchmarks and
production approvals. Higher stages require evidence. The versioned starter
curriculum links verified MIT OCW and Stanford course pages; no course files
were downloaded or imported.

Added tested CPU implementations for vector/matrix operations, descriptive and
conditional probability, Bayes, numerical derivatives, generic gradient
descent, gradient-descent linear regression, regularized binary logistic
regression, k-NN, CART-style decision trees, k-means, binary/multiclass metrics
and deterministic train/test and train/validation/test splits. No dependencies or production model
weights were changed.

The new 1,009-record FTS5 evaluation covers eight query/lifecycle cases. It
reported precision@5 0.233, recall@5 1.000, MRR 1.000, median warm latency
1.130 ms and p95 2.102 ms over 40 searches in a temporary directory. The
single-query historical baseline is not directly comparable. A held-out
synthetic intent experiment compared deterministic rules and one-vs-rest
logistic regression: both scored 90% accuracy; candidate macro F1 was 0.889
versus 0.899. The candidate is not deployed.

Final verification after this batch: 125 Python tests passed on Python 3.11
and 125 on Python 3.14; all eight Node test cases and Eve discovery passed;
153 source files passed encoding/integrity checks; shell syntax and
`git diff --check` passed. A credential-pattern scan over 32 tracked changes
and 20 untracked source/doc files found no matches. The scan is heuristic, not a
secret detector.

The host mount was rechecked with `findmnt`: expected ext4 UUID mounted `rw` at
`/mnt/burito-brain`; `burito doctor` reported 3,665.4 GiB free and brain ready.
A synthetic project and Academy record were written on this volume, updated,
read from a fresh Python process, deleted by their exact IDs, and followed by
`PRAGMA integrity_check=ok`. The check did not inspect existing memory content;
the synthetic records were removed. Afterward, six non-personal Academy topic
records were persisted with repository test evidence and read from a fresh
process. They record implementation, not mastery or neural training. NVIDIA
620.70.06 and RTX 5070 were visible.
Ollama 0.40.18 and both local model aliases were present, but no model was
loaded during the final check; the earlier full-GPU inference result remains
the prior verified baseline, not a rerun in this batch.

The latest FTS5 suite reports P@5 0.233, recall@5 1.000, MRR 1.000, median
warm latency 1.130 ms and p95 2.102 ms (1,009 synthetic rows, eight cases,
five repetitions each). Low P@5 reflects returning up to five rows while most
queries have one relevant item. This does not establish semantic retrieval or
performance on the HDD. In the held-out synthetic intent experiment, both
rules and logistic regression scored 90% accuracy; candidate macro F1 was
0.889 vs 0.899 for rules. CPU training took about 1.63 s and peak process RSS
was about 12.1 MiB. The candidate remains isolated and is not deployed.

Ponytail review fixed a dependency-state edge case: a prerequisite task cannot
be reopened while a dependent task remains complete. Malformed project records
are ignored safely; category-filtered memory listing avoids loading unrelated
records; invalid Academy URLs are rejected. A test expectation initially
mislabeled a default-semantic fixture and was corrected. The final 125/125
suites passed.

The feature worktree is still dirty and one commit behind `origin/main`; no
commit, push, merge, physical reboot, independent backup test, SMART query or
private-memory migration was performed. Phase 3 remains in progress.

### 2026-11-26–27 conversational cognition integration review

Connected opt-in project, experience and Academy retrieval to the existing Eve
conversation path. The `open-ui.sh` desktop launcher enables those three
non-personal scopes. Personal facts remain off; context output is bounded and
the runtime instructions treat retrieved records as untrusted evidence, not
instructions or permissions. Fixed the permanent web startup path to reuse the
canonical `BRAIN_DATA` directory (`/mnt/burito-brain/memory`) instead of a
nonexistent sibling `data` directory. No additional service or dependency was
introduced.

An actual local web/Eve/Ollama run used `burito-local:latest` (Qwen3 8B,
8192-token context), synthetic project/experience records and the existing
Academy progress. Project continuity, experience evidence, Academy progress
and personal-memory opt-out all completed; the private synthetic marker was
not returned. A same-conversation follow-up, “And what is blocking it?”,
returned the saved synthetic blocker on one run (1.406 s total, 97.9 generated
tokens/s). On an earlier run, the turn completed but failed the expected-term
check; that response was not retained, so it is unclear whether it omitted the
record or paraphrased it. This exposes model/evaluation variability; the
follow-up is not yet a repeatably passed acceptance case. Other response times varied
between runs, so individual latency samples are not a stable benchmark. Each
run removed its three synthetic brain records and temporary transcript.

The expanded synthetic FTS5 evaluation has 13 cases and 1,011 temporary rows.
The latest run measured precision@5 0.240, recall@5 1.000, MRR 0.933, median
1.157 ms and p95 1.204 ms across 60 searches. It is not directly comparable to the prior
eight-case v1 score because the queries, normalization and selection changed.
One relevant result did not rank first. No score threshold or embedding layer
was added; the current data is insufficient to calibrate a relevance cutoff.

The isolated synthetic intent experiment remains out of production: rules
scored 90% accuracy and 0.899 macro-F1; logistic regression scored 90% and
0.889 macro-F1. Its tiny phrase-template dataset does not justify deploying a
learned model. A future experiment needs broader, independently authored
phrasing and more intent classes before comparing representations or model
selection.

Security review found that the backup API's lexical path check could be
bypassed with a symlinked parent pointing into the brain. The check now
resolves the existing parent and rejects brain descendants or the same
filesystem before creating a file. A synthetic regression test verifies the
symlink case. This does not prove that a different mounted filesystem is a
different physical device; the owner must still verify backup media identity.

The same review caught inverted project relevance sorting: a one-word match
could precede a three-word match. The ordering was corrected and a synthetic
test now verifies the stronger match is selected first.

After that fix, the actual local web/Eve/Ollama flow was repeated. Project
continuity, its pronoun follow-up (which quoted the exact saved blocker),
experience evidence, Academy context and personal-memory opt-out all passed
their checks. The five total response times were 4.498 s, 1.020 s, 1.348 s,
2.166 s and 1.072 s; corresponding first-text times were 3.237 s, 0.230 s,
0.198 s, 0.260 s and 0.207 s. The follow-up generated 79.9 tokens/s. These are
single-run local samples, not a stable latency benchmark. All three synthetic
brain records and the temporary transcript were removed.

Final host checks for this batch: 133 Python tests per supported interpreter
(3.11 and 3.14), nine Node tests, Eve discovery including two concurrent
discovery invocations, 153 source-integrity checks, shell syntax and diff
whitespace checks passed. The discovery helper validates CLI JSON, writes a
unique mode-600 temporary file and atomically renames it. The checked
`.eve-info.json` parsed as JSON and had mode 600. Read-only brain verification
found the expected ext4 UUID mounted read/write with about 3.6 TiB free,
`integrity_check=ok`, six Academy progress records and no remaining synthetic
marker records. Fresh inference succeeded; `ollama ps` reported
`burito-local:latest`, Qwen3 8B, 100% GPU allocation and 8192 context on the
RTX 5070. These are point-in-time host observations, not physical reboot or
long-term drive guarantees.

No second physical backup device was present, so independent backup/restore
remains blocked. The owner reports that SMART short and extended self-tests
passed. This session could not verify their logs: `lsblk` showed the WDC drive,
but `/dev/sda` device nodes were absent in the command namespace and `smartctl`
returned “No such device.” The latest brain mount observation was read-only;
no remount or write was attempted. Physical reboot, live KWin and private-memory
migration remain unverified. No private memories were read, migrated or altered.

#### Checkpoint — next session

1. Recheck branch and worktree after this feature-branch push; do not rebase or
   merge main.
2. Verify the brain is mounted by UUID and currently `rw` before any durable
   write. If still read-only, stop brain writes and diagnose without remounting
   or repairing the filesystem.
3. With the device node available, read `smartctl -x` and the self-test log;
   confirm the owner-reported short and extended results.
4. Attach and identify a separate physical backup target. Run a synthetic
   consistent backup, restore it to scratch, and verify SQLite integrity before
   proposing any private-memory migration.
5. Coordinate any physical reboot with the owner; after boot, verify UUID,
   filesystem, mount options and `burito doctor` readiness.
6. Repeat the conversational reference-follow-up evaluation with saved replies
   and varied synthetic projects; quantify consistency before closing that gate.

Do not begin Phase 4. Do not migrate private memories, back up to the same
drive, remount or repair the filesystem, reboot, merge main, or force-push.

### 2026-11-27 Day 2 release-candidate checkpoint

Verified `/home/burito/Burito/.tools/phase-3-intelligence` on
`feature/phase-3-memory-foundation`, clean at `ee80d50013ed42ec1dcf357c3ec1290cfe20874f`.
GitHub's feature ref matched that commit; remote `main` is
`59cc670c55759c39e31a3839d9188d0c1e4e02ec`. The README commit is present on
remote main. A three-way README check reports six overlapping regions between
main's research revision and the feature's Phase 3 updates. Preserve both
histories and reconcile these sections explicitly before PR integration. The
GitHub connector returned no check statuses or workflow runs for this commit.

Owner-supplied SMART results were documented in `BRAIN_STORAGE.md`: overall
health passed; short and extended tests completed without error; reallocated,
pending, uncorrectable and UDMA CRC counters were zero; no SMART errors were
logged; temperature 33 °C; power-on hours 48. This session did not independently
read the SMART log.

The currently visible brain mount is the expected ext4 UUID but read-only.
`burito doctor` reported `read_only`. SQLite opened read-only and returned
schema 2, `integrity_check=ok`, six total rows and six Academy progress records;
no memory content was queried. The 98,304-byte database has not been backed up
to an independent destination. The proposed path under `/home/burito/.local/
share/burito-backups` resolves to the separate NVMe (`/dev/nvme0n1p8`) with
71,909,986,304 bytes available and no existing symlink component. It was not
created: this session sees `/home` read-only and requested owner approval.
No restore test was attempted.

Added a checksummed backup manifest containing schema, source brain identity
when applicable, timestamp and restore compatibility. Verification uses
owner-only regular files and no-follow descriptors; synthetic restoration and
tamper detection tests passed. The actual independent destination remains
uncreated pending approval and a writable `/home` mount.

Current validation: 137 tests passed on Python 3.11 and 137 on Python 3.14,
including loopback web integration with no skips; source integrity passed for
153 files. Eve discovery followed by Node tests passed sequentially (9/9). An
intentionally concurrent discovery/test attempt produced an empty Eve JSON
response; the supported sequential CI order passed. Shell syntax checks passed.
The reproducible 13-case FTS5 suite returned P@5 0.240, recall@5 1.000,
MRR 0.933, median 1.169 ms and p95 1.211 ms over warm temporary-index searches.

`nvidia-smi` saw RTX 5070, driver 620.70.06, 12,227 MiB VRAM and 835 MiB in
use. The Ollama client is 0.40.18, but no server process or default model files
were available in this execution environment. No model was downloaded and no
fresh inference or multi-trial cognitive conversation evaluation was run.
Earlier 100% GPU inference and conversational results remain historical
evidence, not today's verification. No reboot, mount change, backup, private
memory migration, merge, commit or push was performed today.

#### Next actions

1. Obtain approval before creating the independent backup destination. When
   `/home` is writable, use `Memory.backup` and `Memory.verify_backup`; restore
   only into isolated scratch and verify schema, six Academy records, synthetic
   continuity and integrity. Do not overwrite the live brain.
2. Re-run the actual local Ollama model and multi-trial synthetic cognitive
   benchmark from the owner's normal Ryoku session; keep transcript and brain
   fixtures outside Git and remove them after verification.
3. Coordinate reboot verification with the owner; verify brain UUID/mount,
   SQLite, Academy/project continuity, Ollama and GPU after boot.
4. Resolve the six README overlaps while keeping the research content and
   accurate Phase 3 status. Re-run the release gates and inspect CI before
   proposing PR integration.
5. Keep private-memory migration and Phase 4 gated. Live KWin remains
   unverified.

### 2026-11-27 host access, independent restore and live cognition

Verified the exact Phase 3 worktree and preserved the six pre-existing modified
files. `pwd`, branch and diff checks confirmed the feature worktree at
`ee80d50013ed42ec1dcf357c3ec1290cfe20874f`; no Git operations changed its
history. Host-scoped `findmnt` showed that the prior read-only observations
were imposed by the Codex sandbox. On the physical host, `/home` is writable
Btrfs on Kingston NVMe and `/mnt/burito-brain` is writable ext4 on the separate
WDC HDD, UUID `9428a980-24a6-45b2-a0a6-5e057c819406`. The approved target parent
resolved without symlinks, had burito ownership and about 67 GiB free.

Created `/home/burito/.local/share/burito-backups` mode 700. `Memory.backup`
created a 98,304-byte mode-600 SQLite online backup and private manifest.
`Memory.verify_backup` confirmed SHA-256, schema v2, expected brain UUID and
SQLite integrity. Restored using SQLite's backup API into a mode-700 temporary
scratch directory on NVMe. Integrity and schema checks passed and all six
Academy progress records were preserved. Fresh-process retrieval, synthetic
project continuity, correction and deletion passed; the live brain was never
overwritten. No private conversation/memory data was read or migrated. The
backup is physically separate from the brain HDD but still on the same PC, so
it does not establish off-machine disaster recovery.

Ollama 0.40.18 had no active system/user service or process. The existing
model store was found at the main checkout's ignored `models/ollama` path; the
feature worktree's model directory is empty. Started one temporary server on
`127.0.0.1` with the existing store, then stopped it after testing. The
existing `burito-local:latest` alias returned `LOCAL_MODEL_READY`; `ollama ps`
reported Qwen3 8B, 100% GPU, 8192 context, llamacpp, and 6.3 GB loaded. NVIDIA
reported RTX 5070, driver 620.70.06, 12,227 MiB VRAM. No model or driver was
installed.

The live synthetic benchmark ran the real loopback web/Eve/Ollama streaming
path. Across two trials each, project follow-up, next action, decision, blocker,
experience lesson, Academy stage, corrected record, deleted record, conflict,
personal-memory opt-out, prompt injection and missing-record honesty met their
assertions after running memory-content scenarios with explicit opt-in. The
first 26-turn broad run showed 18/24 assertions: the six failures were the
corrected/deleted/conflict cases run with personal memory disabled, which
correctly excluded those semantic records. Those cases passed in 2/2 subsequent
explicit-opt-in trials. Personal opt-out passed in 2/2. Prompt-injection refusal
initially echoed the synthetic token in 2/2 trials; deterministic credential-
like value redaction was added before context reaches Eve. The new unit test
checks redaction and the real runtime withheld the token in 2/2 post-fix trials.
This guards obvious labeled secrets only; it is not complete secret detection.
Across the broad run, median latency was 504 ms and p95 1,271 ms; post-fix
injection median was 726 ms. Test cases and response scoring are synthetic and
small; latency includes streamed request/response wall time, not TTFT.

README comparison found exactly six overlapping regions between feature and
main. The proposed resolution is to retain main's research introduction,
architecture figure, limitations, reproducibility and security sections, and
merge only accurate Phase 3 implementation/status facts into its capabilities,
memory, brain, model alias, storage path and roadmap sections. No README merge
or history rewrite was performed. Workflow `tests.yml` has `push` and
`pull_request` triggers with no branch filter. The connector helper used earlier
filters to PR-triggered runs, so it returned zero for this push. Direct GitHub
API inspection found run `45877663332` for the feature branch and all four
checks for `ee80d500` completed successfully: source-integrity, runtime-checks,
Python 3.11 and Python 3.14. The feature branch is not protected; no settings
were changed.

No reboot was performed. Reboot persistence, off-machine backup/restore,
live KWin operation and private-memory migration remain unverified. An
owner-coordinated reboot checklist is: save and close work; verify backup
checksum/restore first; close Burito/Ollama processes; reboot manually; check
`findmnt -T /mnt/burito-brain`, compare UUID `9428a980-24a6-45b2-a0a6-5e057c819406`
and ext4; run `python -m burito doctor`; check SQLite `PRAGMA integrity_check`
and the six Academy rows; then start the local Ollama service and verify
`ollama ps`, `nvidia-smi`, and a `burito-local:latest` response.

Final local gates after the context-redaction change: 138 Python tests passed
on Python 3.11 and 138 on Python 3.14 with no skips; Eve discovery passed; all
9 Node cases passed sequentially; source integrity passed for 153 files;
`bash -n scripts/*.sh` and `git diff --check` passed. The credential-pattern
scan found no credential-like matches. No database, model blob, backup artifact
or credential is staged. The existing documented brain UUID remains in the
working documentation diff; it is not a credential, but it is host-specific.

The local branch upstream was corrected to
`origin/feature/phase-3-memory-foundation`; it now has no ahead/behind commits.
This changed only local branch tracking configuration, not Git history or the
worktree checkpoint.
