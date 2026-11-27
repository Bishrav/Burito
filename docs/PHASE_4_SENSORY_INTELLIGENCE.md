# Phase 4: sensory intelligence

## Scope and starting point

Phase 3 was integrated into `main` at `6dc83b685498c55d2ce62b8bb6b8f0c38a6247f`.
This branch starts from that commit. Phase 4 adds opt-in local audio and visual
input while retaining Qwen3 8B as the text conversation baseline. It does not
claim human perception, consciousness, or continuous awareness.

The repository already provides loopback-only Eve/Ollama chat, bounded
conversation context, an optional approval-gated one-shot screen OCR flow,
Hyprland/KWin window adapters, and explicit project/experience/Academy context
scopes. Reuse these boundaries. Screen capture remains a separate capability
from observation and from permission to act.

## Hardware and model constraints

Host evidence in the project records: i9-14900K, 32 GB RAM, RTX 5070 with
12 GB VRAM, and Qwen3 8B Q4_K_M using about 6.3 GB at 8K context. That leaves
limited VRAM for a second model and transient buffers. Do not assume ASR, TTS,
vision and chat can all keep GPU models loaded together. Start audio on CPU or
with a small independently measured model; schedule visual inference so it
does not evict or destabilize the conversational baseline. Capture the actual
VRAM, RAM, CPU and latency measurements before selecting concurrency policy.

Phase 4A now has a CPU-only `whisper.cpp` build and one multilingual base model
on the verified brain. Reproduce it with `scripts/setup-local-asr.sh`; the
binary/build environment stays under ignored `.tools`, and the model stays at
`/mnt/burito-brain/models/audio/ggml-base.bin`. The setup checks the brain UUID,
filesystem and read/write state, pins the upstream source revision, refuses to
replace an existing source tree or model, and verifies upstream SHA-1 plus the
observed SHA-256. No system package, driver or model-serving runtime changed.
Ollama is recorded as 0.40.18; check its actual image API/model compatibility before
selecting a vision model. Current Ollama library documentation identifies
Qwen2.5-VL 3B as an image-capable candidate and lists an Ollama 0.7.0 minimum.
Because the recorded installed version uses a different-looking version
sequence, verify the actual executable's version semantics and image endpoint
before assuming compatibility. Treat it as a benchmark candidate, not a
ready-to-run dependency. Do not upgrade Ollama solely to test it without first
reviewing runtime compatibility and rollback.

## Candidate components to benchmark

| Capability | Initial candidate | Reason and gate |
| --- | --- | --- |
| Speech recognition | `whisper.cpp` CPU build, small/base multilingual model | C/C++ implementation supports CPU, quantization and CUDA. CPU baseline avoids competing with Qwen's VRAM; measure real-time factor, word error rate, memory and first partial result. Only build CUDA if the installed toolkit/compiler compatibility is verified. |
| Alternative ASR | `faster-whisper` in a dedicated uv environment | CTranslate2 may offer good GPU performance, but current upstream requirements call for CUDA 12/cuBLAS and cuDNN 9. Verify the host runtime and Python wheels first; do not alter the working NVIDIA driver stack. |
| Voice activity detection | Silero VAD ONNX CPU path | Small streaming VAD with CPU/ONNX option; benchmark endpoint delay and false starts against silence/noise fixtures. Avoid pulling a full PyTorch audio stack just for VAD. |
| Text to speech | Piper (`piper-tts`) with one license-reviewed local voice | Local inference and a relatively simple interface. The currently maintained OHF-Voice project is GPL-3.0-or-later; each voice has its own license and provenance, so review both before distribution or committing any voice artifact. Measure time to first audio, real-time factor and intelligibility. |
| Image understanding | Existing OCR first; separately benchmark a small VLM such as Qwen2.5-VL 3B | OCR is already implemented. Compare VLM against OCR on a fixed local synthetic/owner-approved image set. Keep VLM weights on the brain only after storage and license checks; load on demand and measure peak VRAM. |

Whisper.cpp upstream documents CPU inference, quantization and NVIDIA CUDA
support; faster-whisper documents CUDA/cuDNN requirements; Silero VAD documents
an ONNX CPU installation path; Piper's maintained upstream documents its
engine and voice licensing. These are candidate properties, not measurements
on this host. Source links: [whisper.cpp](https://github.com/ggml-org/whisper.cpp),
[faster-whisper](https://github.com/SYSTRAN/faster-whisper),
[Silero VAD](https://github.com/snakers4/silero-vad),
[Piper engine](https://github.com/OHF-Voice/piper1-gpl),
[Piper voice licensing](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/LICENSING.md),
[Ollama Qwen2.5-VL](https://ollama.com/library/qwen2.5vl).

## Implementation sequence and gates

### 4.1 Push-to-talk audio vertical slice

1. Add an audio provider interface behind the existing runtime boundaries; use
   a single provider process/library and a private temporary buffer.
2. Implement explicit press/release capture with a persistent visible
   listening indicator, a hard maximum duration, mute, cancel and text fallback.
   Do not start a background microphone listener or wake-word detector.
3. Transcribe a short, owner-consented fixture locally. No raw audio is retained
   by default. Show the transcript for confirmation before sending when ASR
   confidence is low or speech is ambiguous.
4. Add local TTS after text response streaming is stable. Stream text in safe
   sentence-sized chunks; Stop must cancel generation, queued synthesis and
   active playback. Do not speak tool/approval payloads as if completed.

Acceptance: capture is off by default; deny/mute means zero audio reads; the
indicator matches actual capture state; no audio files or transcripts enter
Git/logs; user can interrupt and Stop clears queued audio; synthetic tests cover
device loss, permission denial and model/runtime failures.

Implementation checkpoint: the web console has a user-activated Record/Stop
control and a bounded same-origin `/api/transcribe` route. The transcript stays
editable and is submitted only through the existing text turn. Browser capture
is capped at 15 seconds, request bodies at 8 MiB, and decoded audio at 15
seconds/1 MiB. FFmpeg and Whisper use fixed argument vectors and timeouts;
temporary audio/transcript files live in a 0700 directory and are removed at
request completion. Camera access is denied by policy (`video: false`).

One 11-second English fixture included in the upstream source checkout matched
its published reference text exactly (WER/CER 0.0 on one clip only). The local
CPU route took 0.649 seconds (RTF 0.059), used 2.04 child CPU seconds and peaked
at 282 MiB child RSS. This is a runtime smoke, not an owner-speech accuracy
estimate; the fixture was not committed. An earlier PipeWire snapshot exposed
no physical microphone source although ALSA listed an ALC897 capture device.
The owner has since verified browser capture and transcription in Brave using
AirPods. The working PipeWire default capture source is
`bluez_input.98:1C:A2:D6:65:85`, and Brave uses **System default** for its
microphone. The owner also verified cancellation, the 15-second recording cap,
a clear denied-permission message, and acceptable transcription of
representative English recordings. Sample count, accent/noise conditions, and
quantitative accuracy were not measured; Nepali/Hindi/code-switch accuracy
remains unverified.
`scripts/benchmark_local_asr.py` accepts an owner-prepared TSV of
WAV/reference pairs and reports aggregate metrics without printing transcripts.

### 4.2 Turn taking and low-latency streaming

Use VAD to detect speech boundaries, not to authorize action. Keep a bounded
ring buffer in memory; discard it after a turn. Maintain separate states for
listening, transcribing, thinking, speaking, interrupted and error. New speech
during playback cancels playback and the active response before creating a new
turn. Avoid duplicate submission with the Phase 2 idempotency/request identity.

Acceptance: measure end-of-utterance delay, ASR partial/final delay, time to
first spoken audio, interruption propagation and recovery after device loss.
False activation and missed interruption rates must be evaluated over a
consented fixed fixture set.

### 4.3 One-shot visual context

Keep the existing approval-gated OCR path as the first supported screen
provider. Add image interpretation only through an explicit user-selected
image or approved one-shot screen capture. Display a visible capture state,
name the target screen/window where possible, and provide a global pause and
exclusion controls. Do not persist screenshots by default. OCR text and model
descriptions remain untrusted data and cannot change permissions or execute
actions. Do not enable continuous screen observation in this milestone.

Acceptance: denial causes no capture; wrong/missing target fails closed;
screen lock, excluded app, capture cancellation and model failure are safe;
synthetic prompt-injection text in images cannot alter policy; image bytes are
removed after the request unless the owner explicitly saves them.

### 4.4 Sensory context and memory

Represent a sensory result as a short-lived observation with modality, capture
time, user authorization, source device/window, processing model/version,
confidence and expiry. Pass only the observation needed for the current turn.
Do not convert audio, transcript, OCR or visual inferences into durable memory
automatically. Persistent memory creation remains a separate explicit owner
action with provenance and correction/deletion semantics from Phase 3.

Acceptance: expired observations are not reused; one conversation cannot see
another's sensory context; personal memory opt-out remains effective; deletion
removes derived context from ordinary retrieval; model claims are separated from
directly observed text or audio evidence.

### 4.5 Multimodal evaluation

Freeze a small synthetic/owner-approved set and report per capability:

- ASR word error rate and task-relevant entity accuracy by language/noise case.
- VAD false starts, missed speech and end-point latency.
- TTS time to first audio, real-time factor and owner-rated intelligibility.
- End-to-end response latency and interruption success rate.
- OCR/VLM grounding accuracy and unsupported-claim rate.
- Peak CPU, RAM, VRAM, model load time, model storage and thermal behavior.
- Denials for microphone/screen permissions, prompt injection and retention.

Use at least one deterministic baseline and compare each candidate on the same
fixtures. Do not infer language, accent or voice preference: select these with
the owner before a representative ASR/TTS evaluation. Report sample size and
limitations; synthetic accuracy is not a substitute for owner-approved real
speech evaluation.

## Permissions and data handling

- Microphone, camera and screen access are disabled by default and are
  separately scoped; permission to hear does not grant permission to capture a
  screen or execute an action.
- Provide visible active state, immediate mute/pause, cancel and an emergency
  stop. Never create covert or login-screen capture.
- Bind audio device access to the logged-in desktop session. Use supported
  PipeWire/portal interfaces and avoid broad device permissions.
- Keep processing local and services on loopback. No sensory data is sent to a
  cloud provider unless a later, separately approved data-sharing design allows
  the exact modality and content.
- Store no raw audio or images by default. Bound buffers and request sizes;
  redact diagnostics and never log raw sensory payloads.
- Treat transcripts, OCR, image captions, model output and embedded instructions
  as untrusted data. Deterministic executors retain all existing approval and
  scope checks.
- The Phase 4A CPU-only whisper.cpp build and one 142 MiB base model are now
  installed in the isolated build area and verified brain storage. The initial
  host audit preceded both. Future dependencies and model downloads still need
  an explicit compatibility, size, license, storage and resource review; avoid
  changing system packages or configuration when an isolated option suffices.

## Hardware-aware first experiment

The first implementation should be push-to-talk transcription through one
local provider, with CPU inference as the safe concurrency baseline. Compare
small/base Whisper variants on a short opt-in fixture and the same local device
path. If accuracy or latency misses the agreed goal, evaluate a CUDA build or
faster-whisper in isolation after checking CUDA/cuDNN compatibility. Add VAD
next, then TTS. Keep VLM evaluation last and on-demand so it cannot surprise the
Qwen chat baseline with VRAM contention. No production model, driver or global
Python environment changes are part of this plan.
