"""No module may define the same top-level name twice.

Python keeps the LAST definition. A shadowed first copy is not a harmless
duplicate: you can read it, edit it, satisfy yourself the change is right,
run the tests green, and have changed nothing at all -- because the file
goes on to define the name again forty lines later.

There were 13 of these, all byte-identical, across three cockpit modules:
_flash, _render_flashes, _preview_pdf_cached, _find_publication_reports,
_report_candidates, _scan_conflicts_cached, _scan_snapshot_path, _save_scan,
_load_scan, load_env_overrides, apply_env_overrides, _save_env_override and
list_dismissals.
"""
import ast
import collections
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src"

#: ``@overload`` and ``@singledispatch`` legitimately repeat a name, and a
#: name defined once per branch of a try/except import is not a shadow --
#: only TOP-LEVEL siblings in the same body are.
_ALLOWED_DECORATORS = {"overload", "singledispatchmethod", "register"}


def _decorator_names(node):
    out = set()
    for d in node.decorator_list:
        target = d.func if isinstance(d, ast.Call) else d
        out.add(getattr(target, "attr", None) or getattr(target, "id", None))
    return out


def _shadowed(path: Path):
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return []
    seen = collections.defaultdict(list)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if _decorator_names(node) & _ALLOWED_DECORATORS:
                continue
            seen[node.name].append(node.lineno)
    return [(name, lines) for name, lines in seen.items() if len(lines) > 1]


ALL = sorted(SRC.rglob("*.py"))


def test_the_source_tree_has_python_files_to_check():
    """Guard the guard: a glob that matches nothing passes every assertion."""
    assert len(ALL) > 100


@pytest.mark.parametrize("path", ALL, ids=lambda p: str(p.relative_to(SRC)))
def test_no_top_level_name_is_defined_twice(path):
    dupes = _shadowed(path)
    assert dupes == [], (
        f"{path.relative_to(SRC)} defines these top-level names more than "
        f"once; Python keeps the last, so editing an earlier copy changes "
        f"nothing: {dupes}"
    )
