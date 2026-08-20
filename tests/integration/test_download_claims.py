"""The downloader package's claims about its own API must be true.

WHAT USED TO BE HERE, AND WHY IT IS GONE
----------------------------------------
This file previously held five ``async def test_*`` functions that
imported ``downloader.open_access_sources`` and
``downloader.proper_downloader``.  Neither module exists anywhere in the
tree.  Every body was shaped like::

    try:
        from downloader.open_access_sources import get_open_access_sources
        ...print(...)
    except Exception as e:
        print(f"failed: {e}")
        return False
    return True

so the ImportError was caught, a message was printed where nobody reads
it, and pytest recorded "5 passed" -- for five tests that had never once
reached the code they named.  Two of them (``test_actual_downloads``,
``test_error_handling``) additionally hit arxiv.org over the live network
and wrote into a ``test_downloads/`` directory, still without asserting
anything about what came back.  All five are deleted: a deleted test is
honest, a green test that checks nothing is a lie.

WHAT REPLACES THEM
------------------
The defect underneath those five tests was not "a module is missing".
It was that nothing anywhere checked whether the download surface the
package advertises is the download surface it can actually provide.
``src/downloader/__init__.py`` builds its public API inside
``try: ... except ImportError:`` blocks, so any import failure -- a
missing module, a typo, a missing third-party dependency, a syntax error
in a submodule -- is converted into a silently absent or ``None``
attribute.  The package keeps importing cleanly and every caller
discovers the hole at runtime instead.

These two tests assert on the resulting state of the package, not on the
path taken to build it.
"""
from __future__ import annotations

import importlib

import pytest


@pytest.fixture()
def downloader_pkg():
    """A freshly imported ``downloader`` package.

    Reloaded rather than reused so the assertions see the result of the
    real import machinery, not whatever another test left in
    ``sys.modules``.
    """
    import downloader

    return importlib.reload(downloader)


def test_the_package_advertises_only_names_it_can_actually_provide(downloader_pkg):
    """``__all__`` is a promise; ``from downloader import *`` must keep it.

    The try/except construction in ``__init__.py`` extends ``__all__``
    from inside a conditional, which is exactly the shape that lets the
    advertised API and the real API drift apart.
    """
    advertised = list(downloader_pkg.__all__)
    assert advertised, "the package advertises nothing at all"

    missing = [n for n in advertised if not hasattr(downloader_pkg, n)]
    assert not missing, (
        f"__all__ promises {missing} but the module has no such attribute; "
        f"`from downloader import *` would raise AttributeError"
    )

    empty = [n for n in advertised if getattr(downloader_pkg, n) is None]
    assert not empty, (
        f"__all__ promises {empty} but they are None -- an ImportError was "
        f"swallowed and the package is advertising a hole"
    )


def test_the_doi_downloader_is_really_there_and_not_a_swallowed_importerror(
    downloader_pkg,
):
    """``DOIDownloader = None`` must never be how this package imports.

    ``__init__.py`` sets ``DOIDownloader = None`` on ImportError, so a
    broken ``doi_downloader`` module leaves ``import downloader``
    succeeding and the only working download path silently absent.  That
    is the same failure mode that let five tests for a nonexistent module
    report success.  Assert the end state: the class is present, is a
    class, and carries the entry point the package docstring advertises.
    """
    cls = getattr(downloader_pkg, "DOIDownloader", None)
    assert cls is not None, (
        "downloader.DOIDownloader is None: the import in __init__.py raised "
        "ImportError and the except branch hid it"
    )
    assert isinstance(cls, type), f"DOIDownloader is {type(cls)!r}, not a class"

    # The package docstring's usage example is `dl.download(doi, path)`.
    assert callable(getattr(cls, "download", None)), (
        "DOIDownloader has no callable .download -- the documented entry "
        "point does not exist"
    )

    # And it must be the real submodule, not a stand-in left in sys.modules.
    mod = importlib.import_module("downloader.doi_downloader")
    assert cls is mod.DOIDownloader
