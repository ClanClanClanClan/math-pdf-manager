#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/sentence_case.py - Academic Title Sentence Case Conversion
Extracted from utils.py to improve modularity

This module handles the complex logic for converting academic titles to proper sentence case
while preserving technical terms, mathematical expressions, and proper nouns.
"""

import os
import unicodedata
from typing import Iterable, Tuple, Set, Optional, Dict
import regex as re

from .io import load_yaml_config, debug_print
from .math_tokenization import robust_tokenize_with_math, DASH_CHARS

# Constants for sentence case processing
MATH_TECHNICAL_PREFIXES = {
    # Lowercase Latin letters often used as technical prefixes
    "g", "h", "l", "f", "c", "k", "p", "q", "r", "s", "t", "w", "v", "u", "x", "y", "z",
    "l^2", "l^p", "c_0", "l_infty", "l^infty", "h-process", "g-expectation", "c_0-sequence",
    # Lowercase Greek technical terms (Unicode)
    "α", "β", "γ", "δ", "ε", "ζ", "η", "θ", "ι", "κ", "λ", "μ", "ν", "ξ", "ο", "π", "ρ",
    "σ", "τ", "υ", "φ", "χ", "ψ", "ω",
    # Common single Greek letter prefixes for chemistry/biology
    "α-synuclein", "ω-automata"
}

# Number to word conversion for sentence starts
NUMBERS = {
    '0': 'zero', '1': 'one', '2': 'two', '3': 'three', '4': 'four', 
    '5': 'five', '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine', 
    '10': 'ten', '11': 'eleven', '12': 'twelve', '13': 'thirteen', 
    '14': 'fourteen', '15': 'fifteen', '16': 'sixteen', '17': 'seventeen', 
    '18': 'eighteen', '19': 'nineteen', '20': 'twenty'
}

# Module-level config cache
_CONFIG_CACHE = {}

# Debug mode flag
DEBUG_SENTENCE_CASE = False


def _load_sentence_case_config() -> Dict:
    """Load configuration for sentence case conversion.

    Uses :mod:`core.config_paths` so paths are always resolved relative to
    the project root (not cwd). This means the validator (called via
    ``check_filename``) and the canonical-filename generator (CMO) both load
    the same config files regardless of where Python is invoked from.
    """
    global _CONFIG_CACHE

    if _CONFIG_CACHE:
        return _CONFIG_CACHE

    try:
        from core.config_paths import config_path, load_set_from_files, load_yaml_section
    except ImportError:
        # core/ should always be importable, but guard anyway
        config_path = lambda *a, **kw: None
        load_set_from_files = lambda *files: set()
        load_yaml_section = lambda *keys, filename="config.yaml": None

    cfg_path = config_path("config.yaml")
    config_data: Dict = {}
    if cfg_path is not None:
        try:
            config_data = load_yaml_config(str(cfg_path)) or {}
            debug_print(f"Loaded config from: {cfg_path}")
        except Exception as exc:
            debug_print(f"Failed to load config from {cfg_path}: {exc}")
    else:
        debug_print("No config file found, using minimal defaults")

    # Capitalization whitelist may live at top level or under exceptions/.
    cap_wl = (
        config_data.get("capitalization_whitelist")
        or config_data.get("exceptions", {}).get("capitalization_whitelist")
        or []
    )

    # Initialize with config data or minimal defaults
    _CONFIG_CACHE = {
        'common_acronyms': frozenset(config_data.get('common_acronyms', [])),
        'mixed_case_words': frozenset(config_data.get('mixed_case_words', [
            'LaTeX', 'macOS', 'iOS', 'iPhone', 'iPad', 'iPod', 'eBay',
            'PyTorch', 'TensorFlow', 'JavaScript', 'TypeScript', 'CoffeeScript',
            'XeLaTeX', 'LuaTeX', 'ConTeXt', 'BibTeX', 'PostScript', 'FaceTime',
            'GitHub', 'GitLab', 'LinkedIn', 'YouTube'
        ])),
        'compound_terms': frozenset(config_data.get('compound_terms', [])),
        'proper_adjectives': frozenset(config_data.get('proper_adjectives', [
            'Bayesian', 'Gaussian', 'Markovian', 'Newtonian', 'Euclidean', 'Laplacian'
        ])),
        'capitalization_whitelist': frozenset(cap_wl),
        'name_dash_whitelist': frozenset(load_set_from_files("name_dash_whitelist.txt")),
        'known_words': frozenset(),  # caller may populate from data files
    }

    if _CONFIG_CACHE['name_dash_whitelist']:
        debug_print(
            f"Loaded {len(_CONFIG_CACHE['name_dash_whitelist'])} name-dash whitelist entries"
        )

    # Add math technical prefixes to the config
    _CONFIG_CACHE['math_technical_prefixes'] = MATH_TECHNICAL_PREFIXES

    debug_print(f"Loaded config: {len(_CONFIG_CACHE)} sections")
    return _CONFIG_CACHE


def extract_title_words(title: str) -> Set[str]:
    """Extract all words from title for filtering whitelist terms."""
    words = set()
    
    # Extract individual words (letters, numbers, apostrophes)
    for match in re.finditer(r"\b\w+(?:[''][a-zA-Z]+)?\b", title, re.U):
        full = match.group().lower()
        words.add(full)
        # Also add the base word without possessive suffix so that
        # whitelist terms like "Euler" match title words like "Euler's"
        for poss in ("\u2019s", "'s"):
            if full.endswith(poss):
                words.add(full[:-2])
                break
    
    # Extract compound terms with dashes
    for match in re.finditer(rf"\b\w+(?:[{DASH_CHARS}]\w+)+\b", title, re.U):
        compound = match.group().lower()
        words.add(compound)
        # Also add normalized versions
        words.add(compound.replace('–', '-').replace('—', '-').replace('−', '-'))
    
    # Extract space-separated phrases (up to 3 words)
    # First extract all word positions
    word_matches = list(re.finditer(r"\b\w+\b", title, re.U))
    
    # Extract 2-word phrases
    for i in range(len(word_matches) - 1):
        phrase = f"{word_matches[i].group()} {word_matches[i+1].group()}".lower()
        words.add(phrase)
    
    # Extract 3-word phrases
    for i in range(len(word_matches) - 2):
        phrase = f"{word_matches[i].group()} {word_matches[i+1].group()} {word_matches[i+2].group()}".lower()
        words.add(phrase)
    
    debug_print(f"Extracted {len(words)} words from title")
    return words


def filter_relevant_whitelist_terms(
    title: str,
    capitalization_whitelist: Optional[Iterable[str]] = None,
    name_dash_whitelist: Optional[Iterable[str]] = None,
    technical_prefix_whitelist: Optional[Iterable[str]] = None,
) -> Tuple[Set[str], Set[str], Set[str]]:
    """
    Filter whitelist terms to only include those relevant to the title.
    This optimization significantly improves performance for large whitelists.
    """
    debug_print(f"Filtering whitelist terms for title: '{title}'")
    
    # Extract all possible words and phrases from the title
    title_words = extract_title_words(title)
    
    # Filter capitalization whitelist
    filtered_cap = set()
    for term in capitalization_whitelist or []:
        term_lower = term.lower()
        debug_print(f"  Checking cap term: '{term}' -> '{term_lower}'")
        if term_lower in title_words:
            debug_print("      -> relevant (exact match)")
            filtered_cap.add(term)
        # Match with dash normalization
        normalized = term_lower.replace('–', '-').replace('—', '-').replace('−', '-')
        if normalized in title_words:
            debug_print("      -> relevant (normalized dash match)")
            filtered_cap.add(term)
        # Match individual words in compound terms
        if any(dash in term_lower for dash in ['-', '–', '—', '−']):
            parts = re.split(rf'[{DASH_CHARS}]+', term_lower)
            if all(part in title_words for part in parts if part):
                debug_print("      -> relevant (compound word parts match)")
                filtered_cap.add(term)
        # Match space-separated terms
        if ' ' in term_lower:
            if term_lower in title_words:
                debug_print("      -> relevant (space-separated match)")
                filtered_cap.add(term)
    
    # Filter name dash whitelist
    filtered_dash = set()
    for term in name_dash_whitelist or []:
        term_lower = term.lower()
        if term_lower in title_words:
            filtered_dash.add(term)
        # Match with dash normalization
        normalized = term_lower.replace('–', '-').replace('—', '-').replace('−', '-')
        if normalized in title_words:
            filtered_dash.add(term)
    
    # Filter technical prefix whitelist
    filtered_tech = set()
    for term in technical_prefix_whitelist or []:
        term_lower = term.lower()
        if term_lower in title_words:
            filtered_tech.add(term)
        # Check if title starts with this technical prefix
        if title.lower().startswith(term_lower):
            filtered_tech.add(term)
    
    debug_print(f"    filtered_cap: {len(filtered_cap)} terms")
    debug_print(f"    filtered_dash: {len(filtered_dash)} terms")
    debug_print(f"    filtered_tech: {len(filtered_tech)} terms")
    
    return filtered_cap, filtered_dash, filtered_tech


#: The two apostrophes this library's titles actually use: U+0027 and U+2019.
#: They must be treated identically -- the same construct spelled two ways
#: cannot be allowed to case differently.
APOSTROPHES = "'\u2019"

def _apostrophe_base(word):
    """The part of *word* before its apostrophe, and the rest.

    "BSDE’s" -> ("BSDE", "’s").  A word with no apostrophe gives
    (word, "").

    WHY THIS EXISTS. Three casing checks -- known acronym, 2-3 letter
    acronym, mixed-case brand -- must look at the BASE, because "BSDE’s"
    is the acronym BSDE carrying a possessive, not a new word. The
    2-3 letter check already did this and only for U+0027, with the comment
    "For possessives, check the base word without apostrophe". The other two
    did not do it at all.

    That asymmetry stayed invisible while U+2019 split into three tokens and
    the acronym was seen on its own. The moment both apostrophes tokenise
    alike, "BSDE’s" arrives whole and the checks stop recognising it --
    which is why the obvious one-character class fix measured as a NET
    REGRESSION: 27 proposals better, 21 worse. It was not the class fix that
    was wrong, it was this.
    """
    for k, ch in enumerate(word):
        if ch in APOSTROPHES:
            return word[:k], word[k:]
    return word, ""


def _split_on_apostrophe(word):
    """("Varadhan", "'", "s") for "Varadhan's"; (word, "", "") if none."""
    for k, ch in enumerate(word):
        if ch in APOSTROPHES:
            return word[:k], ch, word[k + 1:]
    return word, "", ""


def _is_capitalised_name(head):
    """Xxxx-shaped: one capital, then lower case, at least three letters.

    ALL-CAPS is excluded on purpose -- "BSDE's" is an acronym and belongs to
    the acronym branch above, which knows about the possessive. All-lower is
    excluded too, so "don't" and "l'X"'s "l" never reach here.
    """
    if len(head) < 3 or not head.isalpha():
        return False
    return head[0].isupper() and head[1:].islower()


def _is_short_lower_tail(tail):
    """A possessive or a transliterated soft sign: 's, 'sche, 'ev, 'son."""
    return 1 <= len(tail) <= 4 and tail.isalpha() and tail.islower()


def _proper_noun_after_apostrophe(word, prev_token=None):
    """The capital after an apostrophe, when it must survive lowercasing.

    MEASURED over the 25,049 in-scope library titles. An apostrophe is
    followed by a capital in 111 places, and they fall into four kinds --
    every one of which is a name or a title and must keep its capital:

        d'Azéma, d'Itô, d'Euler, d'Alembert, l'Hôpital   82 + 17
            French elision. The "d'" or "l'" is a preposition and belongs
            in lower case; the capital belongs to the MATHEMATICIAN.
        'Choose your opponent', 'Finem Lauda', 'Tis, 'The, 'Jacques    5
            an opening quote, and the capital starts the quoted title.
        l'X (École Polytechnique), d'A. Garsia, 'N                     4
            a single capital that is still an abbreviation or an initial.
        d'EDP, d'EDS                                                   3
            French acronyms.

    Before this guard, 98 of those 108 titles were damaged: "Calcul d'Itô"
    became "Calcul d'itô", "Deux théorèmes d'Abel" became "d'abel", and
    "théorie d'Iwasawa" became "d'iwasawa".

    THE ONE EXCEPTION is the English possessive: "THE AUTHOR'S THEOREM"
    lowercases to "the author's theorem", and preserving that S would give
    "author'S". A lone S is therefore not treated as a name. Measured: this
    library contains no "'S" at all and no all-capitals title, so the
    exception fires nowhere today -- it is here because ingest takes titles
    from Crossref and arXiv, not because the library needed it.

    Returns the string to emit, or None to fall through to normal casing.
    """
    head, sep, tail = _split_on_apostrophe(word)

    # Case 1: the apostrophe is INSIDE this token, and a CAPITAL follows it
    # -- "d'Itô", "l'Hôpital", "'Tis". The head is an elided article or a
    # quote mark and belongs in lower case; the capital belongs to the name.
    if sep and tail[:1].isupper():
        if tail.upper() == "S":
            return None                           # English possessive
        return head.lower() + sep + tail

    # Case 1b: a CAPITALISED head carrying a possessive -- "Varadhan's",
    # "König's", "Solov’ev". In a mathematics library this construct is an
    # EPONYM: a possessive attaches to a person, and a common noun would
    # already be lower case ("the author's"). MEASURED over the 25,049
    # in-scope titles: 702 occurrences of the shape, of which 547 were
    # already preserved because the name happens to sit in the
    # capitalisation whitelist and 154 were being LOWERCASED --
    # könig's, varadhan's, zvonkin's, gronwall's, yosida's, alekseev's,
    # tsirel'son, and possamaï's, the owner's own name.
    #
    # Of the 122 distinct words this rule preserves, 121 are surnames
    # (Abel, Cramér, Doeblin, Fermat, Krein, Sanov, Sklar, Zermelo ...).
    # The single exception measured is "Planner’s advices" in one economics
    # title, where "planner" is a common noun -- so the rule trades one mild
    # over-capitalisation for 153 correct names. A dictionary test was
    # considered and rejected: Abel, Baker, Clark, Engel, Gross, James, Lee,
    # Root and Tong are all dictionary words AND surnames here, so a
    # dictionary would lowercase the very names this exists for.
    if sep and _is_capitalised_name(head) and _is_short_lower_tail(tail):
        return word

    # Case 2: the apostrophe is its own PUNCT token -- "d’Iwasawa" arrived
    # split while the tokeniser's WORD pattern listed U+0027 twice and
    # U+2019 never. Kept after that fix so the rule does not depend on it.
    if (prev_token is not None and prev_token.kind == 'PUNCT'
            and prev_token.value in APOSTROPHES):
        if word[:1].isupper() and word.upper() != "S":
            return word
    return None


#: Characters that join two names into one compound: the ASCII hyphen, the
#: en dash the library's convention prefers for two co-equal people
#: (Hamilton-Jacobi), and the Unicode minus a source occasionally emits.
_NAME_JOINERS = "-\u2010\u2011\u2013\u2212"

#: Lower-case particles that sit INSIDE a name and must not stop the walk
#: across a compound: "Saint-Jean-de-Monts", "de-Americanization",
#: "van der Waerden", "Le Cam". Found by mutation, not by design -- a mutant
#: that removed the lower-case guard altogether scored BETTER on two of the
#: three real titles it changed, because the guard was breaking the walk at
#: the "de" of Saint-Jean-de-Monts and stranding "Monts" in lower case.
_NAME_PARTICLES = frozenset({
    "de", "des", "du", "da", "das", "dos", "di", "del", "della", "der",
    "den", "van", "von", "ter", "te", "la", "le", "les", "el", "al",
    "bin", "ibn", "st", "ste",
})


def _in_a_name_compound(tokens, i, known):
    """Is this capitalised word part of a Xxx-Yyy compound naming people?

    "Kolmogorov-Petrowsky", "Hartman-Wintner", "Borel-Cantelli",
    "Pierre-Andre". Only ONE component needs to be a name we know.

    WHY. Preserving only the half we recognise is worse than preserving
    neither. MEASURED over the 25,043 in-scope titles: the eponym rule alone
    took the count of compounds that come out Xxx-yyy from 48 to 97 --
    "Kolmogorov-petrowsky", "Hartman-wintner", "Pierre-andre". A half-cased
    name reads as a typo in a way that a fully lower-cased one does not, and
    the second half is missing from the vocabulary only because that person
    never authored a paper in this library, or because the title misspells
    them ("Borel-Cantellu", "Lebesgue-Stieljes").

    This is the "dash compound" signal, which is UNUSABLE on its own: applied
    to any two capitals it fires on "Mean-Field", "Time-Dependent",
    "Non-Linear" and was measured at 3,029 wrong capitals on title-cased
    input. It is safe here only because both guards still apply -- at least
    one component must be a known surname, and the title-case gate still has
    to say this title is not Title Cased.
    """
    n = len(tokens)

    def _word_at(j):
        return tokens[j].value if 0 <= j < n and tokens[j].kind == 'WORD' else None

    def _joined(a, b):
        """Are tokens a and b joined by a name-joining punctuation token?"""
        if not (0 <= a < n and 0 <= b < n):
            return False
        mid = tokens[a + 1] if a + 1 == b - 1 else None
        return (mid is not None and mid.kind == 'PUNCT'
                and mid.value in _NAME_JOINERS)

    # walk left and right through the compound this word sits in
    for step, probe in ((-2, lambda j: j - 2), (2, lambda j: j + 2)):
        j = i
        while True:
            k = probe(j)
            nxt = _word_at(k)
            if nxt is None:
                break
            if not _joined(min(j, k), max(j, k)):
                break
            if not nxt[:1].isupper():
                # A lower-case particle is part of the name, not the end of
                # it: Saint-Jean-de-Monts, de-Americanization. Anything else
                # in lower case ends the compound.
                if nxt.lower() in _NAME_PARTICLES:
                    j = k
                    continue
                break
            if nxt.lower() in known:
                return True
            j = k
    return False


def _title_is_title_cased(tokens, i_stop=None):
    """Is this title Title Cased, i.e. is every word's capital meaningless?

    Returns True (title-cased), False (not), or None (too short to judge).

    WHY A GATE IS NEEDED AT ALL. The eponym rule below preserves a capital on
    any word the library knows as an author surname. On a sentence-cased title
    that is what we want. On a TITLE-CASED one -- "A Study Of The Wang
    Equation In Sun Space" -- every word carries a capital, removing them is
    the caser's whole job, and the rule would keep every surname-shaped word
    it met.

    MEASURED, on an oracle of 4,000 titles the library stores in sentence case,
    Title-Cased back and fed in with the stored title as ground truth:

        baseline                      3,763 / 4,000 exact, 193 wrong capitals
        the rule with NO gate         3,179 / 4,000,       997 wrong  (+804)
        the rule with THIS gate       3,763 / 4,000,       193 wrong    (+0)

    The +804 is the collision made visible: `risk` 205, `de` 147, `law` 60,
    `price` 53, `case` 42 -- all genuine mined surnames, all ordinary words.

    THE SECOND CLAUSE, "at least two capitals that are NOT surnames", is not
    decoration. Without it the detector called "Euler, Pisot, Prouhet-Thue-
    Morse, Wallis and the duplication of sines" title-cased -- a title whose
    capitals are ALL names -- and blocked 29 correct recoveries. With it, 31
    of 25,049 titles read as title-cased and only 12 recoveries are blocked.

    Thresholds (0.70, 3, 2) were grid-searched over 0.6/0.7/0.8 x 3/5/6 on this
    corpus. They are the best of what was tried, not proven optimal; 0.8/min-6
    recovers 6 more and costs 113 title-cased errors, so the surface is not
    flat. Re-measure if the mined vocabulary changes materially.
    """
    from processing.casing_vocabulary import preserved
    known = preserved()
    content = []
    for j, tok in enumerate(tokens):
        if tok.kind != 'WORD' or not tok.value[:1].isalpha():
            continue
        if j == 0:                       # the title's own first word is always
            continue                     # capitalised and carries no signal
        content.append(tok.value)
    if len(content) < 3:
        return None
    caps = [w for w in content if w[:1].isupper()]
    if len(caps) / len(content) < 0.70:
        return False
    non_name_caps = [w for w in caps if w.lower() not in known]
    return len(non_name_caps) >= 2


def to_sentence_case_academic(
    title: str,
    capitalization_whitelist: Optional[Iterable[str]] = None,
    name_dash_whitelist: Optional[Iterable[str]] = None,
    known_words: Optional[Iterable[str]] = None,
    technical_prefix_whitelist: Optional[Iterable[str]] = None,
    debug: bool = False,
) -> Tuple[str, bool]:
    """
    Convert title to academic sentence case.
    
    Rules:
    - First word is capitalized (unless technical prefix)
    - All other words are lowercase except:
      - Whitelisted terms (preserved exactly)
      - Short acronyms (2-4 letters, all caps)
      - Mixed-case brands (iPhone, eBay)
      - Proper adjectives (Bayesian, Gaussian, etc.)
    - Technical prefixes like "g-expectation" stay lowercase even when first
    - Context-aware contractions: "It's" stays as pronoun, not "IT" acronym
    
    Performance optimization: Automatically filters whitelists to only relevant terms.
    """
    global DEBUG_SENTENCE_CASE
    old_debug = DEBUG_SENTENCE_CASE
    if debug:
        DEBUG_SENTENCE_CASE = True
    
    try:
        debug_print("=== to_sentence_case_academic ===")
        debug_print(f"Input title: '{title}'")
        
        if not title or not title.strip():
            debug_print("Empty title, returning 'X'")
            return "X", True
        
        
        # Load configuration
        config = _load_sentence_case_config()
        
        # Use provided whitelists or fall back to config
        cap_whitelist = set(capitalization_whitelist or config.get('capitalization_whitelist', []))
        dash_whitelist = set(name_dash_whitelist or config.get('name_dash_whitelist', []))
        tech_whitelist = set(technical_prefix_whitelist or config.get('math_technical_prefixes', []))
        
        # Filter whitelists to only relevant terms (performance optimization)
        filtered_cap, filtered_dash, filtered_tech = filter_relevant_whitelist_terms(
            title, cap_whitelist, dash_whitelist, tech_whitelist
        )
        
        # Tokenize with math protection
        tokens = robust_tokenize_with_math(title, filtered_cap | filtered_dash)
        
        # Check for edge cases after tokenization
        word_tokens = [token for token in tokens if token.kind == 'WORD']
        
        # If no word tokens, handle special cases
        if not word_tokens:
            # A title with no WORD tokens is not necessarily an empty title.
            # It is usually a title that is ENTIRELY mathematics or entirely
            # one whitelisted phrase -- and those need no case change at all,
            # because every character in them is already protected.
            #
            # Falling through to "X" here DESTROYED three real library titles:
            # "F-processes" and "G-expectations" tokenise as a single PHRASE
            # (both are in the capitalisation whitelist) and "Freefem++" as a
            # single MATH token, and all three came back as the one character
            # "X". "L^2" did too. The bug predates the maths-detector work and
            # gets worse the better the detector is, because a more accurate
            # detector claims MORE titles whole.
            keeps = [t for t in tokens if t.kind in ('MATH', 'PHRASE')]
            if keeps:
                return title, False
            # Check if it's punctuation only
            punct_tokens = [token for token in tokens if token.kind == 'PUNCT']
            if punct_tokens:
                # Punctuation only gets X prefix
                result = "X " + ''.join(token.value for token in tokens)
                return result, True
            else:
                # Genuinely nothing to case: no words, no maths, no phrase,
                # no punctuation. This is the only "X" that means "empty".
                return "X", True
        
        # Handle emoji/punctuation stripping at the beginning
        # If title starts with emoji/punctuation followed by words, strip leading punctuation
        if (len(tokens) > 0 and tokens[0].kind == 'PUNCT' and 
            any(token.kind == 'WORD' for token in tokens)):
            # Is the leading token really an EMOJI, or just punctuation that
            # happens not to be ASCII?
            #
            # This used to ask `ord(first_punct[0]) > 127`, and deleted the
            # character outright when it was true. That is not an emoji test,
            # it is a "not ASCII" test, and it silently destroyed three real
            # library titles:
            #
            #   “Choose your opponent”, a new knockout design ...
            #   “Lion-Man” and the fixed point property
            #        -- the OPENING quote deleted, the closing one left
            #           behind, so the title came out unbalanced
            #   …And justice for all!
            #        -- the ellipsis deleted, which is the whole title
            #
            # Unicode already distinguishes these. Emoji and pictographs are
            # category So (Symbol, other); quotation marks are Pi/Pf and the
            # ellipsis is Po. Punctuation the author typed on purpose is not
            # ours to remove.
            first_punct = tokens[0].value
            if unicodedata.category(first_punct[0]) == 'So':
                # Strip leading emoji and spaces
                new_tokens = []
                skip_leading = True
                for token in tokens:
                    if skip_leading and token.kind in ['PUNCT', 'SPACE']:
                        continue
                    else:
                        skip_leading = False
                        new_tokens.append(token)
                tokens = new_tokens
        
        # Convert to sentence case
        result_parts = []
        changed = False
        
        for i, token in enumerate(tokens):
            if token.kind == 'MATH':
                # Preserve math exactly
                result_parts.append(token.value)
                continue
            elif token.kind == 'PHRASE':
                # Check if phrase has whitelist match
                phrase = token.value
                exact_match = None
                matched_via_dash_norm = False
                # The whitelist holds CASE VARIANTS of the same term (both
                # "G-expectation" and "g-expectation"), so several entries can
                # match one phrase case-insensitively while this loop keeps
                # only the first.  Raw set order depends on PYTHONHASHSEED, so
                # the winning spelling differed BETWEEN PROCESSES — a rename
                # preview and the later apply could disagree.  Fix: prefer the
                # entry matching the author's OWN spelling exactly, then fall
                # back to a sorted (reproducible) case-insensitive search.
                candidates = sorted(filtered_cap | filtered_dash)
                if phrase in candidates:
                    exact_match = phrase
                for term in [] if exact_match else candidates:
                    if phrase.lower() == term.lower():
                        exact_match = term
                        break
                    # Check with dash normalization
                    phrase_normalized = phrase.replace('\u2013', '-').replace('\u2014', '-').replace('\u2212', '-')
                    term_normalized = term.replace('\u2013', '-').replace('\u2014', '-').replace('\u2212', '-')
                    if phrase_normalized.lower() == term_normalized.lower():
                        exact_match = term
                        matched_via_dash_norm = True
                        break

                # A whitelist entry does not preserve a capital, it IMPOSES
                # one: matching is case-insensitive and the entry's own
                # spelling is emitted. That is useful for "Ito" -> "Itô" and
                # wrong for a word this library writes in lower case.
                #
                # MEASURED on the shipped 848-entry list: five bare entries
                # impose 267 wrong capitals between them. "Le" turns "sur le
                # grossissement" into "sur Le grossissement" 131 times (the
                # entry is presumably meant for Le Cam and Le Gall);
                # "posedness" turns "well-posedness" into "well-Posedness"
                # 86 times; then White 23, Bank 18, Hold 9.
                #
                # So an entry may not overrule the library's own usage. This
                # only ever blocks an entry from RAISING a lower-case word --
                # a phrase that is already capitalised is untouched, and no
                # entry loses its ability to fix spelling or dashes.
                # ... but ONLY for a single-word entry. A MULTI-WORD phrase is
                # specific enough that it cannot collide with ordinary prose --
                # that is the whole reason institution names are written as
                # phrases. Guarding them too blocked "the university of
                # Durham" and "national university of Kyiv" from ever being
                # raised, because "university" is a common word on its own
                # (2 capitalised against 32) and the guard only looked at the
                # first token.
                if (exact_match and phrase[:1].islower()
                        and len(phrase.split()) == 1):
                    try:
                        from processing.casing_vocabulary import is_common
                        if is_common(phrase):
                            exact_match = None
                    except Exception:            # never take the page down
                        pass

                if exact_match:
                    if matched_via_dash_norm:
                        # Apply the whitelist's EXACT form: both the
                        # capitalisation AND the dash characters.  The
                        # whitelist is authoritative — if it says en-dash,
                        # the output uses en-dash regardless of the input.
                        out_chars = []
                        ti = 0  # index into exact_match (whitelist term)
                        for pc in phrase:
                            if pc in '-\u2013\u2014\u2212':
                                # Use the dash character from the WHITELIST
                                while ti < len(exact_match) and exact_match[ti] not in '-\u2013\u2014\u2212':
                                    ti += 1
                                if ti < len(exact_match):
                                    out_chars.append(exact_match[ti])
                                    ti += 1
                                else:
                                    out_chars.append(pc)
                            else:
                                if ti < len(exact_match):
                                    # Apply case from whitelist term
                                    wc = exact_match[ti]
                                    if wc.isupper():
                                        out_chars.append(pc.upper())
                                    elif wc.islower():
                                        out_chars.append(pc.lower())
                                    else:
                                        out_chars.append(pc)
                                    ti += 1
                                else:
                                    out_chars.append(pc)
                        replacement = ''.join(out_chars)
                    else:
                        replacement = exact_match
                    result_parts.append(replacement)
                    if phrase != replacement:
                        changed = True
                else:
                    # No whitelist match, preserve exactly
                    result_parts.append(phrase)
                continue
            elif token.kind == 'WORD':
                # Process regular words
                word = token.value
                
                # Check if it's a technical prefix (should stay lowercase even if first)
                if word.lower() in filtered_tech:
                    result_parts.append(word.lower())
                    if word != word.lower():
                        changed = True
                    continue
                
                # Strip possessive suffix for whitelist comparison
                # e.g. "Euler's" → base "Euler", suffix "'s"
                possessive_suffix = ""
                word_base = word
                for poss in ("\u2019s", "'s"):  # curly then straight apostrophe
                    if word.endswith(poss):
                        possessive_suffix = word[-2:]
                        word_base = word[:-2]
                        break

                # Check exact whitelist matches (using base form for possessives)
                exact_match = None
                candidates = sorted(filtered_cap | filtered_dash)   # see above
                if word_base in candidates:
                    exact_match = word_base
                for term in [] if exact_match else candidates:
                    if word_base.lower() == term.lower():
                        exact_match = term
                        break

                # Same guard as in the phrase branch above: a whitelist entry
                # may not IMPOSE a capital on a word this library writes in
                # lower case. "Le" alone accounts for 131 of the 267.
                if exact_match and word[:1].islower():
                    try:
                        from processing.casing_vocabulary import is_common
                        if is_common(word):
                            exact_match = None
                    except Exception:            # never take the page down
                        pass

                if exact_match:
                    result_parts.append(exact_match + possessive_suffix)
                    if word != exact_match + possessive_suffix:
                        changed = True
                    continue
                
                # Check if it's a known acronym (check before sentence start to preserve acronyms)
                _base, _suffix = _apostrophe_base(word)
                if word in config.get('common_acronyms', []):
                    result_parts.append(word)
                    continue
                if _suffix and _base in config.get('common_acronyms', []):
                    result_parts.append(_base + _suffix)   # BSDE’s
                    continue
                
                # Check if it's a likely acronym (2-3 letters, all caps, not pronouns or common words)
                # For possessives, check the base word without apostrophe
                base_word = _base
                if (2 <= len(base_word) <= 3 and base_word.isupper() and 
                    base_word not in ['IT', 'HE', 'SHE', 'WE', 'YOU', 'THE', 'AND', 'FOR', 'BUT', 'NOT', 'FOX', 'DOG', 'CAT', 'OF', 'TO', 'IN', 'ON', 'AT', 'BY', 'OR', 'SO', 'UP', 'IF', 'AS', 'MY', 'NO', 'GO', 'DO', 'BE', 'AM', 'IS', 'WAS', 'ARE']):
                    result_parts.append(word)
                    continue
                
                # Check if it's a mixed-case brand (before sentence start check)
                if word in config.get('mixed_case_words', []):
                    result_parts.append(word)
                    continue
                if _suffix and _base in config.get('mixed_case_words', []):
                    result_parts.append(_base + _suffix)   # LinkedIn’s
                    continue
                
                # Check if it's a proper adjective (before sentence start check)  
                proper_adjective_match = None
                for adj in config.get('proper_adjectives', []):
                    if word.lower() == adj.lower():
                        proper_adjective_match = adj
                        break
                        
                if proper_adjective_match:
                    result_parts.append(proper_adjective_match)
                    if word != proper_adjective_match:
                        changed = True
                    continue
                
                # Check if this is the start of a sentence (first word or after sentence-ending punctuation)
                # Also check for opening-quote context (quoted titles like: Corrigendum for "A probabilistic approach")
                _UNAMBIGUOUS_OPEN_QUOTES = {'\u201c', '\u00ab', '\u201e', '\u2018', '\u201a'}  # " « „ ' ‚
                _ALL_QUOTE_CHARS = _UNAMBIGUOUS_OPEN_QUOTES | {'"', "'"}
                is_sentence_start = False
                if i == 0:
                    # First word of the title
                    is_sentence_start = True
                elif i > 0:
                    # Check if we're after sentence-ending punctuation
                    for j in range(i - 1, -1, -1):
                        if tokens[j].kind == 'PUNCT':
                            if tokens[j].value in ['.', '!', '?', '…', ':']:
                                # Special case: check if this period is part of a section number
                                if tokens[j].value == '.':
                                    # Look for number before and after the period
                                    before_is_number = (j > 0 and tokens[j-1].kind == 'WORD' and
                                                       tokens[j-1].value.isdigit())
                                    after_is_number = (i < len(tokens) and tokens[i].kind == 'WORD' and
                                                      tokens[i].value.isdigit())
                                    if before_is_number and after_is_number:
                                        # This is likely a section number like "2.3", not a sentence end
                                        break
                                is_sentence_start = True
                                break
                        elif tokens[j].kind in ('WORD', 'MATH', 'PHRASE'):
                            # Found CONTENT before any punctuation, so this is
                            # not a sentence start.
                            #
                            # MATH and PHRASE used to be missing here, and the
                            # scan walked straight through them to whatever
                            # punctuation lay beyond. In "A remark on the
                            # 1:H-variation of the fractional Brownian motion"
                            # it passed through the MATH token "H", reached the
                            # ":" of "1:H" -- which the library writes for "/"
                            # -- read it as a sentence-ending colon, and
                            # capitalised "Variation".
                            #
                            # A mathematical token is content exactly as a word
                            # is. Whatever sits between us and the punctuation,
                            # if it is content then we are not at a sentence
                            # start.
                            break

                # Opening-quote detection: if the word is immediately after an
                # opening quotation mark that begins a quoted title (≥3 words),
                # capitalise the first word.  Short quoted spans (1–2 words)
                # like the "big" problem or the "very big" problem are
                # scare-quotes / emphasis and stay lowercase.
                # Unambiguous Unicode openers (" « „ ' ‚) are always opening.
                # For ASCII " we use adjacency: preceded by space → opening.
                _QUOTED_TITLE_MIN_WORDS = 3
                _ANY_QUOTE = _ALL_QUOTE_CHARS | {
                    '\u201d', '\u00bb', '\u2019', '\u201f', '\u201b',
                }
                if not is_sentence_start and i > 0:
                    for j in range(i - 1, -1, -1):
                        if tokens[j].kind == 'SPACE':
                            continue
                        if tokens[j].kind == 'PUNCT' and tokens[j].value in _ALL_QUOTE_CHARS:
                            qchar = tokens[j].value
                            is_opening = False
                            if qchar in _UNAMBIGUOUS_OPEN_QUOTES:
                                is_opening = True
                            elif (j > 0 and tokens[j - 1].kind == 'SPACE') or j == 0:
                                # ASCII " or ' preceded by space → opening
                                is_opening = True
                            if is_opening:
                                # Count words until the matching closing quote.
                                # Only capitalise for quoted titles (≥3 words);
                                # shorter spans are scare-quotes / emphasis.
                                words_in_quote = 0
                                found_close = False
                                for k in range(i, len(tokens)):
                                    if tokens[k].kind == 'WORD':
                                        words_in_quote += 1
                                    elif (tokens[k].kind == 'PUNCT'
                                          and tokens[k].value in _ANY_QUOTE):
                                        found_close = True
                                        break
                                if found_close and words_in_quote >= _QUOTED_TITLE_MIN_WORDS:
                                    is_sentence_start = True
                        break  # Only check the immediately preceding non-space token
                
                if is_sentence_start and word.lower() not in filtered_tech:
                    # Check if it's a number that should be converted to word
                    if word in NUMBERS:
                        new_word = NUMBERS[word].capitalize()
                        result_parts.append(new_word)
                        if word != new_word:
                            changed = True
                        continue
                    else:
                        new_word = word.capitalize()
                        result_parts.append(new_word)
                        if word != new_word:
                            changed = True
                        continue
                
                # A capital on a word the library knows as an author
                # surname is an eponym: "the Gronwall inequality", "Fock
                # space", "Bourbaki seminar". PRESERVE-ONLY -- it fires
                # only on an already-capitalised word and emits it verbatim,
                # so it cannot impose a capital, alter a character or destroy
                # a title. That is a structural guarantee, not a measurement
                # to redo when the corpus changes.
                #
                # It is deliberately NOT done by adding the names to
                # capitalization_whitelist: that mechanism matches
                # case-insensitively and emits the ENTRY's spelling, so it
                # imposes. The shipped 848-entry list already imposes 263
                # wrong capitals ("sur le grossissement" -> "sur Le
                # grossissement", 103 times); the same mechanism fed the
                # 11,779 mined surnames was measured at 5,823.
                #
                # MEASURED over the 25,049 in-scope titles: 880 capitals
                # recovered across 723 titles, 4 wrongly kept, 0 imposed,
                # 0 lost, 0 titles destroyed. docs/proper-nouns-measured.md.
                if word[:1].isupper():
                    from processing.casing_vocabulary import preserved
                    _known = preserved()
                    if (word.lower() in _known
                            or _in_a_name_compound(tokens, i, _known)):
                        if _title_is_title_cased(tokens) is not True:
                            result_parts.append(word)
                            continue

                # A capital after an apostrophe is a name, not a word to
                # lowercase: "d'Itô", "l'Hôpital", "'Tis". See
                # _proper_noun_after_apostrophe for the measured population.
                kept = _proper_noun_after_apostrophe(
                    word, tokens[i - 1] if i > 0 else None
                )
                if kept is not None:
                    result_parts.append(kept)
                    if word != kept:
                        changed = True
                    continue

                # Default: lowercase
                new_word = word.lower()
                result_parts.append(new_word)
                if word != new_word:
                    changed = True
            else:
                # Preserve spaces and punctuation
                result_parts.append(token.value)
        
        result = ''.join(result_parts)
        
        debug_print(f"Result: '{result}' (changed: {changed})")
        return result, changed
        
    finally:
        DEBUG_SENTENCE_CASE = old_debug


# Export all functions
__all__ = [
    'to_sentence_case_academic',
    'APOSTROPHES',
    'extract_title_words',
    'filter_relevant_whitelist_terms',
    'DEBUG_SENTENCE_CASE',
    'MATH_TECHNICAL_PREFIXES'
]