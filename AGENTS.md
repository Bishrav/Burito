# Working on Burito

Before implementing changes, read [roadmap](docs/ROADMAP.md),
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
