# First local text conversation

Status: runtime installed, installed-version APIs checked, and agent discovery
compiles with only the explicitly authored PC tools. The owner completed the first local model exchange.
Its response showed a source-attribution error; a revised prompt/lesson awaits retest.
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

The owner verified a working RTX 5070 with about 12 GB VRAM, including about
10.5 GiB free in the supplied snapshot. Start conservatively with
[`qwen3:8b`](https://ollama.com/library/qwen3:8b): its listed quantized download
is 5.2 GB. Runtime memory also includes context/cache and other overhead; model
download size is not total VRAM usage. Start with an 8192-token context and
measure actual placement and responsiveness. This is an initial compatibility
choice, not a benchmark or a claim that it is the strongest available model.

Install Ollama in the normal terminal using its
[official Linux instructions](https://docs.ollama.com/linux):

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama --version
```

The official installer installs a system service and may ask for sudo. This is
separate from Burito's user-local Node installer. Verify installation first;
the next step is the model pull and context configuration. No model is pulled
by these two commands. The restricted development session cannot perform this
download on the owner's behalf.

The prepared adapter expects an
OpenAI-compatible local server, by default `http://127.0.0.1:11434/v1`.
No server or model is bundled. Do not copy a model recommendation without
checking the memory needed for both weights and context.

After `ollama pull qwen3:8b` completes, create a named local configuration:

```bash
cd ~/Burito
ollama create burito-local:8b -f config/ollama/Modelfile
ollama show --modelfile burito-local:8b
```

The committed Modelfile sets `num_ctx 8192`; the corresponding Burito launcher
argument must match. This is a local model configuration, not fine-tuning. It
references the downloaded base weights. No personality or personal memories
are baked into that model; they remain in Burito's application/context layer.
Reference: [Ollama Modelfile documentation](https://docs.ollama.com/modelfile).

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
python3 -m burito chat --model burito-local:8b --context-tokens 8192
```

This command assumes the named local configuration above was created. The launcher
uses an installed system or checkout-local Node and starts `eve dev --no-default-extensions` in
`runtime/`. It sets the Python interpreter and project location for the read-only
context bridge. Personal facts require `--include-personal`; the default is off.
Use a fresh local development session; do not resume unrelated historical chats.

The dynamic model configuration accepts literal loopback endpoints only and
rejects cloud mode. It does not silently fall back to a hosted model. No web
tools, cloud routing, or self-modification extensions are added. Authored file,
application-discovery, and approved launch tools are described in PC_ACCESS.md.
The agent sets `defaultTools: false`, so eve's built-in shell, file, web, and
generic agent tools are absent. The launcher also disables CLI telemetry, trace content
capture, and schedules. Session history still exists; this is not a guarantee
that conversation text is never stored.
Cloud/hybrid routing needs a separate implementation with session isolation,
context-sharing policy, budget limits, and failure handling.

## First practice task

Ask Burito: "I open a code editor every evening. What do you know, and what
are you only guessing?"

Expected distinction: the user reported the repeated activity; Burito did not
directly observe it. An interest in programming is a hypothesis, not a confirmed
fact. Burito should say 'you told me', avoid claiming independent verification,
and avoid unrelated task-completion disclaimers. Then ask it to explain what
evidence would verify a backup.
Review the answer before moving to `home.communication` using `--lesson`.
These checks are a starting point, not a full evaluation suite.

The first owner-tested response distinguished guesses but incorrectly described
the user report as a direct observation. It took 48 seconds for that exchange;
this single result does not establish warm-model speed or GPU placement.
The lesson was revised to version 2 and the standing instructions strengthened.
Reinstall the lesson with `python3 -m burito school install`, then start a fresh
chat with the same command above and repeat the question. Do not record the
revision as successful until the revised behavior is observed.

## Verify the complete flow

Confirm offline operation after dependencies and the local model are present,
lesson retrieval, correction appearing on the next turn, and clear errors for
an unavailable server or model. Context reads are memoized once per turn.
Current records can change on a later turn, but prior session messages may
still contain earlier facts. Deleting SQLite records does not erase eve's
session history; session retention/deletion needs separate handling before
privacy-sensitive use. The agent cannot write memories from chat yet.
