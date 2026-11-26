# Security boundaries

Keep Ollama, Eve and the development web bridge on loopback. Loopback services
are reachable by local processes. Before broader use, validate HTTP host and
origin handling, session authorization and request bounds. Remote use requires
authenticated device pairing, encrypted transport, revocation, rate limits and
a separately reviewed exposure design. Keep the desktop login in force.

The model proposes operations. Deterministic tooling validates scope, inputs,
targets and current owner approval before executing. Denial stops execution.
Files, pages, screenshots, tool output and retrieved documents are untrusted
data. Never collect passwords, authentication codes, browser session tokens
or private credentials. Limit browser coverage to needed sites when possible.
The extension declares optional HTTP and HTTPS host access, so site grants
and the native host's extension identity require separate verification.

Keep memory and logs out of Git, maintain independent backups, and retain only
needed audit metadata. Voice and screen input require explicit opt-in and visible
controls. Add cancellation, emergency stop, least privilege and sandbox limits
before durable automation. Owner approval is required for sensitive operations
and external side effects. The current loopback development runtime is for a
trusted local session. Review each integration before enabling it against
private data.


The Phase 1 browser-facing listener checks the literal loopback Host and
same-origin Origin, limits chat bodies, and exposes no generic Eve proxy.
The internal chat bridge requires a per-start token and accepts session IDs it
created. Eve's independent loopback development listener still follows Eve's
local-development trust model. Keep it off shared or remote interfaces.
