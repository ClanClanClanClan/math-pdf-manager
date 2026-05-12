"""IOP Science downloader.

PDF URL pattern: iopscience.iop.org/article/{doi}/pdf
Many papers are open access; paywalled ones need ETH auth.
"""
from __future__ import annotations

import logging
from typing import Optional

from downloader.publishers import register
from downloader.publishers.base import PublisherDownloader

logger = logging.getLogger(__name__)


@register
class IOPDownloader(PublisherDownloader):
    name = "IOP"
    doi_prefix = "10.1088"
    domain = "iopscience.iop.org"
    test_doi = "10.1088/1361-6544/ad7b78"

    def _get_pdf_url(self, doi: str) -> Optional[str]:
        """IOP PDF URL pattern — but blocked by PerformDrive bot detection.

        Direct requests fail. ETH auth is the primary strategy.
        """
        # IOP has bot protection (PerformDrive). Direct URL works
        # only with browser/institutional cookies.
        return None

    def download(self, doi, output_dir, *, session=None):
        """IOP needs ETH institutional auth (PerformDrive bot protection)."""
        try:
            from downloader.eth_institutional import download_sync
            return download_sync(doi, output_dir)
        except Exception:
            return None
