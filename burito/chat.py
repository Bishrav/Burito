"""Launch the prepared eve runtime; no model installation or cloud fallback."""

import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent


def chat(model, context_tokens, lesson="home.honesty", include_personal=False, include_system=True, pc_access=True):
    runtime = ROOT / "runtime"
    environment = os.environ.copy()
    candidates = sorted((ROOT / ".tools").glob("node-*/bin"), reverse=True)
    if candidates:
        environment["PATH"] = os.pathsep.join([str(candidates[0]), environment.get("PATH", "")])
    node = shutil.which("node", path=environment.get("PATH"))
    cli = runtime / "node_modules/.bin/eve"
    if node is None or not cli.exists():
        raise ValueError("Runtime is missing. In Konsole run: bash scripts/setup-runtime.sh")
    if not model.strip() or not 4096 <= context_tokens <= 131072:
        raise ValueError("Choose a local model and a server context size between 4096 and 131072 tokens")
    # Validate the selected local data before starting the model runtime.
    from .context import build_context
    build_context(lesson, include_personal, include_system=include_system)
    environment.update({
        "BURITO_MODE": "local",
        "BURITO_LOCAL_MODEL": model,
        "BURITO_CONTEXT_TOKENS": str(context_tokens),
        "BURITO_LESSON_ID": lesson,
        "BURITO_INCLUDE_PERSONAL_MEMORY": "1" if include_personal else "0",
        "BURITO_INCLUDE_SYSTEM": "1" if include_system else "0",
        "BURITO_PC_ACCESS": "1" if pc_access else "0",
        "BURITO_PROJECT_ROOT": str(ROOT),
        "BURITO_PYTHON": sys.executable,
        "EVE_TELEMETRY_DISABLED": "1",
        "EVE_TRACES_CONTENT": "off",
        "EVE_SCHEDULES_DISABLED": "1",
    })
    print(f"Starting local Burito with lesson {lesson}. No automatic cloud fallback.")
    print("Personal memory included." if include_personal else "Personal memory excluded.")
    print("Local file/application tools enabled; application launches require approval." if pc_access else "PC file/application tools disabled.")
    try:
        return subprocess.run([node, str(cli), "dev", "--no-default-extensions"], cwd=runtime, env=environment,
                              check=False).returncode
    except KeyboardInterrupt:
        return 130
