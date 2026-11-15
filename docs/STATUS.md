# Status

## Implemented

- Full staged roadmap and architecture decisions.
- Read-only machine diagnostics with bounded command execution.
- Local SQLite memory: explicit creation, listing, deletion, provenance.
- Private storage defaults outside Git; no observation or networking.
- Standard-library tests and GitHub Actions test configuration.
- Diagnostics distinguish a loaded NVIDIA driver with hidden device files from
  evidence of a host driver failure.
- Interactive local home education, memory correction, consistent private backups.
- User-local Node/eve installer and initial agent identity instructions.
- Versioned eleven-lesson beginner curriculum, local knowledge installation,
  source provenance, manual review prompts, and separate personal/general stores.
- Bounded, one-lesson context builder; personal facts excluded by default.
- Prepared local-model configuration, read-only lesson bridge, and chat launcher.
  Local Python tests cover context selection, correction, and launcher boundaries;
  Installed eve discovery compiles successfully and exposes no action tools.
  Live model conversation is not yet verified.

## Not implemented

Verified AI chat, hybrid routing, semantic retrieval, voice, desktop observation,
proactive suggestions, autostart, desktop actions, automatic training,
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

1. Verify host GPU with `nvidia-smi` in a normal terminal and identify the intended storage.
2. Select and install a local model after measuring VRAM, then verify offline text chat.
3. Verify the lesson bridge and optional personal memory, including correction.
4. Add the basic desktop interface around working text chat, followed by voice.
5. Add optional cloud routing with explicit context and budget configuration.
