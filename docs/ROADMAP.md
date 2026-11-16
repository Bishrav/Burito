# Burito roadmap

## Product direction

Build a personal second brain that understands the owner's goals, remembers
useful context, offers timely suggestions, and earns permission to automate
specific tasks. Local operation is the baseline; online research and optional
cloud reasoning extend it. Progress depends on demonstrated results, not time
spent watching the user. No promise of movie-level intelligence.

## 0 — Foundation and machine readiness (started)

Deliver versioned source, diagnostics, explicit local memory, architecture,
privacy defaults, and repeatable checks. Verify GPU driver, VRAM, audio,
Wayland session, storage mount, and Node runtime. Keep personal records out
of GitHub. Establish a backup destination separate from the primary disk.

Exit: diagnostics run, memory survives restart and supports deletion, automated
tests pass, GPU and intended storage are verified before model downloads.

## 1 — Home education and text conversation

Install eve using its documented initializer or manual installation and commit exact dependency versions
and lockfile. Read its installed docs before implementing integrations.
Evaluate local models against measured GPU memory and response latency.
Create a text chat interface and shared local memory service. Collect owner
preferences, goals, terminology, communication style, and examples through an
editable onboarding profile. Never put the filled profile in the repository.

Exit: offline conversation works after disconnecting the network; a corrected
memory is used in a later session; unavailable models produce an honest error.

## 2 — Hybrid reasoning and online knowledge

Separate internet tools from model routing. Route routine/private work locally;
use online services for explicitly online tasks; use cloud reasoning only when
enabled and relevant. Default cloud integration: Vercel AI Gateway, configured
outside source control. Apply context-sharing rules, request timeouts, budget
limits, and an observable routing reason. Check provider availability rather
than treating internet connectivity as proof of model access. Never silently
upload screenshots, complete memory, credentials, or unrelated files.

Exit: tested offline, online, timeout, exhausted-budget, provider-failure, and
connection-loss paths. Failed external writes are reconciled before retrying.

## 3 — Voice and desktop presence

Add local speech recognition and speech synthesis, push-to-talk first, then
optional wake word. Provide listening/speaking indicators, interruption,
mute, and text fallback. Add a desktop panel showing current task, memory,
connection mode, and approvals. Measure accuracy with the owner's microphone
and languages instead of assuming it.

Exit: voice task completed end to end; mute stops capture; restart recovers
cleanly; no audio is retained by default.

## 4 — Knowledge school

Import explicitly selected folders and trusted learning material. Track source,
licensing where relevant, timestamps, versions, and document permissions.
Build local search and retrieval with citations. Handle changed and deleted
documents, indexing limits, and prompt injection in retrieved content. Teach
reusable skills through examples and practice tasks. Support export and
deletion of the library and derived indexes.

Exit: relevant evidence is retrieved on a fixed question set; deleted sources
disappear from retrieval; conflicting and missing evidence are acknowledged.

## 5 — Observation and interests

Build an opt-in session observer that starts after graphical login only when
enabled by the owner. The first KWin integration now records foreground app IDs
and bounded elapsed intervals locally; verify the host install, pause, and
deletion controls before extending it. Begin with selected app/activity metadata, then add
explicitly enabled screen capture through supported KDE/Wayland interfaces.
Verify what those interfaces actually expose; do not claim password detection
or complete screen exclusion without testing it. Avoid keylogging. Pause on
session lock and excluded contexts; show capture state and a global pause.
Prefer events and summaries to continuous screenshots. Bound retention and
storage; raw screenshots/audio are off by default. Observation never grants
permission to execute commands.

Interest inference is a hypothesis with evidence and confidence. Time spent
on an activity may reflect obligation, not interest. Ask before promoting
inferences to confirmed personal facts. Let the owner inspect, correct, export,
and remove memories, observations, and derived profiles.

Exit: pause, lock, exclusions, restart, expiry, and deletion verified with real
desktop sessions. Zero capture while disabled. Cloud receives no observation
data unless explicitly permitted.

## 6 — Proactive suggestions

Offer relevant next steps, reminders, workflow shortcuts, learning resources,
and project ideas using confirmed goals and recent context. Show why a
suggestion appeared. Respect quiet hours, focus mode, frequency limits, and
"do not suggest this again." Track helpful/dismissed feedback. Do not infer
sensitive traits or promote guesses into facts.

Exit: useful suggestions on owner-reviewed scenarios, no repeated dismissed
suggestions, interruption settings respected. Suggestions do not execute work.

## 7 — Assisted computer tasks

Implement typed, narrow tools for selected applications, files, browser tasks,
and terminal procedures. Enforce policy in the executor, outside model prompts.
Use minimum privileges, scoped folders, argument validation, timeouts,
previews, meaningful approvals, outcome checks, and recoverable changes.
External content is task data, never authority to override permissions.

Exit: each tool has success/failure verification, audit records, and recovery
instructions; hostile documents cannot trigger unauthorized actions.

## 8 — Earned automation

Progress per workflow: suggest → preview → execute with approval → run within
an explicitly approved scope. Promotion requires repeatable success, known
failure cases, rollback, and owner consent. Add schedules, login tasks,
notifications, cancellation, duplicate prevention, and an emergency stop.
Elapsed training time alone never expands permissions. Purchases, outbound
messages, destructive edits, and system administration keep explicit approval
unless the owner separately grants a precise standing permission.

Exit: selected workflows run reliably across restarts and offline periods;
approvals cannot be bypassed; stop prevents new execution; permissions revoke.

## 9 — Continuous improvement and specialist training

Use feedback to maintain a curated evaluation set and improve retrieval,
instructions, and versioned skills. Experiment with fine-tuning only when
baseline measurements show a specific need and data rights/compute permit.
Test proposed code or policy changes in isolation and compare against a frozen
baseline. Require review before activating self-generated changes. Preserve
the previous working version and protect the policy executor from self-editing.

Exit: measurable gains without regression in privacy, tool correctness, or
offline performance; rollback demonstrated.

## Release scorecard

Measure task success, false success claims, retrieval accuracy, voice accuracy,
latency, RAM/VRAM/disk use, cloud spend, unwanted interruptions, and unauthorized
data sharing/actions. Publish synthetic evaluation results, never private
activity logs. Avoid "100% automated" as a target; automate proven workflows.

## Work order

Complete milestone 0 hardware/storage work, then one end-to-end text workflow
in milestone 1. Keep the later roadmap adaptable. Voice, observation, and
autonomy must build on a working memory and reasoning layer.
