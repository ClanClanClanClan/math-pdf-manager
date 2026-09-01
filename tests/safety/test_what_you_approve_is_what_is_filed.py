"""The Sort Queue must file the name it shows.

REPORTED, and the sharpest form of "it drops capitals systematically":
the editable box showed one filename and the disk received another. An
audit measured 40 real inbox PDFs through the real path — **20 differed,
by case alone**:

    shown  "Chen, J., Glasserman, P. - Do LLMs Understand Limit Order
            Book Dynamics?.pdf"
    filed  "Chen, J., Glasserman, P. - Do LLMs Understand limit order
            book dynamics?.pdf"

    shown  "... Dynamic Incentive Design in Large Populations, A Mean
            Field Game Approach ..."
    filed  "... Dynamic incentive design in large Populations, A mean
            field game approach ..."

Note the second: some capitals dropped, the adjacent ones kept. That
half-cased result is what makes the behaviour feel arbitrary.

THE MECHANISM. ingest_paper documents canonical_override as "use this
filename verbatim ... to honour user edits", then ran
normalize_full_name over it anyway, re-casing the title AFTER approval.

THE FIX IS TWO-SIDED, and neither half works alone. The box now pre-fills
with the NORMALISED name, so approving unedited files exactly what is
shown and the default outcome is unchanged; and the override is honoured
verbatim, so an edit survives.
"""
import pytest

from processing.move_normalizer import normalize_full_name


def _lib():
    """The library root, from the config accessor rather than a literal.

    tests/safety/test_no_test_touches_the_real_world.py rejects a test tree
    that names the owner's real path, and it was right to reject the first
    draft of this file. The caser needs the library's corpus to decide a
    word, so there is no tmp_path substitute — but the PATH may still come
    from the one accessor that owns it.
    """
    from core.config_paths import get_library_root
    return get_library_root()


@pytest.mark.parametrize("typed", [
    "Chen, J., Glasserman, P. - Do LLMs Understand Limit Order Book Dynamics?.pdf",
    "Smith, J. - Brownian Motion and the Markov Property in Finance.pdf",
    "Smith, J. - Dynamic Incentive Design in Large Populations.pdf",
])
def test_the_prefilled_name_is_a_fixed_point_of_the_caser(typed):
    """What the box shows must survive being filed.

    The box pre-fills with normalize_full_name(...), so normalising it a
    second time must change nothing. If it does not hold, the box is
    showing a name the disk will not receive — the original bug.
    """
    lib = _lib()
    shown, _, _ = normalize_full_name(typed, lib)
    again, changed, _ = normalize_full_name(shown, lib)
    assert again == shown, (
        f"the name shown in the box is not stable under the caser:\n"
        f"  shown {shown!r}\n  filed {again!r}"
    )


def test_the_override_is_taken_verbatim_by_ingest():
    """The contract ingest_paper's own docstring states.

    Asserted at source level: exercising ingest_paper needs a real PDF and
    a writable library, and this repository does not write to the library
    under any circumstances.
    """
    import pathlib
    src = pathlib.Path("src/processing/ingest.py").read_text()
    i = src.index("normalize_full_name(\n                canonical_name, library_root)")
    window = src[max(0, i - 900):i]
    assert "if canonical_override:" in window, (
        "ingest_paper must skip the caser when the caller supplied the "
        "name — its docstring promises the override is used verbatim"
    )


def test_the_cockpit_prefills_the_normalised_name():
    """The other half. Without it, honouring the override changes the
    default outcome for everyone who never edits the box."""
    import pathlib
    src = pathlib.Path("src/ui/cockpit.py").read_text()
    i = src.index('edited_name = st.text_input(')
    window = src[max(0, i - 700):i]
    assert "normalize_full_name" in window, (
        "the Sort Queue box must show the name that will actually be filed"
    )
