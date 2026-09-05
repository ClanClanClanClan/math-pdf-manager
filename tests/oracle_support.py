"""One answer to "can this machine spell-check?".

The typo oracle is macOS NSSpellChecker, reached through ctypes. There is
no equivalent on the Linux CI runner: `maintenance.typos` raises
TypoOracleUnavailable("libobjc/AppKit not found") for every call.

This went unnoticed until 2026-09-05 because CI had not run the full
suite in a long time -- the "Conservation laws" step aborted at
COLLECTION (a manifest without watchdog) and the workflow's later steps
never executed. 68 tests were failing on the runner, unseen.

Two shapes of failure come out of a missing oracle, which is why both a
marker and a hook exist:

  * the exception escapes the test (most of tests/test_maintenance/
    test_typos.py) -- the hook in tests/conftest.py converts it;
  * the production code CATCHES it and degrades, so the test fails on an
    ordinary assertion instead (tests/test_maintenance/
    test_conformance_typos.py, where a suspected_typo bucket comes back
    as invariant_violation) -- those carry @needs_oracle.

The probe runs ONCE. On a machine where the oracle works, nothing here
skips anything: a TypoOracleUnavailable there means the bridge broke,
which is the failure the module was written to catch.
"""
from __future__ import annotations

import pytest


def _probe() -> str | None:
    """The reason the oracle is unreachable here, or None if it works."""
    try:
        from maintenance.typos import TypoOracleUnavailable, self_check
    except Exception as exc:                          # pragma: no cover
        return f"maintenance.typos will not import: {exc}"
    try:
        self_check()
    except TypoOracleUnavailable as exc:
        return str(exc)
    except Exception:
        # Any other failure is a real one. Do not dress it as absence.
        return None
    return None


#: None when NSSpellChecker answers here; otherwise why it does not.
ORACLE_REASON = _probe()

SKIP_TEXT = (
    "needs macOS NSSpellChecker, which this platform does not provide "
    f"({ORACLE_REASON}). NOT a pass: the assertion was never evaluated "
    "here. It runs on the owner's machine, where the pre-commit and "
    "pre-push gates execute the same tests."
)

#: Put this on a test that fails through a DEGRADED result rather than a
#: raised TypoOracleUnavailable -- the hook cannot see those.
needs_oracle = pytest.mark.skipif(ORACLE_REASON is not None, reason=SKIP_TEXT)
