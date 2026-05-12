"""Elsevier / ScienceDirect downloader.

Behind Cloudflare. Uses cloudflare_session.py for cookie-based downloads.
Elsevier uses PII-based URLs, not DOI-based PDF links.
Need to resolve DOI → extract PII → construct PDF URL.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from downloader.publishers import register
from downloader.publishers.base import PublisherDownloader, HEADERS

logger = logging.getLogger(__name__)


@register
class ElsevierDownloader(PublisherDownloader):
    name = "Elsevier"
    doi_prefix = "10.1016"
    domain = "sciencedirect.com"
    test_doi = "10.1016/j.spa.2024.104337"

    def _get_pdf_url(self, doi: str) -> Optional[str]:
        """Resolve DOI to ScienceDirect and extract PDF link.

        Elsevier PDF URLs use PII (not DOI):
        sciencedirect.com/science/article/pii/{PII}/pdf
        """
        try:
            resp = requests.get(
                f"https://doi.org/{doi}", headers=HEADERS,
                timeout=15, allow_redirects=True,
            )
            if resp.status_code != 200:
                return None

            # Extract PII from URL
            pii_match = re.search(r"/pii/(\w+)", resp.url)
            if pii_match:
                pii = pii_match.group(1)
                return f"https://www.sciencedirect.com/science/article/pii/{pii}/pdfft"

            # Fallback: look for PDF link in page
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "/pdfft" in href or "pdf" in href.lower():
                    return urljoin(resp.url, href)

        except Exception as exc:
            logger.debug("Elsevier failed for %s: %s", doi, exc)
        return None

    def download(self, doi, output_dir, *, session=None):
        """Try Cloudflare cookies, then ETH auth."""
        try:
            from downloader.cloudflare_session import download_with_cookies
            result = download_with_cookies("elsevier", doi, output_dir)
            if result:
                return result
        except Exception as exc:
            logger.debug("Elsevier cloudflare download failed for %s: %s", doi, exc)

        result = super().download(doi, output_dir, session=session)
        if result:
            return result

        try:
            from downloader.eth_institutional import download_sync
            return download_sync(doi, output_dir)
        except Exception:
            return None
