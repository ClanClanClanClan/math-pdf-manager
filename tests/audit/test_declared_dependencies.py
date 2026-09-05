"""Every third-party module src/ imports must be a declared dependency.

Two real failures motivated this, found within an hour of each other and
neither by a test:

  * ``pycryptodome`` was imported by downloader/browser_session.py and
    declared nowhere, so six tests of that module could never pass in a
    clean install — and Chrome cookie import, the thing it exists for,
    could never work either.
  * ``streamlit`` was declared but not installed in the project venv,
    so a safety test guarding "no test may write to the owner's real
    activity log" silently did not run.

Both are the same shape: the manifest and the code disagreed, and
nothing compared them.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

#: Import names that differ from the distribution name that provides them.
_PROVIDED_BY = {
    "yaml": "pyyaml",
    "fitz": "pymupdf",
    "PIL": "pillow",
    "bs4": "beautifulsoup4",
    "dateutil": "python-dateutil",
    "Crypto": "pycryptodome",
    "sklearn": "scikit-learn",
    "pypdf": "pypdf",
    "cv2": "opencv-python",
    "OpenSSL": "pyopenssl",
    "jwt": "pyjwt",
    "magic": "python-magic",
    "docx": "python-docx",
    "serial": "pyserial",
    "usb": "pyusb",
}

#: Imported behind a try/except and genuinely optional at runtime. Each
#: entry is a deliberate decision, not a place to hide a missing dep.
_OPTIONAL = {
    "llama_cpp",        # local LLM; large, and the code degrades without it
    "language_tool_python",
    "spacy",
    "transformers",
    "torch",
    "mlx",
}


def _local_top_levels() -> set:
    return {p.stem if p.is_file() else p.name
            for p in SRC.iterdir()
            if p.name != "__pycache__" and (p.is_dir() or p.suffix == ".py")}


def _guarded_line_ranges(tree) -> list:
    """Line spans inside a `try:` body.

    An import there is a deliberate optional dependency: the code is
    written to work without it. An import outside one is a hard
    requirement, and the manifest must say so.
    """
    spans = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Try) and node.body:
            spans.append((node.body[0].lineno,
                          max(getattr(n, "end_lineno", n.lineno)
                              for n in node.body)))
    return spans


def _imports() -> list:
    """[(top_level, guarded, "file:line"), ...] for every import under src/."""
    out = []
    for path in sorted(SRC.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
        except SyntaxError:                          # pragma: no cover
            continue
        spans = _guarded_line_ranges(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and not node.level:
                names = [(node.module or "").split(".")[0]]
            else:
                continue
            guarded = any(a <= node.lineno <= b for a, b in spans)
            for name in names:
                if name:
                    out.append((name, guarded,
                                f"{path.relative_to(ROOT)}:{node.lineno}"))
    return out


def _declared() -> set:
    out: set = set()
    for rel in ("requirements.txt", "config/requirements.txt", "pyproject.toml"):
        p = ROOT / rel
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip().strip('",')
            if not line or line.startswith("#"):
                continue
            m = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)", line)
            if m:
                out.add(m.group(1).lower().replace("_", "-"))
    return out


def _third_party(name: str, local: set) -> bool:
    return not (name in local or name in sys.stdlib_module_names
                or name.startswith("_"))


def test_every_unguarded_third_party_import_is_declared():
    """An unguarded import is a hard requirement by definition — if it
    is missing the module cannot even be imported."""
    local = _local_top_levels()
    declared = _declared()
    bad = {}
    for name, guarded, site in _imports():
        if guarded or not _third_party(name, local):
            continue
        dist = _PROVIDED_BY.get(name, name).lower().replace("_", "-")
        if dist in declared or name.lower().replace("_", "-") in declared:
            continue
        bad.setdefault(name, []).append(site)
    assert not bad, (
        "imported unguarded by src/ but declared in no manifest — a clean "
        "install cannot even import these modules:\n" + "\n".join(
            f"  {n} (provided by {_PROVIDED_BY.get(n, n)}) at {s[0]}"
            f"{f' +{len(s) - 1} more' if len(s) > 1 else ''}"
            for n, s in sorted(bad.items())))


@pytest.mark.parametrize("module", ["streamlit", "cryptography", "regex",
                                    "keyring"])
def test_a_declared_dependency_is_actually_installed(module):
    """Declared but absent is the mirror-image failure, and it hid a
    safety test: the cockpit is the owner's only interface, and its
    import was failing in the test environment for months."""
    import importlib.util
    assert importlib.util.find_spec(module) is not None, (
        f"{module} is declared in requirements but is not installed here")


def test_a_guarded_import_of_a_local_module_can_never_resolve():
    """A fallback that always fails is a fallback that does not exist.

    Four of these are live in the tree today. The worst is
    validators/author_parser.py, which tries `from author_processing
    import fix_author_block` to reach what its own comment calls the
    "comprehensive" implementation — while that module actually sits at
    validators/filename_checker/author_processing.py, so the import
    raises every time and the simple fallback is what has always run.

    This test is deliberately allowed to name them rather than fail:
    fixing them changes behaviour that has been dormant for a long time,
    and that is a decision for the owner, not a side effect of a test.
    """
    local = _local_top_levels()
    unreachable = []
    for name, guarded, site in _imports():
        if not guarded or not _third_party(name, local):
            continue
        # A module of that name exists somewhere under src/, but not at
        # a level where this import statement could ever find it.
        if list(SRC.rglob(f"{name}.py")):
            unreachable.append(f"{name} at {site}")
    assert len(unreachable) <= 4, (
        "new dead fallback import(s) — a guarded import naming a module "
        "that exists under src/ but not where this statement can reach "
        f"it:\n  " + "\n  ".join(unreachable))


def test_the_optional_list_is_not_a_dumping_ground():
    """Anything exempted must genuinely be imported defensively, or the
    exemption list becomes where missing dependencies go to be
    forgotten — which is how this class of bug survives."""
    local = _local_top_levels()
    unguarded_optional = {}
    for name, guarded, site in _imports():
        if name in _OPTIONAL and not guarded and _third_party(name, local):
            unguarded_optional.setdefault(name, []).append(site)
    assert not unguarded_optional, (
        "on the optional list but imported unguarded — either wrap it in "
        f"try/except or declare it: {unguarded_optional}")


# ---------------------------------------------------------------------------
# The gap that let a broken CI look green.
#
# `_declared()` above accepts a dependency declared in ANY of three
# manifests. CI installed exactly ONE of them -- and the stale one. So
# `watchdog` counted as declared (requirements.txt and pyproject.toml both
# name it) while the runner never installed it, and the disagreement was
# invisible to every test.
#
# It surfaced the loud way: tests/safety/test_watcher_survives_a_deleted_inbox.py
# imports `watcher.daemon` at module level, that module imports watchdog
# unguarded, and pytest aborted COLLECTION of the whole tests/safety tier --
# the conservation-laws tier, the one that caught the re-armed inbox
# hard-delete. Six other packages were missing the same way and had been
# skipping quietly, streamlit among them: the cockpit is the owner's entire
# interface and CI could not import it.
#
# The rule below is therefore not "is it declared somewhere" but "does the
# environment CI actually builds satisfy the code".
# ---------------------------------------------------------------------------

CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def _ci_install_set() -> tuple:
    """(distributions CI installs, manifest paths it reads).

    Parsed from the workflow rather than hard-coded: hard-coding the
    answer here would recreate the very split this test exists to close.
    """
    dists: set = set()
    manifests: list = []
    if not CI_WORKFLOW.exists():                     # pragma: no cover
        return dists, manifests
    # Join shell line-continuations FIRST. The workflow spreads one
    # `pip install` over two lines with a trailing backslash, and a
    # parser that reads lines independently silently loses everything
    # after the break -- which would make this check under-report
    # exactly like the bug it is here to catch.
    joined: list = []
    pending = ""
    for raw in CI_WORKFLOW.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if pending:
            stripped = pending + " " + stripped
            pending = ""
        if stripped.endswith("\\"):
            pending = stripped[:-1].strip()
            continue
        joined.append(stripped)
    if pending:
        joined.append(pending)

    for line in joined:
        if line.startswith("#") or "pip install" not in line:
            continue
        tokens = line.split("pip install", 1)[1].strip().split()
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            if tok in ("-r", "--requirement"):
                if i + 1 < len(tokens):
                    rel = tokens[i + 1]
                    manifests.append(rel)
                    p = ROOT / rel
                    if p.exists():
                        for ln in p.read_text(encoding="utf-8").splitlines():
                            ln = ln.split("#")[0].strip()
                            if not ln:
                                continue
                            m = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)", ln)
                            if m:
                                dists.add(m.group(1).lower().replace("_", "-"))
                i += 2
                continue
            if tok.startswith("-") or tok in ("pip", "python", "-m"):
                i += 1
                continue
            m = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)", tok)
            if m:
                dists.add(m.group(1).lower().replace("_", "-"))
            i += 1
    return dists, manifests


def test_the_ci_workflow_actually_reads_a_manifest():
    """Pathology guard: if the parser silently found nothing, the checks
    below would pass over an empty set and prove nothing. An assertion
    that cannot fail is the exact failure mode this file exists to
    prevent."""
    dists, manifests = _ci_install_set()
    assert manifests, (
        "parsed no `pip install -r <file>` out of .github/workflows/ci.yml — "
        "either the workflow stopped installing a manifest, or this parser "
        "no longer understands it. Either way the checks below are vacuous.")
    assert len(dists) > 10, (
        f"CI's install set parsed to only {len(dists)} distributions "
        f"{sorted(dists)} — implausible, so the parse is wrong.")


def test_ci_installs_everything_src_imports_unguarded():
    """What CI installs must satisfy what the code imports.

    This is the check `test_every_unguarded_third_party_import_is_declared`
    cannot make: that one asks whether a human wrote the name down
    somewhere, this one asks whether the runner will actually have it.
    """
    local = _local_top_levels()
    installed, manifests = _ci_install_set()
    missing = {}
    for name, guarded, site in _imports():
        if guarded or not _third_party(name, local):
            continue
        dist = _PROVIDED_BY.get(name, name).lower().replace("_", "-")
        if dist in installed or name.lower().replace("_", "-") in installed:
            continue
        missing.setdefault(name, []).append(site)
    assert not missing, (
        "imported unguarded by src/ but NOT installed by CI "
        f"(CI reads {manifests}) — these modules cannot be imported on the "
        "runner, and a test touching one aborts collection for its whole "
        "tier:\n" + "\n".join(
            f"  {n} (provided by {_PROVIDED_BY.get(n, n)}) at {s[0]}"
            f"{f' +{len(s) - 1} more' if len(s) > 1 else ''}"
            for n, s in sorted(missing.items())))


def test_ci_installs_the_manifest_this_file_validates():
    """`_declared()` validates a union of manifests; CI installs a subset.
    Whenever those diverge a dependency can be 'declared' and still be
    absent on the runner — which is what happened."""
    _, manifests = _ci_install_set()
    validated = {"requirements.txt", "config/requirements.txt", "pyproject.toml"}
    assert set(manifests) & validated, (
        f"CI installs {manifests}, none of which _declared() validates — "
        "the manifest check and the runner have drifted apart again.")
    assert "requirements.txt" in manifests, (
        f"CI installs {manifests}. requirements.txt is the curated manifest "
        "(it names streamlit, watchdog, keyring, langdetect, radon, "
        "typing_extensions and psutil); config/requirements.txt is a stale "
        "superset-of-the-wrong-things that omits all seven.")
