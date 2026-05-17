"""Quiet-window helpers for headful Playwright browser launches.

Some publisher download flows (Elsevier, SIAM, Wiley, Oxford, IEEE, ...)
require a real visible browser to clear Cloudflare or to drive an
institutional Shibboleth login.  By default Playwright opens those
windows full-screen and on top of whatever the user is doing, which is
the opposite of what we want: the user has explicitly said *automatic
web navigation in headful mode must not get in the way*.

This module produces the Chromium launch arguments that pin the
browser to a tiny corner-positioned window, plus a post-launch helper
that calls ``page.evaluate("window.moveTo/resizeTo")`` as a
belt-and-suspenders backup for sites that auto-resize themselves.

Public API
----------
* ``quiet_args(extra=None)`` – list of Chromium ``--flag`` strings to
  pass to ``chromium.launch(args=...)`` or
  ``launch_persistent_context(args=...)``.
* ``quiet_page(page)`` – async coroutine that shrinks and corner-pins
  whatever Playwright Page you pass.  Use after ``new_page()`` /
  ``page = await context.new_page()``.

Configuration
-------------
Defaults match a typical 16" MacBook (2048×1280 logical) but the
positions and sizes are overridable via environment variables so the
user can park the windows wherever they like::

    MATHPDF_QUIET_X     (default 2400)
    MATHPDF_QUIET_Y     (default 1100)
    MATHPDF_QUIET_W     (default 360)
    MATHPDF_QUIET_H     (default 280)

Set ``MATHPDF_QUIET_DISABLE=1`` to fall back to default Playwright
behaviour (useful for debugging download flows).
"""
from __future__ import annotations

import logging
import os
from typing import Iterable, Optional

logger = logging.getLogger(__name__)


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("env %s=%r not an int — using default %d", name, raw, default)
        return default


def is_disabled() -> bool:
    """Honour ``MATHPDF_QUIET_DISABLE`` so debugging stays easy."""
    return os.environ.get("MATHPDF_QUIET_DISABLE", "").lower() in ("1", "true", "yes")


def quiet_position() -> tuple[int, int, int, int]:
    """Return ``(x, y, width, height)`` for the corner-pinned window.

    Defaults: bottom-right of a 16" MacBook screen, just large enough
    that Cloudflare's challenge widget still fits.
    """
    return (
        _env_int("MATHPDF_QUIET_X", 2400),
        _env_int("MATHPDF_QUIET_Y", 1100),
        _env_int("MATHPDF_QUIET_W", 360),
        _env_int("MATHPDF_QUIET_H", 280),
    )


def quiet_args(extra: Optional[Iterable[str]] = None) -> list[str]:
    """Chromium launch args that park a headful window in the corner.

    Pass to ``p.chromium.launch(args=quiet_args())`` or
    ``p.chromium.launch_persistent_context(..., args=quiet_args())``.

    Falls back to ``extra`` only (no positioning) when the user has set
    ``MATHPDF_QUIET_DISABLE=1``.
    """
    base: list[str] = list(extra or [])
    if is_disabled():
        return base

    x, y, w, h = quiet_position()
    pinned = [
        # Position + size of the OS-level browser window.  Chromium
        # accepts these on launch.
        f"--window-position={x},{y}",
        f"--window-size={w},{h}",
        # Reduce visual noise: hide the "Chrome is being controlled by
        # automated test software" infobar.
        "--disable-infobars",
        # Don't steal focus when the window opens.  Without this flag
        # the new window pops to the front and interrupts whatever the
        # user is typing into.
        "--no-startup-window",
    ]
    # ``--no-startup-window`` is too aggressive for some flows (it
    # suppresses the initial blank tab); drop it when there's an
    # explicit URL in extra.  Easiest heuristic: only keep it when no
    # other args mention a URL or a starting page.
    if any("--app=" in a or "http" in a for a in base):
        pinned = [a for a in pinned if a != "--no-startup-window"]
    return base + pinned


async def quiet_page(page) -> None:
    """Post-launch backup: shrink + corner-pin the page's own window.

    Some sites (notably any that uses ``window.resizeTo``) override
    the launch-time window size.  Calling ``window.moveTo`` /
    ``window.resizeTo`` from inside the page is the only reliable way
    to put them back where we want.

    Failures here are non-fatal — the worst case is the window stays
    wherever the site moved it, which is no worse than today.
    """
    if is_disabled():
        return
    x, y, w, h = quiet_position()
    try:
        await page.evaluate(
            f"() => {{ window.moveTo({x}, {y}); window.resizeTo({w}, {h}); }}"
        )
    except Exception as exc:  # pragma: no cover - best-effort
        logger.debug("quiet_page resize failed: %s", exc)


def quiet_page_sync(page) -> None:
    """Sync variant of :func:`quiet_page` for ``sync_playwright`` users."""
    if is_disabled():
        return
    x, y, w, h = quiet_position()
    try:
        page.evaluate(
            f"() => {{ window.moveTo({x}, {y}); window.resizeTo({w}, {h}); }}"
        )
    except Exception as exc:  # pragma: no cover - best-effort
        logger.debug("quiet_page_sync resize failed: %s", exc)
