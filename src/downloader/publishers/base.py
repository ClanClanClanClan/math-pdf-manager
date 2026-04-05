"""Base class for all publisher downloaders."""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

RATE_LIMIT = 1.0  # seconds between requests


class PublisherDownloader:
    """Base class for publisher-specific PDF downloaders.

    Subclasses must set:
        name: str
        doi_prefix: str (or tuple of prefixes)
        domain: str
        test_doi: str — a known-good DOI for self-testing

    And implement:
        _get_pdf_url(doi) — return the PDF URL for a DOI
        or override download() for more complex flows.
    """

    name: str = ""
    doi_prefix: str = ""
    domain: str = ""
    test_doi: str = ""

    def can_handle(self, doi: str) -> bool:
        """Check if this publisher handles this DOI."""
        if isinstance(self.doi_prefix, tuple):
            return any(doi.startswith(p) for p in self.doi_prefix)
        return doi.startswith(self.doi_prefix)

    def _get_pdf_url(self, doi: str) -> Optional[str]:
        """Return the direct PDF URL for a DOI. Override in subclass."""
        return None

    def download(
        self, doi: str, output_dir: Path, *, session: Optional[requests.Session] = None
    ) -> Optional[Path]:
        """Download the PDF for a DOI.

        Returns path to downloaded PDF, or None if failed.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_doi = re.sub(r"[/\\:]", "_", doi)
        output_path = output_dir / f"{safe_doi}.pdf"

        time.sleep(RATE_LIMIT)

        pdf_url = self._get_pdf_url(doi)
        if not pdf_url:
            return None

        sess = session or requests.Session()
        sess.headers.update(HEADERS)

        try:
            resp = sess.get(pdf_url, timeout=30, allow_redirects=True)
            ct = resp.headers.get("content-type", "").lower()

            if "pdf" in ct and len(resp.content) > 1000:
                output_path.write_bytes(resp.content)
                if self._is_valid_pdf(output_path):
                    logger.info("%s: downloaded %s (%d KB)", self.name, doi, len(resp.content) // 1024)
                    return output_path
                output_path.unlink(missing_ok=True)

        except Exception as exc:
            logger.debug("%s: download failed for %s: %s", self.name, doi, exc)

        return None

    def test(self) -> bool:
        """Self-test: try to download the test DOI."""
        if not self.test_doi:
            logger.warning("%s: no test DOI configured", self.name)
            return False

        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            path = self.download(self.test_doi, Path(tmpdir))
            if path and self._is_valid_pdf(path):
                logger.info("%s: test PASSED (%d KB)", self.name, path.stat().st_size // 1024)
                return True

        logger.warning("%s: test FAILED", self.name)
        return False

    @staticmethod
    def _is_valid_pdf(path: Path) -> bool:
        if not path.exists() or path.stat().st_size < 100:
            return False
        with open(path, "rb") as f:
            return f.read(4) == b"%PDF"
