"""A Streamlit stand-in faithful enough to PRESS the cockpit's buttons.

The two stubs already in ``tests/ui`` were built to check that pages
render.  Pressing a button needs more of Streamlit's real behaviour, and
each difference below once let a test pass against code that could not
work for the owner:

* A widget returns its ``value=`` / ``index=`` default, or what
  ``st.session_state[key]`` already holds, when the test does not set it
  -- not ``False`` / ``""``.  The paper editor pre-fills its name box
  through session state; a stub that ignores that renames to ``.pdf``.
* A ``disabled=True`` button cannot be pressed.  Undo is disabled until
  its "Reverse all N change(s)" box is ticked; a stub that presses it
  anyway proves a click the owner cannot make.
* A press lasts one run.  Streamlit returns True once, then False.
* ``st.rerun()`` and ``st.stop()`` end the run.  Code after them never
  executes in the real app, so it must not execute here.
* Assigning ``st.session_state[k]`` after the widget keyed ``k`` was
  drawn in the same run raises, as real Streamlit does.

Everything else (markdown, metric, toast, ...) is recorded in
``calls`` so a test can read what the owner was told.
"""
from __future__ import annotations

import re
import types
from typing import Callable


class Rerun(Exception):
    """``st.rerun()`` was called: the run ends here."""


class Stop(Exception):
    """``st.stop()`` was called: the run ends here."""


class StreamlitAPIException(Exception):
    """Raised where real Streamlit would raise."""


_PRESSABLE = {"button", "form_submit_button"}
_INERT_BOOL = {"download_button", "link_button"}


class SessionState(dict):
    """Attribute and item access, plus the widget-key write guard."""

    def __init__(self, owner):
        super().__init__()
        object.__setattr__(self, "_owner", owner)

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        try:
            del self[name]
        except KeyError:
            raise AttributeError(name)

    def __setitem__(self, key, value):
        owner = object.__getattribute__(self, "_owner")
        if owner is not None and key in owner.drawn_keys:
            raise StreamlitAPIException(
                f"st.session_state.{key} cannot be modified after the widget "
                f"with key {key} is instantiated.")
        super().__setitem__(key, value)


class _Element:
    """A column / container / expander / status / empty slot."""

    def __init__(self, st: "StreamlitDouble"):
        self._st = st

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def __iter__(self):
        return iter([])

    def __call__(self, *a, **kw):
        self._st.calls.append(("<call>", a, kw))
        return _Element(self._st)

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return self._st._widget(name)


class StreamlitDouble(types.ModuleType):
    """Install as ``sys.modules['streamlit']`` before importing the cockpit."""

    def __init__(self):
        super().__init__("streamlit")
        self.calls: list = []
        self.values: dict = {}           # widget key/label -> value
        self._presses: list = []         # one-shot press matchers
        self.pressed: list = []          # keys/labels actually pressed
        self.drawn_keys: set = set()
        self.armed = False               # rerun/stop raise only when armed
        self.session_state = SessionState(self)

    # -- what a test does ------------------------------------------------
    def press(self, *matchers) -> None:
        """Press, on the next run, the button whose key (or label) matches.

        A matcher is the exact key, a compiled regex (``re.compile``) or a
        predicate on the key.  Each press is used once.
        """
        self._presses.extend(matchers)

    def set(self, **values) -> None:
        self.values.update(values)

    def run(self, fn: Callable, *args, **kwargs) -> str:
        """Run one page the way Streamlit does: until it ends or reruns.

        Returns ``"done"``, ``"rerun"`` or ``"stop"``.
        """
        self.drawn_keys = set()
        self.armed = True
        try:
            fn(*args, **kwargs)
            return "done"
        except Rerun:
            return "rerun"
        except Stop:
            return "stop"
        finally:
            self.armed = False
            self.drawn_keys = set()

    def unused_presses(self) -> list:
        return list(self._presses)

    # -- streamlit API ---------------------------------------------------
    def cache_data(self, *args, **kwargs):
        def _wrap(fn):
            fn.clear = lambda *a, **k: None
            return fn
        if len(args) == 1 and callable(args[0]) and not kwargs:
            return _wrap(args[0])
        return _wrap

    cache_resource = cache_data

    def rerun(self, *a, **kw):
        self.calls.append(("rerun", a, kw))
        if self.armed:
            raise Rerun()

    def stop(self, *a, **kw):
        self.calls.append(("stop", a, kw))
        if self.armed:
            raise Stop()

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        if name == "sidebar":
            return _Element(self)
        return self._widget(name)

    # -- widgets ---------------------------------------------------------
    def _take_press(self, key, label) -> bool:
        for i, m in enumerate(self._presses):
            for cand in (key, label):
                if cand is None:
                    continue
                if isinstance(m, re.Pattern):
                    hit = bool(m.search(str(cand)))
                elif callable(m):
                    hit = bool(m(str(cand)))
                else:
                    hit = m == cand
                if hit:
                    del self._presses[i]
                    self.pressed.append(cand)
                    return True
        return False

    def _value(self, key, label, default):
        for cand in (key, label):
            if cand is not None and cand in self.values:
                return self.values[cand]
        if key is not None and key in self.session_state:
            return self.session_state[key]
        return default

    def _widget(self, name: str):
        def _call(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            label = args[0] if args and isinstance(args[0], str) else kwargs.get("label")
            key = kwargs.get("key")
            if name == "columns":
                spec = args[0] if args else kwargs.get("spec", 1)
                n = spec if isinstance(spec, int) else len(spec)
                return [_Element(self) for _ in range(n)]
            if name == "tabs":
                return [_Element(self) for _ in (args[0] if args else [])]
            if name in _PRESSABLE:
                if kwargs.get("disabled"):
                    return False
                return self._take_press(key, label)
            if name in _INERT_BOOL:
                return False
            out = self._default(name, args, kwargs)
            if out is _NOT_A_WIDGET:
                return _Element(self)
            value = self._value(key, label, out)
            if key is not None:
                dict.__setitem__(self.session_state, key, value)
                self.drawn_keys.add(key)
            return value
        return _call

    def _default(self, name, args, kwargs):
        def arg(i, kw, default=None):
            if kw in kwargs:
                return kwargs[kw]
            return args[i] if len(args) > i else default
        if name in ("checkbox", "toggle"):
            return bool(arg(1, "value", False))
        if name in ("text_input", "text_area"):
            v = arg(1, "value", "")
            return "" if v is None else v
        if name == "number_input":
            v = kwargs.get("value", None)
            if v is None:
                v = kwargs.get("min_value", 0)
            return v
        if name == "slider":
            return arg(3, "value", arg(1, "min_value", None))
        if name in ("selectbox", "radio"):
            opts = list(arg(1, "options", []) or [])
            idx = kwargs.get("index", 0)
            return opts[idx] if opts and idx is not None else None
        if name == "multiselect":
            return list(arg(2, "default", []) or [])
        if name == "file_uploader":
            return [] if kwargs.get("accept_multiple_files") else None
        return _NOT_A_WIDGET


_NOT_A_WIDGET = object()


def said(st: StreamlitDouble, *kinds: str) -> str:
    """Every string the given kinds of element showed, one per line."""
    out = []
    for name, args, kwargs in st.calls:
        if kinds and name not in kinds:
            continue
        for v in list(args) + list(kwargs.values()):
            if isinstance(v, str):
                out.append(v)
    return "\n".join(out)
