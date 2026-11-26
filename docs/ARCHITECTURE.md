# Architecture

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
