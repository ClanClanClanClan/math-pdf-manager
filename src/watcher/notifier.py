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

    # Escape for AppleScript. ORDER MATTERS: backslashes first (turning
    # one \ into two), then quotes (so the new \" escape isn't itself
    # backslash-escaped). The previous order produced syntax errors on
    # any filename containing a backslash.
    def _esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace('"', '\\"')

    # Sound is also user-influenced via config.yaml — escape it too so a
    # malformed value can't break out of the string literal.
    title_esc = _esc(title)
    msg_esc = _esc(message)
    sound_esc = _esc(sound) if sound else ""

    script = (
        f'display notification "{msg_esc}" '
        f'with title "{title_esc}"'
    )
    if sound_esc:
        script += f' sound name "{sound_esc}"'

    try:
        subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            timeout=5,
        )
    except Exception as exc:
        logger.debug("Notification failed: %s", exc)
