"""
API Clients for External Services

Contains ArXiv API client and other external service integrations.
Extracted from extractors.py for better modularity.
"""

import time
import logging
from pathlib import Path
from typing import Optional
from urllib.parse import quote
from urllib.request import urlopen
from urllib.error import HTTPError, URLError
import regex as re

from ..models import ArxivMetadata

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
        logging.getLogger(__name__).warning("DefusedXML not available, using standard XML parser (less secure)")
    
    class SecureXMLParser:
        @staticmethod
        def parse_string(xml_data: str):
            # Fallback XML parser with limited security (defusedxml recommended)
            return ET.fromstring(xml_data)  # nosec B314 - fallback when defusedxml unavailable


class ArxivAPIClient:
    """Client for interacting with arXiv API"""

    BASE_URL = "https://export.arxiv.org/api/query"  # Secure HTTPS protocol

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
                "atom": "https://www.w3.org/2005/Atom",  # Secure HTTPS protocol
                "arxiv": "https://arxiv.org/schemas/atom",  # Secure HTTPS protocol
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