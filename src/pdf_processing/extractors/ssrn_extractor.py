"""
SSRN PDF Content Extractor

Specialized extractor for SSRN working papers.
Extracted from extractors.py for better modularity.
"""

import regex as re
import logging
from typing import Optional, Tuple, List

from ..models import TextBlock, PDFMetadata, MetadataSource
from ..constants import PDFConstants

logger = logging.getLogger(__name__)


class AdvancedSSRNExtractor:
    """
    Extract title and authors from SSRN working-paper PDFs.

    The heuristics are deliberately simple because SSRN puts nearly all
    relevant metadata on the first page in plain text – usually the title
    in title-case followed by the author list.
    """

    def __init__(self):
        self.ssrn_patterns = {
            "header_indicators": [
                r"electronic\s+copy\s+available\s+at.*ssrn",
                r"posted\s+at\s+the\s+ssrn",
                r"social\s+science\s+research\s+network",
                r"ssrn\.com",
            ],
            "title_stop_words": [
                "electronic copy",
                "posted at",
                "ssrn",
                "download date",
                "last revised",
                "abstract",
                "keywords",
            ],
        }

    def extract_title(
        self, text: str, text_blocks: List[TextBlock]
    ) -> Tuple[Optional[str], float]:
        """
        Return a tuple (clean_title, confidence).

        The first 20 non-empty lines are inspected.  A line is accepted once
        *  it is not a banner/metadata line,
        *  it is not obviously an author line, **and**
        *  `_score_title_candidate` returns ≥ 0 .6.
        """
        if not text:
            return None, 0.0
            
        for line in (ln.strip() for ln in text.splitlines() if ln.strip()):
            low = line.lower()

            # stop after we inspected the first 20 substantive lines
            if (idx := getattr(self, "_line_counter", 0)) >= 20:
                break
            self._line_counter = idx + 1  # noqa: B020 (set once per call)

            if any(w in low for w in self.ssrn_patterns["title_stop_words"]):
                continue
            if self._looks_like_author_line(line):
                continue

            score = self._score_title_candidate(line)
            if score >= 0.6:
                return self._clean_title(line), score

        return None, 0.0

    def extract_authors(
        self, text: str, text_blocks: List[TextBlock]
    ) -> Tuple[Optional[str], float]:
        """Extract authors from SSRN paper text."""
        if not text:
            return None, 0.0
            
        lines = (ln.strip() for ln in text.splitlines() if ln.strip())
        for ln in list(lines)[:30]:
            if self._looks_like_author_line(ln):
                authors = self._extract_clean_authors(ln)
                if authors:
                    return authors, 0.75
        return None, 0.0

    def _score_title_candidate(self, line: str) -> float:
        """Score a line as potential title"""
        score = 0.0
        line_lower = line.lower()

        # Length bonus
        if 20 <= len(line) <= 200:
            score += 0.4
        elif 10 <= len(line) <= 300:
            score += 0.2

        # Academic content
        academic_keywords = [
            "analysis",
            "study",
            "investigation",
            "approach",
            "method",
            "model",
            "theory",
            "framework",
            "application",
            "evidence",
            "research",
            "machine learning",
            "artificial intelligence",
            "financial",
            "economic",
        ]

        keyword_count = sum(1 for keyword in academic_keywords if keyword in line_lower)
        score += min(0.4, keyword_count * 0.15)

        # Penalty for obvious non-titles
        if any(stop in line_lower for stop in self.ssrn_patterns["title_stop_words"]):
            score -= 0.5

        # Penalty for author-like content
        if self._looks_like_author_line(line):
            score -= 0.3

        return max(0.0, score)

    def _looks_like_author_line(self, line: str) -> bool:
        """Check if line contains author names"""
        # Count potential names
        name_count = len(re.findall(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b", line))

        if name_count < 1:
            return False

        # Check for separators
        has_separators = any(sep in line for sep in [", ", " and ", " & "])

        # Check for institutional contamination
        institutional_words = [
            "university",
            "college",
            "school",
            "institute",
            "department",
        ]
        institutional_count = sum(
            1 for word in institutional_words if word in line.lower()
        )

        return has_separators and institutional_count <= 1

    def _extract_clean_authors(self, line: str) -> Optional[str]:
        """Extract clean author names"""
        # Remove footnote markers
        line = re.sub(r"[¹²³⁴⁵⁶⁷⁸⁹⁰*†‡§¶#]+", "", line)

        # Extract names
        names = re.findall(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b", line)

        # Filter institutional names
        clean_names = []

        for name in names:
            name_lower = name.lower()
            if not any(
                inst in name_lower
                for inst in [
                    "university",
                    "college",
                    "school",
                    "institute",
                    "department",
                    "social",
                    "science",
                    "research",
                    "network",
                    "electronic",
                ]
            ):
                clean_names.append(name.strip())

        # Remove duplicates
        unique_names = list(dict.fromkeys(clean_names))

        if unique_names:
            if len(unique_names) > PDFConstants.MAX_AUTHORS:
                return ", ".join(unique_names[: PDFConstants.MAX_AUTHORS]) + ", et al."
            else:
                return ", ".join(unique_names)

        return None

    def _clean_title(self, title: str) -> str:
        """Clean and format title"""
        if not title:
            return ""

        # Remove artifacts
        title = re.sub(r"[¹²³⁴⁵⁶⁷⁸⁹⁰*†‡§¶#]+", "", title)
        title = re.sub(r"\s+", " ", title).strip()
        title = title.strip(".,;:-")

        return title

    def extract_metadata(self, text: str, text_blocks: List[TextBlock]) -> PDFMetadata:
        """Extract metadata combining title and authors extraction"""
        title, title_confidence = self.extract_title(text, text_blocks)
        authors, author_confidence = self.extract_authors(text, text_blocks)
        
        # Average confidence
        confidence = (title_confidence + author_confidence) / 2
        
        return PDFMetadata(
            title=title or "Unknown Title",
            authors=authors or "Unknown",
            source=MetadataSource.REPOSITORY,
            confidence=confidence,
            repository_type="SSRN"
        )