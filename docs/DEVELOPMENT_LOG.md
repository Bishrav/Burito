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
