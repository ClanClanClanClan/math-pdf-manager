"""Canonical capitalisation of name particles in the AUTHOR BLOCK.

A particle is capitalised when it is PART OF THE SURNAME and lower case
when it is a PREPOSITION.  The test is whether it can be dropped: Alexis
de Tocqueville is "Tocqueville", so "de" is a link word and stays low;
Jean-François Le Gall is never "Gall", so "Le" is part of the name and
takes a capital.  See ``config/author_surnames.yaml`` for the sourcing
and ``docs/FILENAME_CONVENTION.md`` for the rule.

WHY A LIST AND NOT A RULE.  Nationality is not recoverable from the
particle, and the particle is what a rule would have to key on.  "da
Prato" is Italian and takes a capital; "da Silva" is Portuguese and does
not.  "de Feo" and "de Vries" LOOK like the Italian and Flemish cases
that do take a capital, and both were proposed as changes and then
refuted — the people in this library are Filippo de Feo and Casper/
Martijn de Vries, who publish lower case.  A rule keyed on "da" or "de"
gets those wrong every time.

WHY THE AUTHOR BLOCK ONLY.  This repository has already shipped a fix
that reached into the author block from a title rule and rewrote the
mathematician "Makovski" to "Markovski".  The scope of a rule is part of
the rule: an author-surname authority has no business touching a title,
where the same letters are ordinary words ("de" and "van" are French and
Dutch prose, "le Monde" is a newspaper).
"""
from __future__ import annotations

import logging
import re
import unicodedata
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_CACHE: dict = {}

#: A surname is the run before ", Initial." — the same shape the library
#: uses everywhere: "Surname, I. I., Other, J. - Title.pdf".
_SURNAME = re.compile(r"(?:^|,\s)([^,]+?),\s*(?=[A-ZÀ-Þ]\.)")

_SEP = " - "


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def _config_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "author_surnames.yaml"


def _veto_path() -> Optional[Path]:
    """Where the owner's vetoes live — beside his vocabulary decisions.

    In the LIBRARY, not the repo: the authority list is researched
    knowledge that belongs in version control, but "I disagree about this
    person" is his call and must survive a checkout.
    """
    try:
        from core.config_paths import get_library_root
        from processing.title_vocab import VOCAB_DIRNAME
        return get_library_root() / VOCAB_DIRNAME / "author_surname_vetoes.json"
    except Exception:
        return None


def load_vetoes() -> set:
    """Case-folded keys the owner has switched off.  Never raises."""
    p = _veto_path()
    if p is None:
        return set()
    try:
        import json
        raw = json.loads(p.read_text(encoding="utf-8"))
        return {_nfc(str(k)).casefold() for k in (raw.get("disabled") or [])}
    except Exception:
        return set()


def set_veto(key: str, disabled: bool) -> bool:
    """Switch one ruling off (or back on).  Returns whether it changed."""
    p = _veto_path()
    if p is None:
        return False
    import json
    cur = load_vetoes()
    k = _nfc(key).casefold()
    new = set(cur)
    if disabled:
        new.add(k)
    else:
        new.discard(k)
    if new == cur:
        return False
    p.parent.mkdir(parents=True, exist_ok=True)
    from core.io import atomic_write_text
    atomic_write_text(p, json.dumps({"disabled": sorted(new)},
                                    ensure_ascii=False, indent=1))
    return True


def load_map(path: Optional[Path] = None) -> dict:
    """``{casefolded surname: canonical surname}``.  Cached on mtime.

    A missing or malformed file yields an EMPTY map, never an exception:
    the namer must keep working, and doing nothing is the safe failure
    for a rule whose only power is to rewrite people's names.
    """
    p = path or _config_path()
    try:
        mtime = p.stat().st_mtime
    except OSError:
        return {}
    key = (str(p), mtime)
    hit = _CACHE.get(key)
    if hit is not None:
        return hit
    try:
        import yaml
        raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        table = raw.get("author_surnames") or {}
        out = {}
        for k, v in table.items():
            k, v = _nfc(str(k)).strip(), _nfc(str(v)).strip()
            if k and v:
                out[k.casefold()] = v
    except Exception:
        logger.warning("author_surnames.yaml unreadable; no surname rulings applied",
                       exc_info=True)
        return {}
    _CACHE[key] = out
    return out


def active_map(path: Optional[Path] = None) -> dict:
    """The rulings actually in force — the list minus the owner's vetoes."""
    veto = load_vetoes()
    return {k: v for k, v in load_map(path).items() if k not in veto}


def canonicalise_authors(author_block: str, table: Optional[dict] = None) -> tuple[str, bool]:
    """Apply the surname authority to ONE author block.

    ``author_block`` is the part BEFORE " - ".  Returns
    ``(new_block, changed)``.
    """
    table = active_map() if table is None else table
    if not table:
        return author_block, False
    block = _nfc(author_block)
    out, last, changed = [], 0, False
    for m in _SURNAME.finditer(block):
        surname = m.group(1)
        canon = table.get(surname.casefold())
        if canon is None or canon == surname:
            continue
        a, b = m.start(1), m.end(1)
        out.append(block[last:a])
        out.append(canon)
        last = b
        changed = True
    if not changed:
        return author_block, False
    out.append(block[last:])
    return "".join(out), True


def canonicalise_filename(name: str, table: Optional[dict] = None) -> tuple[str, bool]:
    """Apply the authority to the author block of a full filename.

    A name with no ``" - "`` separator has no author block that this
    library's convention recognises, so it is returned untouched — the
    same early return ``normalize_full_name`` makes.
    """
    if _SEP not in name:
        return name, False
    author, rest = name.split(_SEP, 1)
    new_author, changed = canonicalise_authors(author, table)
    if not changed:
        return name, False
    return new_author + _SEP + rest, True
