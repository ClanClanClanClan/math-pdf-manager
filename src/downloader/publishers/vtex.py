"""VTeX (Modern Stochastics: Theory and Applications) downloader.

Fully open access. PDF link on article page.
"""
from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from downloader.publishers import register
from downloader.publishers.base import PublisherDownloader, HEADERS

logger = logging.getLogger(__name__)


@register
class VTeXDownloader(PublisherDownloader):
    name = "VTeX"
    doi_prefix = "10.15559"
    domain = "vmsta.org"
    test_doi = "10.15559/22-VMSTA212"

    def _get_pdf_url(self, doi: str) -> Optional[str]:
        """Resolve DOI and find PDF link on VMSTA article page."""
        try:
            resp = requests.get(
                f"https://doi.org/{doi}", headers=HEADERS,
                timeout=15, allow_redirects=True,
            )
            if resp.status_code != 200:
                return None

            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                text = a.get_text(strip=True).lower()
                if "pdf" in text and "file/pdf" in href:
                    return urljoin(resp.url, href)

        except Exception as exc:
            logger.debug("VTeX failed for %s: %s", doi, exc)
        return None
