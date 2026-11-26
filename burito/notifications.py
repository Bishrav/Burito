"""Optional local desktop notification delivery."""

import subprocess


def notify_chat_complete():
    """Report a completed turn without including conversation contents."""
    try:
        subprocess.run(
            ["notify-send", "--app-name=Burito", "Burito", "Your local reply is ready."],
            capture_output=True, timeout=2, check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return True
