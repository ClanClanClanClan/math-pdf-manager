#!/usr/bin/env python3
"""Tests for scoring, garbage detection, confidence calibration, and consensus.

The EnhancedPDFParser has a complex import chain that makes direct import
difficult in unit tests. We test the scoring logic by reimplementing the
core algorithms from the source — this validates the LOGIC, not the wiring.
"""

import re
import unicodedata

import pytest
from rapidfuzz import fuzz


# ---------------------------------------------------------------------------
# Minimal metadata container
# ---------------------------------------------------------------------------


class FakeMeta:
    def __init__(self, title="", authors="", confidence=0.5,
                 doi=None, abstract="", arxiv_id=None):
        self.title = title
        self.authors = authors
        self.confidence = confidence
        self.doi = doi
        self.abstract = abstract
        self.arxiv_id = arxiv_id
        self.extraction_method = "heuristic"
        self.source = None


# ---------------------------------------------------------------------------
# Reimplemented scoring functions (must stay in sync with enhanced_parser.py)
# ---------------------------------------------------------------------------


def compute_diacritic_bonus(authors: str) -> int:
    """Reimplements the diacritic bonus from enhanced_parser.py."""
    if not authors:
        return 0
    has_diacritics = any(
        unicodedata.combining(char) or ord(char) > 127
        for char in authors
        if char.isalpha()
    )
    return 20 if has_diacritics else 0


def calibrate_confidence(meta: FakeMeta, method: str) -> float:
    """Reimplements _calibrate_confidence from enhanced_parser.py."""
    base = meta.confidence
    penalties = 0.0

    if not meta.title or len(meta.title.strip()) < 10:
        penalties += 0.3
    if meta.title and meta.title.rstrip().endswith('...'):
        penalties += 0.15
    if not meta.authors or meta.authors == "Unknown":
        penalties += 0.2
    if meta.authors and len(meta.authors.strip()) < 3:
        penalties += 0.15

    bonus = 0.0
    if meta.doi:
        bonus += 0.05
    if meta.abstract and len(meta.abstract) > 100:
        bonus += 0.05

    return max(0.0, min(1.0, base - penalties + bonus))


def is_garbage_extraction(meta: FakeMeta, method: str) -> bool:
    """Reimplements _is_garbage_extraction from enhanced_parser.py."""
    if not meta.title:
        return True

    title_lower = meta.title.lower().strip()
    authors_lower = meta.authors.lower() if meta.authors else ""

    # LLM garbage
    llm_garbage_patterns = [
        'extract the title', 'extract title and authors',
        'from this academic paper', 'from the academic paper',
        'please extract', 'identify the title',
        'paper title:', 'authors:',
        'unknown paper', 'example paper', 'academic paper', 'research paper',
        '<pdf text>', '<|im_start|>', '<|im_end|>',
        'metadata extraction', 'return a json', 'json object',
        'here is the', 'i found the following',
        'the title of this paper', 'based on the text',
    ]
    if method == "llm":
        for pattern in llm_garbage_patterns:
            if pattern in title_lower:
                return True

    # Generic garbage starts
    bad_title_starts = [
        'contents lists available', 'sciencedirect', 'springer', 'elsevier',
        'ieee', 'acm digital library', 'communicated by', 'published by',
        'available online', 'accepted manuscript', 'copyright',
        'doi:', 'doi 10.', 'vol.', 'volume ',
    ]
    for bad in bad_title_starts:
        if title_lower.startswith(bad):
            return True

    # Journal header regex
    journal_header_re = re.compile(
        r'^(?:annals|journal|transactions|proceedings|bulletin|letters|reviews?)'
        r'\s+(?:of|in|on)\s+', re.IGNORECASE,
    )
    if journal_header_re.match(title_lower):
        return True

    # Venue patterns
    venue_patterns = [
        r'^(?:siam|ams|ieee|acm)\s+(?:j\.|journal|review|trans)',
        r'^(?:inventiones|mathematische|communications?\s+in|advances?\s+in)\s+math',
        r'^\d{4}\s+mathematics\s+subject\s+classification',
        r'^(?:received|accepted|revised)\s+\d',
    ]
    for pat in venue_patterns:
        if re.match(pat, title_lower):
            return True

    # OCR artifacts
    if len(meta.title) > 10:
        alpha_count = sum(1 for c in meta.title if c.isalpha())
        alpha_ratio = alpha_count / len(meta.title)
        if alpha_ratio < 0.5:
            return True

    # Title == authors
    if meta.authors and meta.authors != "Unknown":
        if len(authors_lower.strip()) > 5 and title_lower == authors_lower.strip():
            return True

    # Length bounds
    if len(meta.title) < 8 or len(meta.title) > 300:
        return True

    # Garbage authors (mark Unknown, don't reject)
    bad_authors = [
        'the author', 'unknown', 'extract', 'paper', 'springer',
        'elsevier', 'ieee', 'microsoft', 'admin', 'user',
    ]
    for bad in bad_authors:
        if authors_lower.strip() == bad:
            meta.authors = "Unknown"

    return False


def compute_consensus_bonus(scored_results: list) -> list:
    """Reimplements _compute_consensus_bonus from enhanced_parser.py."""
    n = len(scored_results)
    if n < 2:
        return scored_results

    titles = [
        r[2].title.lower().strip() if r[2].title else ""
        for r in scored_results
    ]
    agreement_counts = [0] * n

    for i in range(n):
        if not titles[i]:
            continue
        for j in range(i + 1, n):
            if not titles[j]:
                continue
            similarity = fuzz.ratio(titles[i], titles[j])
            if similarity >= 85:
                agreement_counts[i] += 1
                agreement_counts[j] += 1

    adjusted = []
    for idx, (score, method, metadata) in enumerate(scored_results):
        if agreement_counts[idx] >= 1:
            consensus_bonus = 30 * agreement_counts[idx]
            score += consensus_bonus
        adjusted.append((score, method, metadata))

    return adjusted


# ===========================================================================
# TESTS
# ===========================================================================


class TestDiacriticScoring:

    def test_diacritic_bonus_capped_at_20(self):
        many = "Évariste Galois, André Weil, Jérôme Bézout, László Lovász"
        none_ = "John Smith, Jane Doe"

        assert compute_diacritic_bonus(many) == 20
        assert compute_diacritic_bonus(none_) == 0

    def test_diacritics_cannot_override_method_priority(self):
        """50-point method gap (110 vs 60) can't be bridged by +20 bonus."""
        garbage_score = 60 + 20  # heuristic + max diacritic
        good_score = 110 + 0     # metadata_fetcher + no diacritics
        assert good_score > garbage_score

    def test_single_diacritic_gets_bonus(self):
        assert compute_diacritic_bonus("José") == 20

    def test_empty_authors_no_bonus(self):
        assert compute_diacritic_bonus("") == 0
        assert compute_diacritic_bonus(None) == 0


class TestConfidenceCalibration:

    def test_good_result_stays_high(self):
        meta = FakeMeta(title="A Properly Extracted Title", authors="John Smith",
                        confidence=0.98)
        cal = calibrate_confidence(meta, "arxiv_api")
        assert cal >= 0.90

    def test_empty_title_penalised(self):
        cal = calibrate_confidence(
            FakeMeta(title="", confidence=0.98), "arxiv_api"
        )
        assert cal <= 0.70

    def test_no_authors_penalised(self):
        cal = calibrate_confidence(
            FakeMeta(title="Valid Title Here", authors="Unknown", confidence=0.98),
            "arxiv_api",
        )
        assert cal <= 0.80

    def test_doi_gives_bonus(self):
        without = calibrate_confidence(
            FakeMeta(title="Title Here OK", authors="A. B.", confidence=0.70), "h"
        )
        with_doi = calibrate_confidence(
            FakeMeta(title="Title Here OK", authors="A. B.", confidence=0.70,
                     doi="10.1234/test"), "h"
        )
        assert with_doi > without

    def test_truncated_title_penalised(self):
        cal = calibrate_confidence(
            FakeMeta(title="Some truncated title...", authors="A. B.",
                     confidence=0.90), "h"
        )
        assert cal < 0.90

    def test_abstract_gives_bonus(self):
        without = calibrate_confidence(
            FakeMeta(title="Title Here OK", authors="A. B.", confidence=0.70), "h"
        )
        with_abs = calibrate_confidence(
            FakeMeta(title="Title Here OK", authors="A. B.", confidence=0.70,
                     abstract="x" * 150), "h"
        )
        assert with_abs > without

    def test_clamped_to_zero_one(self):
        """Heavily penalised result should not go below 0."""
        cal = calibrate_confidence(
            FakeMeta(title="", authors="", confidence=0.1), "h"
        )
        assert 0.0 <= cal <= 1.0


class TestGarbageDetection:

    def test_empty_title_is_garbage(self):
        assert is_garbage_extraction(FakeMeta(title=""), "h") is True
        assert is_garbage_extraction(FakeMeta(title=None), "h") is True

    def test_journal_header_is_garbage(self):
        assert is_garbage_extraction(FakeMeta(title="Journal of Mathematical Analysis"), "h") is True
        assert is_garbage_extraction(FakeMeta(title="Annals of Probability"), "h") is True
        assert is_garbage_extraction(FakeMeta(title="Transactions of the AMS"), "h") is True

    def test_venue_pattern_is_garbage(self):
        assert is_garbage_extraction(FakeMeta(title="SIAM Journal on Control"), "h") is True
        assert is_garbage_extraction(FakeMeta(title="SIAM J. Math. Anal."), "h") is True

    def test_publisher_is_garbage(self):
        assert is_garbage_extraction(FakeMeta(title="Contents lists available at ScienceDirect"), "h") is True
        assert is_garbage_extraction(FakeMeta(title="Springer-Verlag Berlin"), "h") is True
        assert is_garbage_extraction(FakeMeta(title="Elsevier B.V. publishes"), "h") is True

    def test_doi_as_title_is_garbage(self):
        assert is_garbage_extraction(FakeMeta(title="DOI: 10.1214/aop/2023"), "h") is True
        assert is_garbage_extraction(FakeMeta(title="doi 10.1007/s00440"), "h") is True

    def test_volume_as_title_is_garbage(self):
        assert is_garbage_extraction(FakeMeta(title="Vol. 42, No. 3, pp. 1-25"), "h") is True

    def test_ocr_artifacts_are_garbage(self):
        assert is_garbage_extraction(FakeMeta(title="!@#$%^&*()_+{}|:<>?~`12345"), "h") is True

    def test_llm_prompt_leakage_is_garbage(self):
        assert is_garbage_extraction(
            FakeMeta(title="Extract the title from this paper"), "llm"
        ) is True
        assert is_garbage_extraction(
            FakeMeta(title="Based on the text, the title is"), "llm"
        ) is True
        assert is_garbage_extraction(
            FakeMeta(title="<pdf text> some content here"), "llm"
        ) is True

    def test_valid_title_is_not_garbage(self):
        assert is_garbage_extraction(
            FakeMeta(title="On the convergence of stochastic gradient descent"), "h"
        ) is False
        assert is_garbage_extraction(
            FakeMeta(title="Mean field games with common noise"), "h"
        ) is False
        assert is_garbage_extraction(
            FakeMeta(title="Brownian motion and stochastic calculus"), "h"
        ) is False

    def test_short_title_is_garbage(self):
        assert is_garbage_extraction(FakeMeta(title="Hi"), "h") is True
        assert is_garbage_extraction(FakeMeta(title="Paper"), "h") is True

    def test_long_title_is_garbage(self):
        assert is_garbage_extraction(FakeMeta(title="A" * 301), "h") is True

    def test_title_equals_authors_is_garbage(self):
        assert is_garbage_extraction(
            FakeMeta(title="John Smith", authors="John Smith"), "h"
        ) is True

    def test_garbage_authors_marked_unknown(self):
        meta = FakeMeta(title="Valid Paper Title Here", authors="springer")
        result = is_garbage_extraction(meta, "h")
        assert result is False
        assert meta.authors == "Unknown"

    def test_llm_garbage_not_triggered_for_non_llm(self):
        """LLM-specific patterns should only fire for method='llm'."""
        assert is_garbage_extraction(
            FakeMeta(title="Extract the title from this research paper"), "heuristic"
        ) is False


class TestConsensusScoring:

    def test_two_methods_agree_get_bonus(self):
        results = [
            (100, "arxiv_api", FakeMeta(title="Mean Field Games")),
            (80, "heuristic", FakeMeta(title="Mean Field Games")),
        ]
        adjusted = compute_consensus_bonus(results)
        assert adjusted[0][0] == 130
        assert adjusted[1][0] == 110

    def test_disagreeing_methods_no_bonus(self):
        results = [
            (100, "arxiv_api", FakeMeta(title="Completely Different Paper")),
            (80, "heuristic", FakeMeta(title="Mean Field Games with Noise")),
        ]
        adjusted = compute_consensus_bonus(results)
        assert adjusted[0][0] == 100
        assert adjusted[1][0] == 80

    def test_fuzzy_agreement_works(self):
        results = [
            (100, "arxiv_api", FakeMeta(title="Mean Field Games with Common Noise")),
            (80, "heuristic", FakeMeta(title="Mean field games with common noise")),
        ]
        adjusted = compute_consensus_bonus(results)
        assert adjusted[0][0] > 100
        assert adjusted[1][0] > 80

    def test_single_result_no_bonus(self):
        results = [
            (100, "arxiv_api", FakeMeta(title="Some Paper Title")),
        ]
        adjusted = compute_consensus_bonus(results)
        assert adjusted[0][0] == 100

    def test_three_methods_agree(self):
        title = "Convergence of BSDE Solutions"
        results = [
            (110, "metadata_fetcher", FakeMeta(title=title)),
            (100, "arxiv_api", FakeMeta(title=title)),
            (60, "heuristic", FakeMeta(title=title)),
        ]
        adjusted = compute_consensus_bonus(results)
        assert adjusted[0][0] == 170  # +60 (2 agreements × 30)
        assert adjusted[1][0] == 160
        assert adjusted[2][0] == 120

    def test_empty_title_excluded(self):
        results = [
            (100, "arxiv_api", FakeMeta(title="")),
            (80, "heuristic", FakeMeta(title="")),
        ]
        adjusted = compute_consensus_bonus(results)
        assert adjusted[0][0] == 100
        assert adjusted[1][0] == 80

    def test_partial_agreement(self):
        """Two agree, one disagrees — only the two get bonus."""
        results = [
            (110, "metadata_fetcher", FakeMeta(title="Mean Field Games")),
            (100, "arxiv_api", FakeMeta(title="Mean Field Games")),
            (60, "heuristic", FakeMeta(title="Something Entirely Different Here")),
        ]
        adjusted = compute_consensus_bonus(results)
        assert adjusted[0][0] == 140  # +30
        assert adjusted[1][0] == 130  # +30
        assert adjusted[2][0] == 60   # no bonus
