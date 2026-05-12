"""De Gruyter downloader.

De Gruyter PDF URL pattern: /document/doi/{doi}/pdf
Many papers are open access. Paywalled papers need ETH auth.

Note: De Gruyter resolved URLs end in /html — replace with /pdf.
"""
from __future__ import annotations

import logging
from typing import Optional

import requests

from downloader.publishers import register
from downloader.publishers.base import PublisherDownloader, HEADERS

logger = logging.getLogger(__name__)


@register
class DeGruyterDownloader(PublisherDownloader):
    name = "De Gruyter"
    doi_prefix = "10.1515"
    domain = "degruyterbrill.com"
    test_doi = "10.1515/math-2024-0058"  # Open Mathematics — OA

    def _get_pdf_url(self, doi: str) -> Optional[str]:
        """Build De Gruyter PDF URL.

        Strategy 1: Direct URL construction (no request needed).
        Strategy 2: Resolve DOI and replace /html with /pdf.
        """
        # Strategy 1: direct construction — most reliable
        return f"https://www.degruyterbrill.com/document/doi/{doi}/pdf"

    def download(self, doi, output_dir, *, session=None):
        """Try direct first, fall back to ETH institutional auth."""
        result = super().download(doi, output_dir, session=session)
        if result:
            return result

        # Paywalled → try ETH auth
        try:
            from downloader.eth_institutional import download_sync
            return download_sync(doi, output_dir)
        except Exception:
            return None
