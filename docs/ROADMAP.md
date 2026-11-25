# Burito roadmap

## Current delivery order

The sequence below supersedes the historical milestones retained in this file.

0. **Recovery**. Restore source and manifests, pass integrity and required tests,
   verify local conversation and approval denial, and review the recovery diff.
1. **Ryoku desktop**. Verify local chat and wire the existing interface to Eve.
   Add a desktop adapter with Hyprland enumeration and focus state while retaining
   KWin. Test approved launches, file reads and notifications on the host.
2. **Conversation**. Add streaming, interruption, clarification, summaries and
   user-controlled tone. Measure latency and multi-turn task success.
3. **Memory**. Add attributable episodic, procedural and project records, conflict
   handling and hybrid retrieval. Evaluate retrieval, correction and deletion.
4. **Voice and vision**. Benchmark local components and verify opt-in capture and
   visible controls before enabling hands-free or screen features.
5. **Companions**. Verify pairing, revocation, encrypted transport and locked-PC
   non-GUI tasks. Build Flutter companions and test the wake path separately.
6. **Workflows**. Require durable status, evidence, cancellation, retry and recovery.
7. **Specialists**. Add agents only after measured improvement under central policy.
8. **Learning**. Evaluate approved feedback, memory and prompt changes. Fine-tuning
   requires separately authorized data, evaluation and rollback.

See [vision](VISION.md), [security](SECURITY.md), and [innovation](INNOVATION.md).

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

Current progress: an optional CLI-only online research tool is implemented as
an explicitly enabled, per-query approval-gated capability. It sends only the
approved query. Live provider calls, approval denial, timeout, budget limits,
and provider-failure behavior still need verification; this does not complete
milestone 2. See `docs/ONLINE_RESEARCH.md`.

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
and terminal procedures. The first optional desktop-context slice is one-shot
local OCR via KDE Spectacle and Tesseract, enabled per chat and approved per
capture. Add tested accessibility/app-specific integrations for richer visual
context and UI control next. Enforce policy in the executor, outside prompts.
Use minimum privileges, scoped folders, argument validation, timeouts,
previews, meaningful approvals, outcome checks, and recoverable changes.
External content is task data, never authority to override permissions.

Exit: each tool has success/failure verification, audit records, and recovery
instructions; hostile documents cannot trigger unauthorized actions.

Current progress: the optional browser controls can read page text, locate
phrases in captured text, navigate, click, fill a non-password field, scroll,
and move back/forward with per-action approval. KWin window selection and
focus are separate, on-demand tools. A narrow AT-SPI insertion path can place
owner-approved text at the caret in an accessible native text field after
revalidating the exact active KWin window. It does not change the system
clipboard. A write-only browser clipboard tool is also available behind an
optional extension permission and per-copy approval; it cannot read clipboard
contents. Native insertion after copy is separate and is not a simulated Ctrl+V.
Browser-to-native-app use still requires owner-run checks; this does not
complete milestone 7 or authorize general computer control.

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
