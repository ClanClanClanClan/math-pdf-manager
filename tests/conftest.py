"""Test configuration to fix import issues."""
import sys
from pathlib import Path

# Add src to Python path for proper imports
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


import os

import pytest


@pytest.fixture(autouse=True)
def _never_touch_the_real_library(tmp_path_factory, monkeypatch):
    """Point every test at a throwaway library.

    Production helpers resolve the library from ``MATH_LIBRARY``, and a
    few of them construct their own ``UndoLog()`` deep inside (bulk_sort,
    process_report, bulk_apply).  Without this, running the suite wrote
    real transactions into the owner's real ``.operation_log`` — 342 of
    the 357 entries in his undo history were test junk, which buried the
    15 genuine ones and made the Activity page useless.

    A test that genuinely wants the real library can still set the
    variable itself; this only changes the DEFAULT.
    """
    root = tmp_path_factory.mktemp("library")
    monkeypatch.setenv("MATH_LIBRARY", str(root))
    yield root
