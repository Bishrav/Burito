# Cognitive architecture and capability map

These are logical responsibilities in the current Python, Eve and SQLite
application. Add a separate process only for an observed isolation or runtime need.

| Responsibility | Reuse and next dependency |
| --- | --- |
| Core and Interface | Eve agent, Python CLI, local web bridge and Brave console. Stabilize live turns, context, independent cancellation and restoration in Phase 2. |
| Reasoning and Research | Existing bounded context and opt-in online research. Begin with explicit goals, alternatives, evidence and verification. Evaluate hierarchical task plans before automated execution. |
| Memory and Brain | Keep Phase 2 transcripts separate from personal memory. Extend existing schemas and FTS5 retrieval in Phase 3. Verify volume identity, migrations and independent restore before moving durable data. |
| Awareness, Vision and Voice | Reuse inventory, Hyprland/KWin adapters, opt-in activity and scoped OCR. Later benchmark local speech and multimodal perception with visible owner consent. |
| Actions and Guardian | Reuse the scoped file reader, typed browser and desktop executors, approval rules and audit. Add capabilities only with threat cases, least privilege, bounded input and evidence of execution. |
| Academy and Learning | Reuse the lesson catalog, provenance, feedback and suggestions. Compare deterministic and statistical baselines before introducing trained models. |
| Connect and Scheduler | Pair devices securely before remote control. Use durable task state and explicit approval across restart, then evaluate specialist orchestration only when a single coordinator falls short. |

Working memory holds current context and task state. Semantic memory records
verified concepts and facts. Episodic memory records consented events and
experiences. Procedural memory contains validated workflows. Project and
preference memory explain decisions and owner choices. Error memory ties a
failure to evidence and recovery. Prospective memory records commitments and
scheduled work. Operational history tracks versioned development and execution.
For material records keep source, category, timestamp, confidence, verification,
corrections and retention. Separate owner statements, observations, inferences,
research claims and verified facts. Support correction, conflict resolution,
deletion and export before relying on persistent retrieval.

Current Phase 3 retrieval reuses the owner-fact table and a temporary FTS5
index for each opted-in query. Schema v2 adds categories, nullable confidence,
verification provenance, owner-defined claim keys, retention label, timestamps
and active/superseded state. Corrections save prior values; deletion cascades to
revision and conflict records. Explicit claim keys detect competing values for
owner review. The CLI exposes history and conflict review. This does not infer
arbitrary natural-language contradictions, implement expiry, or provide general
memory consolidation. Matching records retain their IDs and source labels; an
unresolved conflict is passed into context as data, never as an instruction.

## Research hypotheses and evaluation

Use ACT-R and Soar to study activation, declarative versus procedural stores,
and learning from impasses. Test simple recency and relevance scoring first.
Use global workspace theory as inspiration for bounded attention and shared task
state, without claims about consciousness. Use beliefs, desires and intentions
to separate observations from objectives and authorized commitments. Compare
hierarchical task networks to a linear checklist on synthetic recovery tasks.
Evaluate neuro-symbolic representations, knowledge graphs, causal and probabilistic
reasoning, and world models only on tasks where the existing baseline fails.
Use computational neuroscience as a source of testable hypotheses. Keep
continual learning and safe reinforcement learning inside isolated evaluations.

Freeze evaluation inputs and report success, false claims, clarification quality,
context and memory recall, safety denials, latency, tokens/s, CPU/GPU/VRAM/RAM
and storage. Add blinded owner feedback where appropriate. Prefer one simple
planner and verification step before specialists. Record fallbacks, retry budgets
and blocked outcomes; a failed attempt never becomes completion evidence.

Primary research entry points include [ACT-R](https://act-r.psy.cmu.edu/),
[Soar](https://soar.eecs.umich.edu/), and [Baars and Franklin on global workspace theory](https://pubmed.ncbi.nlm.nih.gov/17998071/).

## Computer and terminal intelligence

Map browser navigation, tabs, webpage understanding and authorized forms or
downloads to the existing Brave integration. Keep webpages, file contents and
tool output untrusted. A page cannot grant authority. Verify the final state,
and require approval for outbound messages, purchases and account changes.
Extend desktop windows to workspaces, accessibility, approved mouse and
keyboard input, clipboard, screen, notifications and audio through provider
adapters. Keep Hyprland and KWin behavior separately testable.

The unified capability registry should also describe scoped file writes and
directory changes, Git/build environments, packages, services, network and
hardware diagnostics, and supported external APIs. The current terminal
foundation is structured local diagnostics and subprocess-based adapters.
General model-controlled shell work is not implemented. Start with typed,
read-only diagnostics for Bash/Zsh, Arch, systemd, processes, permissions,
filesystems, networks, hardware, Git, Python, Node, Docker and build tools.
Each consequential command needs structured arguments or an exact command,
working directory, intent, permissions, risk, timeout, output limits, exit
status, verification and a recovery procedure where possible. Default to
unprivileged execution. Promote only narrow, tested low-risk workflows to
standing authorization. Keep execution separate from inference and approval.
