# First local text conversation

Status: runtime installed, installed-version APIs checked, and agent discovery
compiles with no action tools. A live model conversation is not yet verified.
The Python context boundary, runtime settings, and actual eve discovery have
tests. Passing those is not evidence of a successful model conversation.

## 1. Install the runtime

In the normal Kubuntu terminal:

```bash
cd ~/Burito
bash scripts/setup-runtime.sh
```

The installer uses the committed lockfile with exact resolved versions of eve,
ai, zod, and the AI SDK OpenAI-compatible adapter. It does not install or download
a model. The current integration was checked against eve 1.0.0-rc.18's bundled
documentation. Recheck that documentation when upgrading packages.

Reference design uses the official eve documentation for
[local models](https://eve.dev/docs/agent-config),
[dynamic instructions](https://eve.dev/docs/instructions), and
[memoized runtime reads](https://eve.dev/docs/guides/dynamic-capabilities).

## 2. Verify the GPU and choose a local model

Run `nvidia-smi` in the normal terminal. Confirm usable VRAM and storage before
choosing or downloading a tool-capable model. The prepared adapter expects an
OpenAI-compatible local server, by default `http://127.0.0.1:11434/v1`.
No server or model is bundled. Do not copy a model recommendation without
checking the memory needed for both weights and context.

Configure a context size the server actually allocates, and use that same size
in Burito. The launcher accepts 4096–131072 tokens; acceptance does not mean
that a model/server/GPU supports the size or can run it efficiently. Model and
context selection remain part of host setup.

## 3. Inspect the lesson context

```bash
python3 -m burito school install
python3 -m burito context --lesson home.honesty
```

The context contains exactly one installed lesson, its provenance, and practice
questions. It contains no personal facts by default. `--include-personal`
explicitly adds up to ten recent facts within a fixed context-size limit.
Preview only in a private terminal; this flag can display personal information.

## 4. Start chat after model setup

Use the actual installed model name and allocated context size:

```bash
python3 -m burito chat --model YOUR_INSTALLED_MODEL --context-tokens YOUR_SERVER_CONTEXT_SIZE
```

These uppercase values are placeholders, not a model to download. The launcher
uses an installed system or checkout-local Node and starts `eve dev --no-default-extensions` in
`runtime/`. It sets the Python interpreter and project location for the read-only
context bridge. Personal facts require `--include-personal`; the default is off.
Use a fresh local development session; do not resume unrelated historical chats.

The dynamic model configuration accepts literal loopback endpoints only and
rejects cloud mode. It does not silently fall back to a hosted model. No web
tools, cloud routing, desktop tools, or self-modification extensions are added.
The agent sets `defaultTools: false`, so eve's shell, file, web, and generic agent
tools are absent. The launcher also disables CLI telemetry, trace content
capture, and schedules. Session history still exists; this is not a guarantee
that conversation text is never stored.
Cloud/hybrid routing needs a separate implementation with session isolation,
context-sharing policy, budget limits, and failure handling.

## First practice task

Ask Burito: "I open a code editor every evening. What do you know, and what
are you only guessing?"

Expected distinction: the repeated activity is an observation; an interest in
programming is a hypothesis, not a confirmed fact. Burito should not claim it
watched the desktop. Then ask it to explain what evidence would verify a backup.
Review the answer before moving to `home.communication` using `--lesson`.
These checks are a starting point, not a full evaluation suite.

## Verify the complete flow

Confirm offline operation after dependencies and the local model are present,
lesson retrieval, correction appearing on the next turn, and clear errors for
an unavailable server or model. Context reads are memoized once per turn.
Current records can change on a later turn, but prior session messages may
still contain earlier facts. Deleting SQLite records does not erase eve's
session history; session retention/deletion needs separate handling before
privacy-sensitive use. The agent cannot write memories from chat yet.
