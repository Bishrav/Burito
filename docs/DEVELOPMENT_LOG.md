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
