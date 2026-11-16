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
  explicit `--include-activity` flag. Activity remains excluded from normal chat.
- Prepared local-model configuration, read-only lesson bridge, and chat launcher.
  Local Python tests cover context selection, correction, and launcher boundaries;
  Installed eve discovery compiles and exposes only the three authored PC tools.
  The owner completed a local model conversation; answer-quality retesting remains.

## Not implemented

Fully evaluated AI chat, hybrid routing, semantic retrieval, voice, screen observation,
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
4. Add owner-reviewed suggestion records, feedback, duplicate suppression, and
   evidence links before making suggestions recurring.
5. Add the basic desktop interface around working text chat, followed by voice.
6. Add optional cloud routing with explicit context and budget configuration.

The intended 4 TB volume remains unidentified. The current Linux filesystem has
enough free space for this initial small model; use it for the first smoke test,
without repartitioning or changing Windows volumes. Plan large libraries and
model collections only after confirming the intended storage mount.

The owner reports Ollama installed and the `qwen3:8b` pull completed. The
restricted session cannot access loopback sockets to independently verify the
server. The owner started a conversation using `burito-local:8b` with an
8192-token context. Continue with the targeted verification steps above.
