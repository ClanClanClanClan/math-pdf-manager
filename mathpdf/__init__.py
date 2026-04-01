"""Compatibility shim exposing the legacy ``src`` package as ``mathpdf``.

The historical codebase kept all modules inside a ``src`` directory without a
proper top-level package.  Modern tooling and the new test-suite expect
``import mathpdf`` to resolve to these modules.  We achieve this by declaring
``mathpdf`` as a package whose search path points at the existing ``src``
folder.  Submodules such as ``mathpdf.acquisition.engine`` therefore map
transparently to ``src/acquisition/engine.py`` without duplicating code.
"""
from __future__ import annotations

from pathlib import Path
import sys

_PACKAGE_DIR = Path(__file__).resolve().parent
_SRC_DIR = _PACKAGE_DIR.parent / "src"

# Ensure ``src`` is importable for legacy absolute imports like ``import constants``.
_src_str = str(_SRC_DIR)
if _src_str not in sys.path:
    sys.path.insert(0, _src_str)

# Allow importing ``mathpdf`` submodules while keeping room for future overrides
# inside the top-level ``mathpdf`` package.
__path__ = [str(_PACKAGE_DIR), _src_str]

# Provide lightweight shims for optional third-party modules that are not
# required in constrained environments. This keeps unit tests running without
# pulling heavy dependencies.
try:  # pragma: no cover - real dependency available
    import respx as _respx  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - expected in minimal envs
    from .external import respx_stub as _respx_stub  # noqa: WPS433 (vendored module)

    sys.modules.setdefault("respx", _respx_stub)

# Expose a basic version attribute for convenience when introspecting the
# package.  Fall back to a development marker if the VERSION file is absent.
try:
    _version_file = Path(__file__).resolve().parent.parent / "VERSION"
    __version__ = _version_file.read_text(encoding="utf-8").strip()
except FileNotFoundError:  # pragma: no cover - optional metadata
    __version__ = "0.0.dev"

__all__ = ["__version__"]
