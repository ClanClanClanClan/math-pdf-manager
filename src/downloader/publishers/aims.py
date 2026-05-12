"""AIMS Press downloader.

AIMS blocks automated PDF downloads (export-pdf returns empty body).
Needs browser-based ETH institutional auth for paywalled papers.
"""
from __future__ import annotations

import logging
from typing import Optional

from downloader.publishers import register
from downloader.publishers.base import PublisherDownloader

logger = logging.getLogger(__name__)


@register
class AIMSDownloader(PublisherDownloader):
    name = "AIMS"
    doi_prefix = "10.3934"
    domain = "aimsciences.org"
    test_doi = "10.3934/dcds.2024022"

    def _get_pdf_url(self, doi: str) -> Optional[str]:
        """AIMS blocks automated PDF downloads (returns empty body).

        export-pdf endpoint requires browser session. ETH auth is primary.
        """
        return None

    def download(self, doi, output_dir, *, session=None):
        """AIMS needs browser-based download — use ETH institutional auth."""
        try:
            from downloader.eth_institutional import download_sync
            return download_sync(doi, output_dir)
        except Exception:
            return None
