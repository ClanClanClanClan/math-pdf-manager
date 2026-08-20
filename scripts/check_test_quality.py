#!/usr/bin/env python3
"""Fail on tests that cannot fail.

Seven audits of this repo kept finding the same shape of defect: a test
that runs, goes green, and would go green just as happily against code
that deletes the owner's papers.  This linter looks for the five forms
that have actually shipped here, all of which are decidable from the AST
alone:

  TQ001  a ``test_*`` function containing no assertion of any kind.
         33 of them were counted in the last audit.  A function that only
         *calls* the code under test proves that it imports.

  TQ002  ``assert x in "some literal"``.  Substring-against-a-literal is
         vacuous whenever ``x`` is the empty string, which is exactly the
         value a broken extractor returns.  ``assert "" in "anything"``
         is True.

  TQ003  an assertion whose subject is a truthy constant — ``assert
         True``, ``assert 1``, and the classic ``assert (x == y,
         "message")``, where the parenthesised tuple is always truthy and
         the comparison is never evaluated.

  TQ004  two functions with the same name in the same scope.  Python
         binds the second; the first never runs again, and pytest never
         reports it missing.  One such test in this repo has never
         executed in its life.

  TQ005  ``assert (... or True)`` and relatives — a disjunction with a
         truthy constant in it can never be False.

Usage:

    python3 scripts/check_test_quality.py                # all of tests/
    python3 scripts/check_test_quality.py tests/a.py ...  # only these
    python3 scripts/check_test_quality.py --selftest      # prove it bites

Exit status is 1 when anything is found, 0 otherwise.  Passing explicit
paths is the pre-commit mode: it fails only on the files being committed,
so the standing backlog does not block unrelated work while still making
it impossible to add a new one.
"""
from __future__ import annotations

import argparse
import ast
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

#: Callables that count as "this test can fail".  Anything whose name
#: starts with ``assert`` covers unittest (``assertEqual``) and mock
#: (``assert_called_once_with``) in one rule.
ASSERTING_NAMES = {
    "raises", "warns", "deprecated_call", "fail", "xfail", "exit",
    "check", "verify", "assert_frame_equal", "assert_series_equal",
    "assert_array_equal", "assert_allclose", "assert_almost_equal",
}


class Finding:
    __slots__ = ("path", "line", "code", "message")

    def __init__(self, path: str, line: int, code: str, message: str):
        self.path, self.line, self.code, self.message = path, line, code, message

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.code}: {self.message}"

    def key(self):
        return (self.path, self.line, self.code)


# --------------------------------------------------------------------------
# primitives
# --------------------------------------------------------------------------

def _is_truthy_constant(node: ast.AST) -> bool:
    """True for a literal that is always truthy at runtime.

    Deliberately includes non-empty tuple/list/set/dict displays: the
    ``assert (cond, "msg")`` bug is a two-element tuple and is the single
    most common always-true assertion in the wild.
    """
    if isinstance(node, ast.Constant):
        return bool(node.value)
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return len(node.elts) > 0
    if isinstance(node, ast.Dict):
        return len(node.keys) > 0
    return False


def _called_name(call: ast.Call) -> str:
    f = call.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return ""


def _is_asserting_call(call: ast.Call) -> bool:
    name = _called_name(call)
    return name.startswith("assert") or name in ASSERTING_NAMES


def _has_direct_assertion(fn: ast.AST) -> tuple[bool, set[str]]:
    """(does this body assert?, names of same-module functions it calls).

    The call set exists so that ``def test_x(): _check(thing)`` — where
    ``_check`` asserts — is not reported.  That delegation pattern is used
    legitimately in this repo's property tests.
    """
    calls: set[str] = set()
    asserts = False
    for node in ast.walk(fn):
        if isinstance(node, ast.Assert):
            asserts = True
        elif isinstance(node, ast.Call):
            if _is_asserting_call(node):
                asserts = True
            calls.add(_called_name(node))
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                ctx = item.context_expr
                if isinstance(ctx, ast.Call) and _is_asserting_call(ctx):
                    asserts = True
    return asserts, calls


# --------------------------------------------------------------------------
# the checks
# --------------------------------------------------------------------------

def _comprehension_bound_compares(root: ast.AST) -> set[int]:
    """ids of ``x in "chars"`` comparisons where ``x`` is a loop variable.

    ``all(c in "0123456789abcdef" for c in digest)`` is the character-class
    idiom, not the vacuous-substring bug: ``c`` is one character of the
    digest and can never be the empty string.  Three of these live in
    tests/utils/test_security.py and flagging them would have taught the
    reader to ignore TQ002.
    """
    exempt: set[int] = set()
    for node in ast.walk(root):
        if not isinstance(node, (ast.GeneratorExp, ast.ListComp,
                                 ast.SetComp, ast.DictComp)):
            continue
        bound = {n.id for gen in node.generators
                 for n in ast.walk(gen.target) if isinstance(n, ast.Name)}
        for inner in ast.walk(node):
            if isinstance(inner, ast.Compare) and \
                    isinstance(inner.left, ast.Name) and inner.left.id in bound:
                exempt.add(id(inner))
    return exempt


def _check_assert_expression(test: ast.AST, path: str, out: list[Finding]) -> None:
    """TQ002 / TQ003 / TQ005 over the subject of one assertion."""
    exempt = _comprehension_bound_compares(test)
    if _is_truthy_constant(test):
        rendered = _short(test)
        out.append(Finding(path, test.lineno, "TQ003",
                           f"assertion subject is the always-true literal {rendered}"
                           + (" — a parenthesised tuple, so the comparison inside "
                              "it is never checked"
                              if isinstance(test, ast.Tuple) else "")))
    for node in ast.walk(test):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
            for v in node.values:
                if _is_truthy_constant(v):
                    out.append(Finding(
                        path, getattr(v, "lineno", test.lineno), "TQ005",
                        f"`or {_short(v)}` makes this assertion unfailable"))
        if isinstance(node, ast.Compare) and id(node) not in exempt:
            for op, comp in zip(node.ops, node.comparators):
                if isinstance(op, ast.In) and isinstance(comp, ast.Constant) \
                        and isinstance(comp.value, str) \
                        and not isinstance(node.left, ast.Constant):
                    out.append(Finding(
                        path, node.lineno, "TQ002",
                        "substring test against a literal: passes vacuously when "
                        f"the left side is empty ({_short(node.left)} in "
                        f"{_short(comp)})"))
        if isinstance(node, ast.Call) and _called_name(node) == "assertIn" \
                and len(node.args) == 2 \
                and isinstance(node.args[1], ast.Constant) \
                and isinstance(node.args[1].value, str) \
                and not isinstance(node.args[0], ast.Constant):
            out.append(Finding(
                path, node.lineno, "TQ002",
                "assertIn against a string literal: passes vacuously when the "
                "first argument is empty"))


def _short(node: ast.AST, limit: int = 40) -> str:
    try:
        s = ast.unparse(node)
    except Exception:                                   # pragma: no cover
        return "<expr>"
    s = " ".join(s.split())
    return s if len(s) <= limit else s[: limit - 1] + "…"


def check_source(source: str, path: str) -> list[Finding]:
    out: list[Finding] = []
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as exc:
        return [Finding(path, exc.lineno or 0, "TQ000", f"cannot parse: {exc.msg}")]

    # ---- TQ004: duplicate names, per lexical scope --------------------
    def scan_scope(body: list[ast.stmt], scope: str) -> None:
        seen: dict[str, int] = {}
        for stmt in body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if stmt.name in seen:
                    out.append(Finding(
                        path, stmt.lineno, "TQ004",
                        f"`{stmt.name}` redefines the one at line {seen[stmt.name]} "
                        f"in {scope}; the earlier definition can never run"))
                seen[stmt.name] = stmt.lineno
            if isinstance(stmt, ast.ClassDef):
                scan_scope(stmt.body, f"class {stmt.name}")
    scan_scope(tree.body, "module scope")

    # ---- index every function so delegation can be resolved ----------
    defs: dict[str, ast.AST] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defs.setdefault(node.name, node)

    direct: dict[str, tuple[bool, set[str]]] = {}

    def asserts_transitively(name: str, seen: set[str]) -> bool:
        if name in seen or name not in defs:
            return False
        seen.add(name)
        if name not in direct:
            direct[name] = _has_direct_assertion(defs[name])
        ok, calls = direct[name]
        if ok:
            return True
        return any(asserts_transitively(c, seen) for c in calls)

    # ---- TQ001 + expression checks -----------------------------------
    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            _check_assert_expression(node.test, path, out)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("test"):
                continue
            # A @skip'd empty test is still an empty test; it is reported
            # like any other, because skips get removed and the emptiness
            # does not.
            ok, calls = _has_direct_assertion(node)
            if not ok:
                ok = any(asserts_transitively(c, {node.name}) for c in calls)
            if not ok:
                out.append(Finding(
                    path, node.lineno, "TQ001",
                    f"`{node.name}` contains no assertion — it proves only that "
                    "the code under it does not raise"))

    out.sort(key=lambda f: (f.line, f.code))
    return out


def check_file(p: Path, display: str | None = None) -> list[Finding]:
    return check_source(p.read_text(encoding="utf-8", errors="replace"),
                        display or str(p))


# --------------------------------------------------------------------------
# selftest — the linter's own evidence that it bites
# --------------------------------------------------------------------------

_GOOD = '''
import pytest

def helper(x):
    assert x > 0

def test_delegates():
    helper(3)

def test_plain():
    assert 1 + 1 == 2

def test_unittest_style(self):
    self.assertEqual(2, 2)

def test_raises():
    with pytest.raises(ValueError):
        int("x")

def test_membership_in_list():
    assert name in ["a", "b"]

def test_char_class_idiom():
    assert len(digest) == 64
    assert all(c in "0123456789abcdef" for c in digest)

def test_mock():
    m.assert_called_once_with(3)

class TestA:
    def test_one(self):
        assert True is not False

class TestB:
    def test_one(self):
        assert 2 == 2
'''

_BAD = '''
def test_no_assertion():
    do_the_thing()

def test_substring():
    assert extract_title(pdf) in "Some Long Expected Title"

def test_always_true():
    assert True

def test_tuple_assert():
    assert (a == b, "they differ")

def test_or_true():
    assert (check(x) or True)

def test_dup():
    assert 1 == 1

def test_dup():
    assert 2 == 2
'''

#: (line in _BAD, code).  Exact, not a superset: an over-eager linter is
#: as useless as an absent one, so the selftest fails on extras too.
_EXPECTED_BAD = {
    (2, "TQ001"),    # def test_no_assertion
    (6, "TQ002"),    # assert extract_title(pdf) in "Some Long Expected Title"
    (9, "TQ003"),    # assert True
    (12, "TQ003"),   # assert (a == b, "they differ")
    (15, "TQ005"),   # assert (check(x) or True)
    (20, "TQ004"),   # the second def test_dup shadows the first
}


def selftest() -> int:
    ok = True
    good = check_source(_GOOD, "<good>")
    if good:
        ok = False
        print("SELFTEST FAIL: clean fixture produced findings:")
        for f in good:
            print("   ", f)
    bad = check_source(_BAD, "<bad>")
    got = {(f.line, f.code) for f in bad}
    missing = _EXPECTED_BAD - got
    extra = got - _EXPECTED_BAD
    if missing:
        ok = False
        print("SELFTEST FAIL: these anti-patterns were NOT detected:")
        for ln, code in sorted(missing):
            print(f"    line {ln}: {code}")
    if extra:
        ok = False
        print("SELFTEST FAIL: unexpected findings on the bad fixture:")
        for f in bad:
            if (f.line, f.code) in extra:
                print("   ", f)
    print("selftest: OK" if ok else "selftest: FAILED")
    return 0 if ok else 1


# --------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="AST linter for unfailable tests")
    ap.add_argument("paths", nargs="*",
                    help="files to check; default is every tests/**/*.py")
    ap.add_argument("--selftest", action="store_true",
                    help="run the linter against its own fixtures and exit")
    ap.add_argument("--summary", action="store_true",
                    help="print per-code counts instead of every finding")
    ap.add_argument("--select", default="",
                    help="comma-separated codes to report (default: all)")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    if args.paths:
        files = [Path(p) for p in args.paths
                 if p.endswith(".py") and Path(p).is_file()]
    else:
        files = sorted((REPO / "tests").rglob("*.py"))

    wanted = {c.strip() for c in args.select.split(",") if c.strip()}
    t0 = time.perf_counter()
    findings: list[Finding] = []
    for p in files:
        try:
            rel = p.resolve().relative_to(REPO)
        except ValueError:
            rel = p
        findings.extend(check_file(p, str(rel)))
    if wanted:
        findings = [f for f in findings if f.code in wanted]
    elapsed = time.perf_counter() - t0

    counts: dict[str, int] = {}
    for f in findings:
        counts[f.code] = counts.get(f.code, 0) + 1

    if not args.summary:
        for f in findings:
            print(f)
        if findings:
            print()
    print(f"{len(files)} files, {len(findings)} findings in {elapsed:.2f}s")
    for code in sorted(counts):
        print(f"  {code}  {counts[code]}")
    if findings:
        print("\nA test that cannot fail is not evidence. Give it a postcondition\n"
              "or delete it.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
