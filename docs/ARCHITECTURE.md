# Architecture
See the [cognitive architecture map](COGNITIVE_ARCHITECTURE.md) for planned responsibilities and research gates.

## Current boundaries and next change

Python owns SQLite storage, retrieval and host operations. Eve assembles local
context and proposes tool calls, with Ollama serving inference on loopback.
Approval and host input validation are separate from the model. The desktop adapter selects Hyprland in its session and retains the KWin bridge.
Hyprland focus validates compositor-issued stable IDs and confirms the active
window after dispatch. The web console serves only the chat and readiness APIs
to the browser. Its private bridge forwards turns to Eve, which calls Ollama on
loopback. Web chat leaves desktop actions in the separately scoped CLI path.

Keep Core, Memory, Reasoning, Awareness, Actions, Guardian, Research and the
Interface as logical boundaries in this codebase. Add Vision, Voice, Connect,
Learning and Scheduler when their roadmap prerequisites pass. Use durable
state and clear permissions before splitting services or adding agents.
```text
Text / voice / desktop panel
           |
Local coordinator (Eve runtime)
           |
           +-- Local memory and document retrieval
           +-- Model router --> local model / permitted cloud context
           +-- Online tools --> selected internet services
           +-- Suggestions --> user feedback
           +-- Policy executor --> scoped desktop tools

Opt-in observer --> filtered events --> summaries --> candidate memories
Owner confirmation -------------------------------> confirmed memories
```

The offline desktop companion owns memory, capture controls, policy enforcement,
and audit records. The cloud is optional and does not own the personal database.
The exact local-model adapter and eve persistence configuration must be tested
for offline operation before selecting the production integration.

## Web conversation lifecycle

The web process owns one exclusive, private SQLite transcript store. A browser
request UUID maps to one stored user turn, and a retry replaces the failed
attempt in that same turn. A live delivery owns the only active reply slot.
Eve emits text deltas through the internal bridge, and Stop forwards cancellation
against the active Eve delivery. The web worker keeps saving progress when a
browser disconnects. A new application process marks unfinished turns as
interrupted and keeps their partial reply and original message.

Each new turn uses an isolated Eve session with bounded reference data built
from completed transcript turns. The context builder keeps recent exchanges
and ranks older excerpts by query overlap. Excerpts preserve speaker attribution
and wording. They can be incomplete, and a prior assistant reply is not evidence
of a fact or action. Personality settings use an allowlist and carry no authority.
System and approval instructions remain in the agent configuration.

Transcript files are mode 600 in an owned private directory outside the source
tree. By default normal web startup uses the XDG state directory. Temporary
testing uses a disposable lesson database and a separate transcript location.
An explicit `--conversation-dir` outside Git lets a synthetic test exercise
persistence across web process restarts. The brain mount is excluded from
conversation storage. The web runtime's volatile Eve state lives in a separate
temporary directory and is discarded after a graceful shutdown.

## Memory categories

- Owner facts: explicitly provided or confirmed; editable and attributable.
- Observations: short-lived events, separate from interpretation.
- Inferences: uncertain hypotheses with supporting evidence and expiry.
- Knowledge: indexed documents with source attribution and access scope.
- Procedures: versioned instructions verified by task outcomes.
- Episodes: task history, results, and feedback with retention limits.

Personal memory stores explicitly supplied owner facts, with correction,
local onboarding, and consistent backups. Lessons and PC inventory live in
separate tables. The foundation is not a vector
index, conversational memory, or training pipeline. Private SQLite storage is
outside the checkout; future services must enforce access control too.

Phase 3 preserves this separation: existing `Memory`, `Knowledge`, and `School`
SQLite/FTS5 components remain the initial persistence and retrieval path. The
default memory path is the existing `/mnt/burito-brain/memory` directory. It
validates filesystem UUID and type, requires the volume manifest and opens
SQLite through a pinned directory descriptor. It does not create an XDG fallback.
Explicit `BURITO_DATA_DIR` overrides remain available for isolated tests.
Memory retrieval currently builds a temporary in-memory FTS5 index per query;
it does not persist another index. Embeddings remain an evaluated extension.
The Academy regression experiment is isolated under `academy/`.

The Eve instruction bridge asks the existing Python context builder for selected
records per turn. Project, experience and Academy scopes are separately opt-in,
bounded and query-selected; Academy progress is distinct from curriculum
metadata and imported knowledge. Personal facts use a separate category allowlist
and remain off by default. Retrieved records are evidence, not instructions or
permissions. The desktop web launcher opts into the three non-personal cognitive
scopes; it does not enable personal memory or memory writes.

## Routing contract (planned)

Classify the task's tools and data needs independently of the model. Local tasks
remain local even when connected. Online tasks require actual service access.
Cloud inference requires enablement, allowed context, and remaining budget.
On failure, use a capable local model or clearly report what cannot continue.
Never pretend that queued external work has completed.

## Trust boundaries

Observation is not permission to act. Model output and retrieved web/document
content cannot grant permissions. A separate executor validates every action
against current owner-granted scopes. Credentials stay in local secret storage
or environment configuration. The GitHub repository contains code and synthetic
examples, never the owner's memory, conversations, observations, or tokens.

An optional systemd user timer now supports periodic local inventory after user
manager startup. It is separate from chat startup, screen capture, internet tools,
cloud inference, and action execution. See PC_AWARENESS.md for scope and controls.
