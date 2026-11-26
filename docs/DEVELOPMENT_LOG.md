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
