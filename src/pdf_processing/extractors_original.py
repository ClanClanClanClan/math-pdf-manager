"""
PDF Content Extractors

Specialized extractors for different types of academic papers.
Extracted from parsers.pdf_parser.py for better modularity.
"""

import regex as re
import time
import logging
from pathlib import Path
from typing import Optional, Tuple, List
from urllib.parse import quote
from urllib.request import urlopen
from urllib.error import HTTPError, URLError

from .models import TextBlock, ArxivMetadata
from .constants import PDFConstants

# Get logger
logger = logging.getLogger(__name__)

# Check if we're in offline mode
try:
    from config import OFFLINE
except ImportError:
    OFFLINE = False

# Check for SecureXMLParser
try:
    from security.xml_parser import SecureXMLParser
except ImportError:
    # Fallback to defusedxml for secure XML parsing
    try:
        import defusedxml.ElementTree as ET
    except ImportError:
        import xml.etree.ElementTree as ET
        import logging
        logging.getLogger(__name__).warning("DefusedXML not available, using standard XML parser (less secure)")
    
    class SecureXMLParser:
        @staticmethod
        def parse_string(xml_data: str):
            # Fallback XML parser with limited security (defusedxml recommended)
            return ET.fromstring(xml_data)  # nosec B314 - fallback when defusedxml unavailable


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

    # ─────────────────────── TITLE ────────────────────────
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

    # ─────────────────────── AUTHORS ──────────────────────
    def extract_authors(
        self, text: str, text_blocks: List[TextBlock]
    ) -> Tuple[Optional[str], float]:
        """Unchanged from your original version."""
        if not text:
            return None, 0.0
            
        lines = (ln.strip() for ln in text.splitlines() if ln.strip())
        for ln in list(lines)[:30]:
            if self._looks_like_author_line(ln):
                authors = self._extract_clean_authors(ln)
                if authors:
                    return authors, 0.75
        return None, 0.0

    # helper methods (_score_title_candidate, _looks_like_author_line,
    # _extract_clean_authors, _clean_title) stay exactly as you wrote them

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

    def extract_metadata(self, text: str, text_blocks: List[TextBlock]) -> 'PDFMetadata':
        """Extract metadata combining title and authors extraction"""
        from .models import PDFMetadata, MetadataSource
        
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

    def extract_metadata(self, text: str, text_blocks: List[TextBlock]) -> 'PDFMetadata':
        """Extract metadata combining title and authors extraction"""
        from .models import PDFMetadata, MetadataSource
        
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


class AdvancedJournalExtractor:
    """Enhanced journal extractor with better title extraction"""

    def __init__(self):
        self.journal_indicators = [
            "journal of",
            "proceedings of",
            "transactions on",
            "ieee",
            "acm",
            "springer",
            "elsevier",
            "wiley",
            "nature",
            "science",
        ]

        self.journal_metadata = [
            "vol.",
            "volume",
            "pp.",
            "pages",
            "doi:",
            "issn",
            "©",
            "copyright",
            "received:",
            "accepted:",
            "published:",
        ]

    def extract_title(
        self, text: str, text_blocks: List[TextBlock]
    ) -> Tuple[Optional[str], float]:
        """Extract title from journal paper with proper cleaning"""
        if not text:
            return None, 0.0
            
        lines = text.split("\n")

        # Skip journal headers - find actual content start
        content_start = 0
        for i, line in enumerate(lines[:15]):
            line_lower = line.lower().strip()
            if not line_lower:
                continue
            if any(journal in line_lower for journal in self.journal_indicators):
                content_start = i + 1
                # Skip additional empty lines after journal name
                while content_start < len(lines) and not lines[content_start].strip():
                    content_start += 1
                break
            if any(meta in line_lower for meta in self.journal_metadata):
                content_start = i + 1
                continue

        # Look for title after skipping headers
        for i in range(content_start, min(content_start + 10, len(lines))):
            if i >= len(lines):
                break

            line = lines[i].strip()
            if not line or len(line) < 10:
                continue

            # Skip if it's clearly authors (has comma-separated names)
            if re.search(r"[A-Z][a-z]+\s*,\s*[A-Z][a-z]+\s*,\s*[A-Z][a-z]+", line):
                continue

            # Skip if it has institutional indicators
            if any(
                inst in line.lower()
                for inst in ["university", "institute", "research center", "laboratory"]
            ):
                continue

            # Check if this could be a title
            if self._is_journal_title(line):
                # Extract just the title portion if line is long
                if len(line) > 200:
                    clean_title = self._extract_title_portion(line)
                else:
                    clean_title = self._clean_journal_title(line)

                # Ensure reasonable length - be more conservative about truncation
                if len(clean_title) > 250:
                    # Try to find natural break point
                    if ". " in clean_title:
                        clean_title = clean_title.split(". ")[0]
                    elif " - " in clean_title:
                        clean_title = clean_title.split(" - ")[0]
                    else:
                        # Truncate at word boundary - be more conservative
                        words = clean_title.split()
                        # Only truncate if we have a substantial title (more than 10 words)
                        # and ensure we keep at least 8 words
                        while len(" ".join(words)) > 250 and len(words) > 8:
                            words.pop()
                        clean_title = " ".join(words)

                # Final length check
                if 10 <= len(clean_title) < 300:
                    return clean_title, 0.75

        return None, 0.0

    def extract_authors(
        self, text: str, text_blocks: List[TextBlock]
    ) -> Tuple[Optional[str], float]:
        """Extract authors from journal paper"""
        if not text:
            return None, 0.0
            
        lines = text.split("\n")

        for i, line in enumerate(lines[3:20], 3):
            line = line.strip()
            if line and self._looks_like_authors(line):
                authors = self._extract_authors(line)
                if authors:
                    return authors, 0.7

        return None, 0.0

    def _is_journal_title(self, line: str) -> bool:
        """Check if line is journal title"""
        line_lower = line.lower()

        # Should not be metadata
        if any(meta in line_lower for meta in self.journal_metadata):
            return False

        # Should not be journal name itself
        if any(journal in line_lower for journal in self.journal_indicators):
            return False

        # Should not be author names
        if self._looks_like_authors(line):
            return False

        # Should have academic content
        academic_words = [
            "analysis",
            "study",
            "method",
            "approach",
            "model",
            "algorithm",
            "framework",
            "investigation",
            "research",
            "evidence",
            "quantum",
            "machine",
            "learning",
            "discovery",
            "development",
            "application",
        ]

        has_academic_content = any(word in line_lower for word in academic_words)

        # Or should look like a proper title (good capitalization)
        words = line.split()
        if words:
            capital_ratio = sum(
                1 for word in words if word and word[0].isupper()
            ) / len(words)
            good_capitalization = capital_ratio > 0.4
        else:
            good_capitalization = False

        return has_academic_content or good_capitalization

    def _looks_like_authors(self, line: str) -> bool:
        """Check if line contains authors"""
        # Look for potential name patterns
        potential_names = re.findall(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b", line)
        
        # Filter out common academic terms that might look like names
        academic_terms = {
            "Deep Learning", "Machine Learning", "Neural Networks", "Economic Forecasting",
            "Data Science", "Computer Science", "Artificial Intelligence", "Natural Language",
            "Information Technology", "Signal Processing", "Image Processing", "Pattern Recognition",
            "Knowledge Management", "Decision Making", "Problem Solving", "Risk Management",
            "Quality Control", "Process Optimization", "System Design", "Software Engineering",
            "Network Security", "Database Management", "Web Development", "Mobile Computing"
        }
        
        actual_names = [name for name in potential_names if name not in academic_terms]
        name_count = len(actual_names)
        
        # Check for author-specific separators (commas are stronger indicators than "and")
        has_comma_separators = ", " in line
        has_weak_separators = any(sep in line for sep in [" and ", " & "]) and not has_comma_separators
        
        # Should not be heavily institutional
        institutional_count = sum(
            1
            for word in ["university", "institute", "department"]
            if word in line.lower()
        )
        
        # More restrictive: require comma separators OR multiple names with weak separators
        if has_comma_separators:
            return name_count >= 1 and institutional_count <= 2
        elif has_weak_separators:
            return name_count >= 2 and institutional_count <= 1  # More restrictive for weak separators
        else:
            return False

    def _extract_authors(self, line: str) -> Optional[str]:
        """Extract authors"""
        # Remove prefixes
        line = re.sub(r"^authors?\s*:\s*", "", line, flags=re.IGNORECASE)

        # Extract names
        names = re.findall(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b", line)

        # Filter contamination
        clean_names = []
        for name in names:
            if not any(
                inst in name.lower()
                for inst in ["university", "institute", "department"]
            ):
                clean_names.append(name)

        if clean_names:
            if len(clean_names) > PDFConstants.MAX_AUTHORS:
                return ", ".join(clean_names[: PDFConstants.MAX_AUTHORS]) + ", et al."
            else:
                return ", ".join(clean_names)

        return None

    def _extract_title_portion(self, line: str) -> str:
        """Extract just the title portion from a line that may contain authors/abstract"""
        # First, check if there are clear author patterns
        # Look for comma-separated names which indicate author list
        author_match = re.search(
            r"([A-Z][a-z]+\s+[A-Z][a-z]+)\s*,\s*([A-Z][a-z]+\s+[A-Z][a-z]+)", line
        )
        if author_match:
            # Title is likely before the first author
            title_end = author_match.start()
            if title_end > 10:
                line = line[:title_end].strip()

        # Also check for institution indicators
        inst_indicators = [
            r"\b(?:University|Institute|College|School|Department|Laboratory|Center|Centre)\b",
            r"\b(?:MIT|IBM|Google|Microsoft|Stanford|Harvard|Cambridge)\b",
        ]

        earliest_pos = len(line)
        for pattern in inst_indicators:
            match = re.search(pattern, line, re.IGNORECASE)
            if match and match.start() > 20:  # Title should be at least 20 chars
                # Check if there are names before the institution
                text_before = line[: match.start()]
                if re.search(r"[A-Z][a-z]+\s+[A-Z][a-z]+", text_before[-50:]):
                    # Find where names likely start
                    name_match = re.search(r"([A-Z][a-z]+\s+[A-Z][a-z]+)", text_before)
                    if name_match:
                        earliest_pos = min(
                            earliest_pos, text_before.find(name_match.group())
                        )

        if earliest_pos < len(line) and earliest_pos > 20:
            line = line[:earliest_pos].strip()

        # Remove any trailing metadata indicators
        line = re.sub(r"\s*ABSTRACT\s*:?.*", "", line, flags=re.IGNORECASE)
        line = re.sub(r"\s*Abstract\s*:?.*", "", line)
        line = re.sub(r"\s*Keywords?\s*:.*", "", line, flags=re.IGNORECASE)

        return self._clean_journal_title(line)

    def _clean_journal_title(self, title: str) -> str:
        """Clean journal title of artifacts"""
        # Remove journal names
        for journal in self.journal_indicators:
            title = re.sub(journal, "", title, flags=re.IGNORECASE)

        # Remove metadata - be more specific to avoid false matches
        for meta in self.journal_metadata:
            # Add word boundary for patterns that could match inside words
            if meta in ["pp.", "vol.", "doi:", "issn"]:
                pattern = r"\b" + re.escape(meta) + r".*"
            else:
                pattern = re.escape(meta) + r".*"
            title = re.sub(pattern, "", title, flags=re.IGNORECASE)

        # Clean whitespace
        title = re.sub(r"\s+", " ", title).strip()
        title = title.strip(".,;:-")

        # Ensure proper capitalization
        if title:
            title = title[0].upper() + title[1:] if len(title) > 1 else title.upper()

        return title

    def extract_metadata(self, text: str, text_blocks: List[TextBlock]) -> 'PDFMetadata':
        """Extract metadata combining title and authors extraction"""
        from .models import PDFMetadata, MetadataSource
        
        title, title_confidence = self.extract_title(text, text_blocks)
        authors, author_confidence = self.extract_authors(text, text_blocks)
        
        # Average confidence
        confidence = (title_confidence + author_confidence) / 2
        
        return PDFMetadata(
            title=title or "Unknown Title",
            authors=authors or "Unknown",
            source=MetadataSource.REPOSITORY,
            confidence=confidence,
            repository_type="Journal"
        )


class ArxivAPIClient:
    """Client for interacting with arXiv API"""

    BASE_URL = "http://export.arxiv.org/api/query"  # WARNING: Insecure HTTP protocol - use HTTPS

    def __init__(self, delay_seconds: float = 3.0):
        self.delay_seconds = delay_seconds
        self.last_call_time = 0
        self.api_available = not OFFLINE

    def extract_arxiv_id_from_filename(self, filename: str) -> Optional[str]:
        """Extract arXiv ID from filename"""
        name = Path(filename).stem

        patterns = [
            r"^(\d{4}\.\d{4,5}(?:v\d+)?)$",  # 2021.12345[v2]
            r"^(?:[\w\-\.]+/)?\d{4}\.\d{4,5}(?:v\d+)?$",  # With prefix
            r"^(?:[\w\-]+/)?(\d{7})$",  # Old format
            r"[^\d]*(\d{4}\.\d{4,5}(?:v\d+)?)[^\d]*",  # ID anywhere
        ]

        for pattern in patterns:
            match = re.search(pattern, name)
            if match:
                arxiv_id = match.group(1) if match.groups() else match.group(0)
                arxiv_id = re.sub(r"^.*?(\d{4}\.\d{4,5}(?:v\d+)?).*$", r"\1", arxiv_id)
                logger.debug(
                    f"Extracted arXiv ID '{arxiv_id}' from filename '{filename}'"
                )
                return arxiv_id

        return None

    def extract_arxiv_id_from_text(self, text: str) -> Optional[str]:
        """Extract arXiv ID from PDF text content"""
        if not text:
            return None

        patterns = [
            r"arXiv\s*:\s*(\d{4}\.\d{4,5}(?:v\d+)?)",
            r"arXiv\s*:\s*(\d{4}\.\d{4,5}(?:v\d+)?)\s*\[[^\]]+\]",
            r"(\d{4}\.\d{4,5}(?:v\d+)?)\s*\[[^\]]+\]",
            # Only match standalone arXiv IDs if they appear to be in a citation context
            # (not just any number sequence) - removing overly permissive pattern
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
            if match:
                arxiv_id = match.group(1)
                logger.debug(f"Found arXiv ID '{arxiv_id}' in document text")
                return arxiv_id

        return None

    def fetch_metadata(self, arxiv_id: str) -> Optional[ArxivMetadata]:
        """Fetch metadata from arXiv API"""
        if not self.api_available:
            return None

        # Respect rate limit
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time
        if time_since_last_call < self.delay_seconds:
            time.sleep(self.delay_seconds - time_since_last_call)

        try:
            query_url = f"{self.BASE_URL}?id_list={quote(arxiv_id)}"
            logger.info(f"Fetching metadata from arXiv API for ID: {arxiv_id}")

            # Validate URL scheme for security
            if not query_url.startswith(('http://', 'https://')):
                raise ValueError("Only HTTP(S) URLs are allowed")

            with urlopen(query_url, timeout=10) as response:  # nosec B310 - URL validated above for HTTP/HTTPS only
                xml_data = response.read().decode("utf-8")

            self.last_call_time = time.time()

            metadata = self._parse_arxiv_xml(xml_data, arxiv_id)

            if metadata:
                logger.info(f"Successfully fetched metadata for arXiv:{arxiv_id}")
            else:
                logger.warning(f"No results found for arXiv:{arxiv_id}")

            return metadata

        except (HTTPError, URLError) as e:
            logger.error(f"Network error fetching arXiv metadata: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching arXiv metadata: {e}")
            return None

    def _parse_arxiv_xml(
        self, xml_data: str, original_id: str
    ) -> Optional[ArxivMetadata]:
        """Parse arXiv API XML response"""
        try:
            root = SecureXMLParser.parse_string(xml_data)

            ns = {
                "atom": "http://www.w3.org/2005/Atom",  # WARNING: Insecure HTTP protocol - use HTTPS
                "arxiv": "http://arxiv.org/schemas/atom",  # WARNING: Insecure HTTP protocol - use HTTPS
            }

            entries = root.findall(".//atom:entry", ns)
            if not entries:
                return None

            entry = entries[0]  # Take first result

            # Extract basic info
            title = entry.find("atom:title", ns)
            summary = entry.find("atom:summary", ns)
            published = entry.find("atom:published", ns)
            updated = entry.find("atom:updated", ns)

            # Extract authors
            authors = []
            for author in entry.findall("atom:author", ns):
                name = author.find("atom:name", ns)
                if name is not None:
                    authors.append(name.text.strip())

            # Extract categories
            categories = []
            primary_category = None
            for category in entry.findall("atom:category", ns):
                term = category.get("term")
                if term:
                    categories.append(term)
                    if category.get("scheme") and "primary" in category.get("scheme", ""):
                        primary_category = term

            if not primary_category and categories:
                primary_category = categories[0]

            # Extract links
            pdf_url = ""
            for link in entry.findall("atom:link", ns):
                if link.get("type") == "application/pdf":
                    pdf_url = link.get("href", "")

            # Extract DOI and journal reference
            doi = None
            journal_ref = None
            comment = None

            for element in entry.findall("arxiv:doi", ns):
                if element.text:
                    doi = element.text.strip()

            for element in entry.findall("arxiv:journal_ref", ns):
                if element.text:
                    journal_ref = element.text.strip()

            for element in entry.findall("arxiv:comment", ns):
                if element.text:
                    comment = element.text.strip()

            return ArxivMetadata(
                arxiv_id=original_id,
                title=title.text.strip() if title is not None else "",
                authors=authors,
                abstract=summary.text.strip() if summary is not None else "",
                categories=categories,
                primary_category=primary_category or "",
                published=published.text.strip() if published is not None else "",
                updated=updated.text.strip() if updated is not None else "",
                doi=doi,
                journal_ref=journal_ref,
                comment=comment,
                pdf_url=pdf_url,
                confidence=0.95,
            )

        except Exception as e:
            logger.error(f"Error parsing arXiv XML: {e}")
            return None


# Backward compatibility - Fake Grobid client for tests
class _FakeGrobidClient:
    """minimal API-surface"""

    def process_fulltext_document(self, *args, **kwargs):
        return {"title": "Sample Title", "authors": [{"first": "John", "last": "Doe"}]}


# Backward compatibility
globals().update(
    AdvancedSSRNExtractor=AdvancedSSRNExtractor,
    AdvancedArxivExtractor=AdvancedArxivExtractor,
    AdvancedJournalExtractor=AdvancedJournalExtractor,
    ArxivAPIClient=ArxivAPIClient,
    _FakeGrobidClient=_FakeGrobidClient,
)