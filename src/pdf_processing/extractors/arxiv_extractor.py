"""
ArXiv PDF Content Extractor

Specialized extractor for arXiv papers with enhanced title cleaning.
Extracted from extractors.py for better modularity.
"""

import regex as re
import logging
from typing import Optional, Tuple, List

from ..models import TextBlock, PDFMetadata, MetadataSource
from ..constants import PDFConstants

logger = logging.getLogger(__name__)


class AdvancedArxivExtractor:
    """Enhanced arXiv extractor with better title cleaning"""

    def __init__(self):
        self.arxiv_patterns = {
            "header_pattern": r"arxiv:\d{4}\.\d{4,5}",
            "indicators": [
                "arxiv:",
                "submitted",
                "revised",
                "[cs.",
                "[math.",
                "[stat.",
            ],
        }

    def extract_title(  # noqa: C901
        self, text: str, text_blocks: List[TextBlock]
    ) -> Tuple[Optional[str], float]:
        """
        arXiv first page → title extraction.

        Strategy
        --------
        1.  Scan the first 10 logical lines looking for the canonical
            "arXiv:NNNN.NNNNN [cat]" header.  If we see it, test both
            *same-line* and *next-line* variants.
        2.  If nothing acceptable is found, fall back to the original
            heuristic pass (same code as before).
        """
        if not text:
            return None, 0.0
            
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

        # ---------- step 1 : explicit header -----------------
        header_re = re.compile(r"arxiv:\d{4}\.\d{4,5}", re.I)
        for idx, ln in enumerate(lines[:10]):
            if not header_re.search(ln):
                continue

            # 1 a)  title on the same line  …  "…[cs.CV]  Title of the Paper"
            m = re.search(r"\[[A-Za-z]+\.[A-Za-z]+\]\s*(.+)$", ln)
            if m:
                cand = self._clean_arxiv_title(m.group(1))
                if len(cand) >= PDFConstants.MIN_TITLE_LENGTH:
                    return cand, 0.80

            # 1 b)  title starts right after the identifier
            m = re.search(r"arxiv:\d{4}\.\d{4,5}v?\d*\s+(.+)", ln, re.I)
            if m:
                cand_raw = re.sub(r"^\[[\w.]+\]\s*", "", m.group(1))
                cand = self._clean_arxiv_title(cand_raw)
                if len(cand) >= PDFConstants.MIN_TITLE_LENGTH:
                    return cand, 0.80

            # 1 c)  title is on the very next non-empty line
            if idx + 1 < len(lines):
                cand = self._clean_arxiv_title(lines[idx + 1])
                if len(cand) >= PDFConstants.MIN_TITLE_LENGTH:
                    return cand, 0.75

        # ---------- step 2 : heuristic fallback (unchanged) --
        for ln in lines[:15]:
            if self._looks_like_authors(ln) or len(ln) < 10 or len(ln) > 250:
                continue
            if self._is_title_like(ln):
                cand = self._clean_arxiv_title(ln)
                if len(cand) >= PDFConstants.MIN_TITLE_LENGTH:
                    return cand, 0.60

        return None, 0.0

    def extract_authors(
        self, text: str, text_blocks: List[TextBlock]
    ) -> Tuple[Optional[str], float]:
        """Extract authors from arXiv paper"""
        if not text:
            return None, 0.0
            
        lines = text.split("\n")

        for i, line in enumerate(lines[3:20], 3):
            line = line.strip()
            if not line:
                continue

            # Skip metadata
            if any(skip in line.lower() for skip in self.arxiv_patterns["indicators"]):
                continue

            if self._looks_like_authors(line):
                authors = self._extract_authors(line)
                if authors:
                    return authors, 0.75

        return None, 0.0

    def _is_title_like(self, line: str) -> bool:
        """Check if line looks like title"""
        line_lower = line.lower()

        # Should have academic content
        academic_indicators = [
            "learning",
            "analysis",
            "method",
            "algorithm",
            "model",
            "theory",
            "approach",
            "framework",
            "study",
            "survey",
            "deep",
            "neural",
            "computer",
            "vision",
            "machine",
            "artificial",
            "intelligence",
        ]

        has_academic = any(word in line_lower for word in academic_indicators)

        # Good capitalization
        words = line.split()
        if words:
            capital_ratio = sum(
                1 for word in words if word and word[0].isupper()
            ) / len(words)
            good_caps = capital_ratio > 0.3
        else:
            good_caps = False

        return has_academic or good_caps

    def _looks_like_authors(self, line: str) -> bool:
        """Check if line contains authors"""
        name_count = len(re.findall(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b", line))
        has_separators = any(sep in line for sep in [", ", " and ", " & "])

        # Should not be too long for just authors
        reasonable_length = len(line) < 200

        return name_count >= 1 and has_separators and reasonable_length

    def _extract_authors(self, line: str) -> Optional[str]:
        """Extract clean author names"""
        # Remove prefixes
        line = re.sub(r"authors?\s*:\s*", "", line, flags=re.IGNORECASE)

        # Extract names
        names = re.findall(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b", line)

        # Filter institutional contamination
        clean_names = []
        for name in names:
            if not any(
                inst in name.lower() for inst in ["university", "institute", "arxiv"]
            ):
                clean_names.append(name.strip())

        if clean_names:
            if len(clean_names) > PDFConstants.MAX_AUTHORS:
                return ", ".join(clean_names[: PDFConstants.MAX_AUTHORS]) + ", et al."
            else:
                return ", ".join(clean_names)

        return None

    def _clean_arxiv_title(self, title: str) -> str:
        """Clean arXiv title of artifacts - ENHANCED"""
        # Remove arXiv identifiers at any position
        title = re.sub(r"arxiv:\d{4}\.\d{4,5}v?\d*\s*", "", title, flags=re.IGNORECASE)

        # Remove category codes like [cs.lg], [math.CO], etc.
        title = re.sub(r"\[[a-z]+\.[a-z]+\]\s*", "", title, flags=re.IGNORECASE)

        # Remove common arXiv metadata - be more precise
        title = re.sub(r"submitted\s+on\s+\d{1,2}\s+\w{3}\s+\d{4}\s*", "", title, flags=re.IGNORECASE)
        title = re.sub(r"revised\s+on\s+\d{1,2}\s+\w{3}\s+\d{4}\s*", "", title, flags=re.IGNORECASE)
        title = re.sub(r"\d+\s+pages?\b.*", "", title, flags=re.IGNORECASE)

        # Clean whitespace
        title = re.sub(r"\s+", " ", title).strip()
        title = title.strip(".,;:-")

        # Check if result looks like a date (not a title)
        date_patterns = [
            r'^\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}$',
            r'^\d{4}-\d{2}-\d{2}$',
            r'^\d{1,2}/\d{1,2}/\d{4}$',
            r'^\d{4}\.\d{2}\.\d{2}$'
        ]
        for pattern in date_patterns:
            if re.match(pattern, title, re.IGNORECASE):
                return ""  # Reject date-like strings as titles

        # Ensure proper capitalization
        if title:
            title = title[0].upper() + title[1:] if len(title) > 1 else title.upper()

        # If the cleaning process stripped everything, signal "no title".
        return title if len(title) >= PDFConstants.MIN_TITLE_LENGTH else ""

    def extract_arxiv_id_from_text(self, text: str) -> Optional[str]:
        """Extract arXiv ID from PDF text content"""
        if not text:
            return None

        patterns = [
            r"arXiv\s*:\s*(\d{4}\.\d{4,5}(?:v\d+)?)",
            r"arXiv\s*:\s*(\d{4}\.\d{4,5}(?:v\d+)?)\s*\[[^\]]+\]",
            r"arXiv\s+identifier\s*:\s*(\d{4}\.\d{4,5}(?:v\d+)?)",
            r"(\d{4}\.\d{4,5}(?:v\d+)?)\s*\[[^\]]+\]",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
            if match:
                arxiv_id = match.group(1)
                return arxiv_id

        return None

    def extract_metadata(self, text: str, text_blocks: List[TextBlock]) -> PDFMetadata:
        """Extract metadata combining title and authors extraction"""
        title, title_confidence = self.extract_title(text, text_blocks)
        authors, author_confidence = self.extract_authors(text, text_blocks)
        
        # Extract arXiv ID
        arxiv_id = self.extract_arxiv_id_from_text(text)
        
        # Average confidence
        confidence = (title_confidence + author_confidence) / 2
        
        return PDFMetadata(
            title=title or "Unknown Title",
            authors=authors or "Unknown",
            source=MetadataSource.REPOSITORY,
            confidence=confidence,
            repository_type="arXiv",
            arxiv_id=arxiv_id
        )