"""Launch the prepared eve runtime; no model installation or cloud fallback."""

import os
from pathlib import Path
import shutil
import subprocess
import sys

from .runtime_lock import acquire_runtime_lock


ROOT = Path(__file__).resolve().parent.parent


def chat(model, context_tokens, lesson="home.honesty", include_personal=False, include_system=True,
         pc_access=True, include_activity=False, activity_only=False, include_feedback=False,
         include_project=False, include_suggestions=False, enable_online=False,
         enable_screen_read=False, enable_desktop_control=False):
    if activity_only:
        if enable_online:
            raise ValueError("Online research cannot be enabled in activity-only chats")
        include_personal = False
        include_system = False
        include_activity = True
        pc_access = False
        enable_screen_read = False
        enable_desktop_control = False
        include_feedback = False
        include_project = False
        include_suggestions = False
    runtime = ROOT / "runtime"
    environment = os.environ.copy()
    # Never pass inherited gateway credentials to the local agent unless this
    # chat explicitly enables the separately approved research tool.
    gateway_key = environment.pop("AI_GATEWAY_API_KEY", None)
    gateway_model = environment.pop("BURITO_GATEWAY_MODEL", None)
    environment.pop("BURITO_ONLINE_ENABLED", None)
    if enable_online:
        if not gateway_key or not gateway_model:
            raise ValueError(
                "Online research needs AI_GATEWAY_API_KEY and BURITO_GATEWAY_MODEL in this terminal"
            )
        if "/" not in gateway_model or len(gateway_model) > 160:
            raise ValueError("BURITO_GATEWAY_MODEL must be a provider/model ID, such as openai/gpt-5.4-nano")
        environment["AI_GATEWAY_API_KEY"] = gateway_key
        environment["BURITO_GATEWAY_MODEL"] = gateway_model
        environment["BURITO_ONLINE_ENABLED"] = "1"
    # eve assigns these per development process. Inheriting another process's
    # route or transport token can send queue deliveries to the wrong host.
    for name in ("WORKFLOW_LOCAL_BASE_URL", "EVE_DEV_WORKFLOW_TRANSPORT_SECRET",
                 "EVE_DEV_WORKER_APP_ROOT"):
        environment.pop(name, None)
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
    build_context(lesson, include_personal, include_system=include_system,
                  include_activity=include_activity, activity_only=activity_only,
                  include_feedback=include_feedback, include_project=include_project,
                  include_suggestions=include_suggestions)
    environment.update({
        "BURITO_MODE": "local",
        "BURITO_LOCAL_MODEL": model,
        "BURITO_CONTEXT_TOKENS": str(context_tokens),
        "BURITO_LESSON_ID": lesson,
        "BURITO_INCLUDE_PERSONAL_MEMORY": "1" if include_personal else "0",
        "BURITO_INCLUDE_SYSTEM": "1" if include_system else "0",
        "BURITO_INCLUDE_ACTIVITY": "1" if include_activity else "0",
        "BURITO_INCLUDE_FEEDBACK": "1" if include_feedback else "0",
        "BURITO_INCLUDE_PROJECT": "1" if include_project else "0",
        "BURITO_INCLUDE_SUGGESTIONS": "1" if include_suggestions else "0",
        "BURITO_GLOSSARY_WRITES": "1" if include_personal else "0",
        "BURITO_MEMORY_WRITES": "1" if include_personal else "0",
        "BURITO_PC_ACCESS": "1" if pc_access else "0",
        "BURITO_SCREEN_READ": "1" if pc_access and enable_screen_read else "0",
        "BURITO_DESKTOP_CONTROL": "1" if pc_access and enable_desktop_control else "0",
        "BURITO_PROJECT_ROOT": str(ROOT),
        "BURITO_PYTHON": sys.executable,
        "EVE_TELEMETRY_DISABLED": "1",
        "EVE_TRACES_CONTENT": "off",
        "EVE_SCHEDULES_DISABLED": "1",
    })
    print(f"Starting local Burito with lesson {lesson}. No automatic cloud fallback.")
    print("Personal memory included." if include_personal else "Personal memory excluded.")
    print("Private glossary and memory corrections available; writes require approval." if include_personal else "Private glossary and memory writes excluded.")
    print("Local activity summary included for this chat." if include_activity else "Activity summary excluded.")
    print("Owner feedback included for this chat." if include_feedback else "Owner feedback excluded.")
    print("Verified Burito project context included." if include_project else "Project context excluded.")
    print("Owner-reviewed suggestions included for this chat." if include_suggestions else "Suggestions excluded.")
    if activity_only:
        print("Activity-only scope: PC inventory, personal memory, and PC tools are excluded.")
    print("Local file/application tools enabled; application launches require approval." if pc_access else "PC file/application tools disabled.")
    if pc_access and enable_screen_read:
        print("On-demand screen OCR enabled; each capture requires approval and is processed locally.")
    else:
        print("Screen reading disabled. Start with --enable-screen-read to expose the approval-gated tool.")
    if pc_access and enable_desktop_control:
        print("On-demand KDE window listing and approval-gated focus enabled; no continuous title logging.")
    else:
        print("Desktop window control disabled. Start with --enable-desktop-control to expose it.")
    lock_fd = acquire_runtime_lock(runtime)
    try:
        return subprocess.run([node, str(cli), "dev", "--no-default-extensions"], cwd=runtime, env=environment,
                              check=False).returncode
    except KeyboardInterrupt:
        return 130
    finally:
        os.close(lock_fd)
