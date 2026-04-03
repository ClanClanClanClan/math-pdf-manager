"""macOS native notifications for the paper watcher."""

from __future__ import annotations

import logging
import subprocess
import sys

logger = logging.getLogger(__name__)


def notify(title: str, message: str, *, sound: str = "Glass") -> None:
    """Send a macOS notification.

    Parameters
    ----------
    title : str
        Notification title (e.g. "Paper Filed").
    message : str
        Notification body (e.g. "Dupont, J.-P. - Title.pdf → 01/D/").
    sound : str
        Sound name (Glass, Basso, Ping, Pop, etc.).  Empty string for silent.
    """
    if sys.platform != "darwin":
        logger.info("[%s] %s", title, message)
        return

    # Escape for AppleScript
    title_esc = title.replace('"', '\\"').replace("\\", "\\\\")
    msg_esc = message.replace('"', '\\"').replace("\\", "\\\\")

    script = (
        f'display notification "{msg_esc}" '
        f'with title "{title_esc}" '
        f'sound name "{sound}"'
    )

    try:
        subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            timeout=5,
        )
    except Exception as exc:
        logger.debug("Notification failed: %s", exc)
