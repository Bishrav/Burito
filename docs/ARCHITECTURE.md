# Architecture

```text
Text / voice / desktop panel
           |
Local coordinator (eve runtime, planned)
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

The foundation implements only explicitly supplied owner facts, with correction,
local onboarding, and consistent backups. It is not a vector
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

No automatic startup is installed in this milestone. Startup, capture, internet
tools, cloud inference, and action execution are separate capabilities.
