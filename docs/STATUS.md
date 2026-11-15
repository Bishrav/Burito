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
  live eve/model integration is not yet verified.

## Not implemented

Verified AI chat, hybrid routing, semantic retrieval, voice, desktop observation,
proactive suggestions, autostart, desktop actions, automatic training,
encryption, scheduled backups, restore tooling, and autonomous execution.
Runtime dependency installation and live conversation remain unverified: the
restricted development shell has no direct download access. The runtime skeleton
now has a prepared read-only Python context bridge, pending installed-version
API checks and live end-to-end verification.

## Next

1. Verify host GPU with `nvidia-smi` in a normal terminal and identify the intended storage.
2. Run `bash scripts/setup-runtime.sh` in the normal terminal with internet.
3. Inspect installed eve docs, review and commit resolved dependencies/lockfile.
4. Select and install a local model after measuring VRAM, then verify offline text chat.
5. Verify the lesson bridge and optional personal memory, including correction.
6. Add optional cloud routing with explicit context and budget configuration.
