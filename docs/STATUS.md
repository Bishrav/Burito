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
- Prepared local-model configuration, read-only lesson bridge, and chat launcher.
  Local Python tests cover context selection, correction, and launcher boundaries;
  Installed eve discovery compiles successfully and exposes no action tools.
  Live model conversation is not yet verified.

## Not implemented

Verified AI chat, hybrid routing, semantic retrieval, voice, screen observation,
proactive suggestions, chat autostart, desktop actions, automatic training,
encryption, scheduled backups, restore tooling, and autonomous execution.
Runtime dependency installation succeeded through the normal desktop terminal.
Node 26.13.1 and eve 1.0.0-rc.18 are installed. Exact package versions and the
generated lockfile are committed. Installed-version documentation was checked;
discovery reports zero errors. The gateway-catalog warning in the restricted
shell does not block this local configuration, which supplies its context size.
The read-only Python context bridge and live model remain to be tested together.
Default model action tools and development extensions are disabled; CLI telemetry
and trace content capture are disabled by the launcher.

## Next

Host GPU verification succeeded in the owner's normal terminal: RTX 5070,
12227 MiB VRAM, NVIDIA driver 595.99.02. The restricted session's missing GPU
device files do not require a driver reinstall.

1. Install Ollama in the normal terminal, then prepare the first small local model.
2. Start with `qwen3:8b` and an 8192-token context; verify actual GPU placement
   and response behavior before increasing size. This is a starter choice,
   not a claim of best possible model quality or measured performance.
3. Verify the lesson bridge and optional personal memory, including correction.
4. Add the basic desktop interface around working text chat, followed by voice.
5. Add optional cloud routing with explicit context and budget configuration.

The intended 4 TB volume remains unidentified. The current Linux filesystem has
enough free space for this initial small model; use it for the first smoke test,
without repartitioning or changing Windows volumes. Plan large libraries and
model collections only after confirming the intended storage mount.

The owner reports Ollama installed and the `qwen3:8b` pull completed. The
restricted session cannot access loopback sockets to independently verify the
server. Next run `ollama create burito-local:8b -f config/ollama/Modelfile` in
Konsole, then start chat with that model and `--context-tokens 8192`.
