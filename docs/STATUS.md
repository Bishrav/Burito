# Status

## Implemented

- Full staged roadmap and architecture decisions.
- Read-only machine diagnostics with bounded command execution.
- Local SQLite memory: explicit creation, listing, deletion, provenance.
- Private storage defaults outside Git; no observation or networking.
- Standard-library tests and GitHub Actions test configuration.

## Not implemented

AI chat, local/cloud inference, semantic retrieval, voice, desktop observation,
proactive suggestions, autostart, desktop actions, automatic training,
encryption, backups, and autonomous execution.

## Next

1. Verify host GPU and intended 4 TB storage mount.
2. Make a supported Node/npm runtime available.
3. Install and inspect the eve scaffold and bundled docs.
4. Select a local model after measuring VRAM, then add offline text chat.
5. Connect personal memory and demonstrate correction across sessions.
6. Add optional cloud routing with explicit context and budget configuration.
