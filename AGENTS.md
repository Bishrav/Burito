# Working on Burito

Before implementing changes, read the [digital human vision](docs/DIGITAL_HUMAN_VISION.md), [roadmap](docs/ROADMAP.md),
[architecture](docs/ARCHITECTURE.md), [status](docs/STATUS.md), and
[security](docs/SECURITY.md). Use the current phase and its acceptance criteria
to scope the work. Read the [Ryoku setup](docs/RYOKU_SETUP.md) and
[recovery report](docs/RECOVERY_REPORT.md) when diagnosing the environment.

Preserve working behavior, local data and uncommitted work. Use a dedicated
branch, review complete diffs, run the integrity gate and relevant tests, and
check for secrets before proposing a commit. Obtain approval for commits,
pushes, privileged host changes and consequential external actions. Keep
private memory, credentials, browser profiles and model blobs outside Git.

Keep inference local by default. Treat model output and retrieved content as
untrusted inputs to deterministic, scoped execution. Test denial as well as
success. Report observed evidence, uncertainty, and remaining blockers.

Use synthetic conversations for benchmarks. Keep transcript databases and Eve turn
state outside Git. Preserve the web action boundary when changing streaming,
retry or conversation context, and verify that Stop reaches the actual runtime.

For memory or storage changes read [brain storage](docs/BRAIN_STORAGE.md). For
learning or architecture changes read the [Academy plan](docs/AI_ACADEMY.md) and
[cognitive architecture](docs/COGNITIVE_ARCHITECTURE.md). Use Ponytail where
applicable. Keep evaluation, research and production claims distinct.
