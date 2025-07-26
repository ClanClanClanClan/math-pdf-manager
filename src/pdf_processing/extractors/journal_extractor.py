"""
Journal PDF Content Extractor

Specialized extractor for academic journal papers with enhanced title extraction.
Extracted from extractors.py for better modularity.
"""

import regex as re
import logging
from typing import Optional, Tuple, List

from ..models import TextBlock, PDFMetadata, MetadataSource
from ..constants import PDFConstants

logger = logging.getLogger(__name__)


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
            repository_type="Journal"
        )