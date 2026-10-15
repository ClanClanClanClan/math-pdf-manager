"""Find, by AST, every cockpit button that changes the library.

A "write site" is a button press whose branch reaches a function that
moves, renames, retires or rewrites a paper or its saved record.  It is
found from the source, not from a hand-kept list, so a button added
tomorrow is in the list tomorrow.

Three shapes of press occur in the cockpit, and all three are read:

* ``if st.button(...):`` / ``if col.button(...) and ok:`` -- the branch;
* ``go = st.form_submit_button(...)`` then ``if go:`` -- the same;
* ``if not st.button(...): continue`` -- everything after the guard in
  that block (Home's per-item actions).  When that code then dispatches
  on a constant (``if action_id == "accept_topic":``) each arm that
  writes is its own site, because each is a different button on screen.

"Reaches" is computed by name over the ``ui`` package: a function defined
there that calls -- or merely names, as ``_locked_call(lib, "Undo",
_undo_transaction, tx)`` does -- a writer is itself a writer.  The roots
are :data:`SINKS`, the library-writing entry points the cockpit can call,
each with what it writes.  A call with a literal ``dry_run=True`` is a
preview and does not count.

A press nested inside another press (a two-step confirm) belongs to the
inner button only: pressing the outer one alone writes nothing.

Used by ``test_every_library_writing_button_is_pressed.py``.
"""
from __future__ import annotations

import ast
import functools
import importlib.util
from dataclasses import dataclass
from pathlib import Path

def _src() -> Path:
    """The ``src`` the ``ui`` package is imported from -- the code that
    actually runs, which is what a mutation harness changes."""
    spec = importlib.util.find_spec("ui")
    return Path(spec.origin).resolve().parents[1]


SRC = _src()

#: The ui modules the cockpit is made of.  ``cockpit.py`` delegates pages
#: and actions to the others.
UI_MODULES = ("ui/cockpit.py", "ui/cockpit_actions.py", "ui/attention_queue.py",
              "ui/search_page.py", "ui/paper_preview.py")

#: Library-writing entry points, by the name the cockpit calls them under,
#: with what they write.  Generic names (``save``) are deliberately NOT
#: here: ``C.save`` writes a conformance report and ``cfg.save`` the
#: watcher's settings, neither of which is the library.
SINKS: dict[str, str] = {
    # papers moved or renamed
    "apply_renames": "library_normalize: renames PDFs and their records",
    "logged_move": "undo_log: moves a PDF and its record",
    "logged_rename": "undo_log: renames a PDF and its record",
    "undo_transaction": "undo_log: puts files back (unless dry_run=True)",
    "file_into_topic": "publication_topic_router: files a paper into a topic",
    "accept_topic_suggestion": "publication_topic_router: file_into_topic",
    "apply_topic_proposals": "pipeline_preview: files papers into topics",
    "bulk_sort": "bulk_sort: files the 12/ backlog",
    "sort_one": "bulk_sort: files one paper",
    "process_report": "upgrade_to_published: replaces preprints",
    "upgrade_paper": "upgrade_to_published: replaces a preprint",
    "upgrade_entries": "upgrade_to_published: replaces preprints",
    "transition_aged_papers": "aging_checker: moves 03 -> 02",
    "ingest_paper": "ingest: files a new paper into the library",
    # papers retired
    "retire_variant": "preprint_variants: retires a variant to .trash",
    "resolve_group": "duplicate_scan: retires duplicate copies",
    "apply_duplicate_resolutions": "duplicate_scan: retires duplicates",
    "resolve_keep_both": "conflict_resolver: renames a conflict copy",
    "resolve_keep_canonical": "conflict_resolver: retires a conflict copy",
    "resolve_keep_conflict": "conflict_resolver: replaces the canonical",
    "mark_flag_done": "cockpit_actions: retires a .txt flag to .trash",
    # files created in the library
    "flag_for_manual_download": "upgrade_to_published: writes a 04/ flag",
    # saved records
    "apply_reconnect": "sidecar_repair: moves records",
    "apply_trash_reconnect": "sidecar_repair: moves records",
    "apply_record_merges": "sidecar_repair: merges records",
    "backfill_directory": "identity: writes records",
    "backfill_classifier_text": "classifier_text: writes records",
    "backfill_identifiers": "preprint_variants: writes records",
    "reject_topic_suggestion": "publication_topic_router: writes a record",
    "reset_recheck_state": "publication_state: writes a record",
    "patch_record": "identity: rewrites a record",
    "check_publications": "weekly_report: writes Crossref answers to records",
    "save": "PaperIdentity.save: writes a record (but see SAVE_NOT_THE_LIBRARY)",
    # out of process
    "run_publication_check": "cockpit_actions: a subprocess writes records",
    # raw filesystem primitives, wherever they appear in ui code
    "move": "shutil.move",
    "rename": "Path.rename / os.rename",
    "unlink": "Path.unlink",
}

#: ``<receiver>.save(...)`` calls in ui code that do not write a record.
SAVE_NOT_THE_LIBRARY: dict[str, str] = {
    "C": "maintenance.conformance.save writes a conformance report",
    "cfg": "WatcherConfig.save writes the filer's settings",
}

#: ui functions that use a raw primitive on something that is NOT the
#: library.  The structural test fails if one of these stops existing, so
#: the list cannot rot into a blanket excuse.
NOT_THE_LIBRARY: dict[str, str] = {
    "_log_activity": "rotates ~/.mathpdf/cockpit_activity.jsonl",
    "stop_weekly": "moves the Monday sweep's LaunchAgent plist aside",
    "save_uploads_to_inbox": "writes the inbox, which is plumbing",
}

_BUTTONS = {"button", "form_submit_button"}
_DEFS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)


@dataclass(frozen=True)
class WriteSite:
    module: str
    function: str            # dotted chain of enclosing defs
    label: str               # key if given, else label; f-string holes {}
    arm: str                 # the dispatch constant, or ""
    line: int                # line of the button call
    write_lines: frozenset   # statements in the branch that reach a sink
    reaches: tuple           # the sinks reached
    body_lines: frozenset = frozenset()   # every statement of the branch
    helpers: tuple = ()      # ui functions the branch calls that write

    @property
    def module_name(self) -> str:
        return self.module[:-3].replace("/", ".")

    @property
    def id(self) -> str:
        return f"{self.function}[{self.label}]" + (
            f"<{self.arm}>" if self.arm else "")


# --------------------------------------------------------------------------
# names
# --------------------------------------------------------------------------

def _text(node) -> str:
    """A key or label as source text; f-string holes become {}."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(v.value if isinstance(v, ast.Constant) else "{}"
                       for v in node.values)
    return "" if node is None else "{" + ast.unparse(node) + "}"


def _button_call(node) -> ast.Call | None:
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr in _BUTTONS):
        return node
    return None


def _button_label(call: ast.Call) -> str:
    for want in ("key", "label"):
        for kw in call.keywords:
            if kw.arg == want:
                return _text(kw.value)
    return _text(call.args[0]) if call.args else ""


def _dry_run(call: ast.Call) -> bool:
    """``f(..., dry_run=True)`` with a literal True previews, never writes."""
    return any(kw.arg == "dry_run" and isinstance(kw.value, ast.Constant)
               and kw.value.value is True for kw in call.keywords)


def _walk_own(node):
    """``node`` and its descendants, NOT descending into nested defs."""
    stack = [node]
    while stack:
        n = stack.pop()
        yield n
        for c in ast.iter_child_nodes(n):
            if not isinstance(c, _DEFS):
                stack.append(c)


#: ``from m import a as b`` anywhere in the ui modules: b means a.  Filled
#: by :func:`load_trees`.
_ALIASES: dict[str, str] = {}


def _refs(nodes) -> set[str]:
    """Names called or referenced (``fn`` passed as an argument counts).

    The callee of a literal ``dry_run=True`` call is not counted, and an
    import alias (``mark_flag_done as _mark_flag_done``) is read as the
    name it stands for.
    """
    nodes = list(nodes)
    skip = {id(n.func) for n in nodes
            if isinstance(n, ast.Call) and _dry_run(n)}
    out = set()
    for n in nodes:
        if id(n) in skip:
            continue
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
            out.add(_ALIASES.get(n.id, n.id))
        elif isinstance(n, ast.Attribute):
            if (n.attr == "save" and isinstance(n.value, ast.Name)
                    and n.value.id in SAVE_NOT_THE_LIBRARY):
                continue
            out.add(n.attr)
    return out


def load_trees(src: Path = SRC) -> dict:
    trees = {m: ast.parse((src / m).read_text(encoding="utf-8"), filename=m)
             for m in UI_MODULES if (src / m).exists()}
    _ALIASES.clear()
    for tree in trees.values():
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom):
                for a in n.names:
                    if a.asname and a.asname != a.name:
                        _ALIASES[a.asname] = a.name
    return trees


def writers(trees: dict) -> dict[str, set[str]]:
    """{ui function name: the sinks it reaches}, closed under calls."""
    fns: dict[str, list] = {}
    for tree in trees.values():
        for n in ast.walk(tree):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fns.setdefault(n.name, []).append(n)
    refs = {name: set().union(*(_refs(
        x for s in fn.body for x in _walk_own(s)) for fn in nodes))
        for name, nodes in fns.items()}
    reach = {name: (set() if name in NOT_THE_LIBRARY
                    else refs[name] & SINKS.keys()) for name in fns}
    changed = True
    while changed:
        changed = False
        for name in fns:
            if name in NOT_THE_LIBRARY:
                continue
            for callee in refs[name] & fns.keys():
                if callee != name and not reach[callee] <= reach[name]:
                    reach[name] |= reach[callee]
                    changed = True
    for name in fns:              # a sink defined in ui code (mark_flag_done)
        if name in SINKS:
            reach[name].add(name)
    return {k: v for k, v in reach.items() if v}


# --------------------------------------------------------------------------
# presses
# --------------------------------------------------------------------------

def _terminates(stmts) -> bool:
    return bool(stmts) and isinstance(stmts[-1], (ast.Continue, ast.Return,
                                                  ast.Break))


def _press_in(test, pressed: dict) -> ast.Call | None:
    for n in ast.walk(test):
        call = _button_call(n)
        if call is not None:
            return call
        if isinstance(n, ast.Name) and n.id in pressed:
            return pressed[n.id]
    return None


def _positive_press(stmt, pressed) -> ast.Call | None:
    """``if <press ...>:`` -- but not ``if not <press>: continue``."""
    if not isinstance(stmt, ast.If) or _guard_press(stmt, pressed):
        return None
    return _press_in(stmt.test, pressed)


def _guard_press(stmt, pressed) -> ast.Call | None:
    """``if not <press>: continue`` (or return/break)."""
    if (isinstance(stmt, ast.If) and isinstance(stmt.test, ast.UnaryOp)
            and isinstance(stmt.test.op, ast.Not) and not stmt.orelse
            and _terminates(stmt.body)):
        return _press_in(stmt.test.operand, pressed)
    return None


def _blocks(stmt):
    for name in ("body", "orelse", "finalbody"):
        b = getattr(stmt, name, None)
        if b and isinstance(b[0], ast.stmt):
            yield b
    for h in getattr(stmt, "handlers", ()) or ():
        yield h.body
    for c in getattr(stmt, "cases", ()) or ():
        yield c.body


def _arm_of(stmt) -> str | None:
    """``if NAME == "const":`` -> "const"."""
    t = getattr(stmt, "test", None)
    if (isinstance(t, ast.Compare) and len(t.ops) == 1
            and isinstance(t.ops[0], ast.Eq) and isinstance(t.left, ast.Name)
            and isinstance(t.comparators[0], ast.Constant)
            and isinstance(t.comparators[0].value, str)):
        return t.comparators[0].value
    return None


def _write_stmts(stmts, wr, pressed, arm=""):
    """(arm, line, sinks, helpers) for each statement in ``stmts``, stopping
    at nested presses and nested defs.  ``sinks`` is empty for a statement
    that does not write by itself."""
    for i, s in enumerate(stmts):
        if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(s, ast.Assign) and _button_call(s.value) is not None:
            for t in s.targets:
                if isinstance(t, ast.Name):
                    pressed[t.id] = s.value
            continue
        if _positive_press(s, pressed) is not None:
            yield from _write_stmts(s.orelse, wr, pressed, arm)
            continue
        if _guard_press(s, pressed) is not None:
            return                      # the rest belongs to the inner press
        own = [n for n in _shallow(s)]
        hit = _reach(own, wr)
        yield arm, s.lineno, hit, (_refs(own) & wr.keys()) if hit else set()
        sub_arm = _arm_of(s)
        if isinstance(s, ast.If) and sub_arm is not None:
            yield from _write_stmts(s.body, wr, pressed, sub_arm)
            yield from _write_stmts(s.orelse, wr, pressed, arm)
            continue
        for b in _blocks(s):
            yield from _write_stmts(b, wr, pressed, arm)


def _shallow(stmt):
    """A statement's own expressions, not the statements nested in it."""
    stack = [stmt]
    while stack:
        n = stack.pop()
        yield n
        for c in ast.iter_child_nodes(n):
            if isinstance(c, (ast.stmt, ast.excepthandler, ast.match_case)
                          ) or isinstance(c, _DEFS):
                continue
            stack.append(c)


def _reach(nodes, wr) -> set[str]:
    out = set()
    for name in _refs(nodes):
        if name in SINKS:
            out.add(name)
        if name in wr:
            out |= wr[name]
    return out


def find_write_sites(src: Path = SRC) -> list[WriteSite]:
    """Every write site in the ``ui`` modules under ``src``."""
    return list(_find_write_sites(Path(src).resolve()))


@functools.lru_cache(maxsize=8)
def _find_write_sites(src: Path) -> tuple:
    trees = load_trees(src)
    wr = writers(trees)
    sites: list[WriteSite] = []

    def emit(module, chain, call, body, pressed):
        by_arm: dict[str, tuple[set, set, set, set]] = {}
        for arm, line, hit, helpers in _write_stmts(body, wr, dict(pressed)):
            lines, sinks, every, hl = by_arm.setdefault(
                arm, (set(), set(), set(), set()))
            every.add(line)
            if hit:
                lines.add(line)
                sinks |= hit
                hl |= helpers
        for arm, (lines, sinks, every, hl) in sorted(by_arm.items()):
            if not lines:
                continue
            sites.append(WriteSite(
                module=module, function=".".join(chain),
                label=_button_label(call), arm=arm, line=call.lineno,
                write_lines=frozenset(lines), reaches=tuple(sorted(sinks)),
                body_lines=frozenset(every), helpers=tuple(sorted(hl))))

    def scan(module, stmts, chain, pressed):
        for i, s in enumerate(stmts):
            if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)):
                scan(module, s.body, chain + [s.name], {})
                continue
            if isinstance(s, ast.ClassDef):
                scan(module, s.body, chain + [s.name], {})
                continue
            if isinstance(s, ast.Assign) and _button_call(s.value) is not None:
                for t in s.targets:
                    if isinstance(t, ast.Name):
                        pressed[t.id] = s.value
            call = _positive_press(s, pressed)
            if call is not None:
                emit(module, chain, call, s.body, pressed)
            call = _guard_press(s, pressed)
            if call is not None:
                emit(module, chain, call, stmts[i + 1:], pressed)
            for b in _blocks(s):
                scan(module, b, chain, pressed)

    for module, tree in trees.items():
        scan(module, tree.body, [], {})
        for n in ast.walk(tree):
            if _button_call(n) is None:
                continue
            for kw in n.keywords:
                if kw.arg == "on_click":
                    hit = _reach(_walk_own(kw.value), wr)
                    if hit:
                        sites.append(WriteSite(
                            module=module, function="<on_click>",
                            label=_button_label(n), arm="", line=n.lineno,
                            write_lines=frozenset({n.lineno}),
                            reaches=tuple(sorted(hit))))
    return tuple(sites)


if __name__ == "__main__":  # pragma: no cover -- a reading aid
    for s in find_write_sites():
        print(f"{s.module}:{s.line}  {s.id}  -> {', '.join(s.reaches)}"
              f"  write_lines={sorted(s.write_lines)}")


# --------------------------------------------------------------------------
# Is SINKS complete?  A second, independent opinion.
# --------------------------------------------------------------------------
#
# SINKS is a list someone keeps.  If a cockpit button starts calling a new
# processing function that writes, and nobody adds it there, its button
# silently stops being a write site.  So every name the ui imports from the
# rest of ``src`` is also traced through the code that defines it, module-
# qualified, to the operations that can only mean "the library changed":
# the undo log's own record_* calls and logged_* helpers, patch_record, a
# record's ``.save(``, ``shutil.move`` and ``.rename(``.  Anything that
# reaches one must be a SINK or be named in IMPORTS_NOT_THE_LIBRARY.

#: Primitives that, wherever they occur, change the library.
STRONG = {"logged_move", "logged_rename", "logged_copy", "patch_record",
          "record_move", "record_rename", "record_copy", "record_sidecar_edit"}

#: Imported by the ui, reaches a STRONG primitive, and is still not a
#: library-writing entry point.  Name -> why.
IMPORTS_NOT_THE_LIBRARY: dict[str, str] = {}


@functools.lru_cache(maxsize=2)
def _module_trees(src: Path) -> dict:
    out = {}
    for f in src.rglob("*.py"):
        mod = ".".join(f.relative_to(src).with_suffix("").parts)
        if mod.endswith(".__init__"):
            mod = mod[: -len(".__init__")]
        try:
            out[mod] = ast.parse(f.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):     # pragma: no cover
            continue
    return out


def _imports(mod: str, tree) -> dict:
    out = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and n.module is not None:
            base = n.module
            if n.level:
                base = ".".join(mod.split(".")[: -n.level] + [n.module])
            for a in n.names:
                out[a.asname or a.name] = (base, a.name)
    return out


def imports_that_write(src: Path = None) -> dict:
    """{(module, name) the ui imports: the STRONG primitives it reaches}."""
    src = Path(src or SRC).resolve()
    trees = _module_trees(src)
    funcs = {}
    for mod, t in trees.items():
        for n in t.body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                funcs[(mod, n.name)] = n
            elif isinstance(n, ast.ClassDef):
                for m in n.body:
                    if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        funcs[(mod, f"{n.name}.{m.name}")] = m
    imps = {mod: _imports(mod, t) for mod, t in trees.items()}

    def direct(mod, node):
        prims, callees = set(), set()
        for n in ast.walk(node):
            if not isinstance(n, ast.Call) or _dry_run(n):
                continue
            f = n.func
            if isinstance(f, ast.Name):
                target = imps[mod].get(f.id, (mod, f.id))
                if target[1] in STRONG:
                    prims.add(target[1])
                callees.add(target)
            elif isinstance(f, ast.Attribute):
                recv = f.value.id if isinstance(f.value, ast.Name) else None
                if f.attr in STRONG:
                    prims.add(f.attr)
                elif f.attr == "save" and recv not in (*SAVE_NOT_THE_LIBRARY,
                                                       "self"):
                    prims.add("save")
                elif f.attr == "move" and recv == "shutil":
                    prims.add("shutil.move")
                elif f.attr == "rename":
                    prims.add("rename")
                if recv in imps[mod]:
                    base, name = imps[mod][recv]
                    callees.add((f"{base}.{name}", f.attr))
                    callees.add((base, f"{name}.{f.attr}"))
                if recv and recv[:1].isupper():
                    callees.add((mod, f"{recv}.{f.attr}"))
        return prims, callees

    table = {k: direct(k[0], v) for k, v in funcs.items()}
    memo: dict = {}

    def reach(key, stack=()):
        if key in memo:
            return memo[key]
        if key in stack or key not in table:
            return set()
        prims, callees = table[key]
        out = set(prims)
        for c in callees:
            out |= reach(c, stack + (key,))
        memo[key] = out
        return out

    found = {}
    for m in UI_MODULES:
        mod = m[:-3].replace("/", ".")
        for _alias, (base, name) in imps.get(mod, {}).items():
            if base.split(".")[0] in ("ui", "__future__") or base not in trees:
                continue
            hit = reach((base, name))
            if hit:
                found[(base, name)] = hit
    return found
