"""MDPI downloader. Open access — but blocks automated PDF downloads (403).

MDPI is fully open access, but their server returns 403 for automated
requests to PDF URLs. The ETH institutional auth browser-based approach
works because it uses a real browser session.
"""
from __future__ import annotations

import logging
from typing import Optional

from downloader.publishers import register
from downloader.publishers.base import PublisherDownloader

logger = logging.getLogger(__name__)


@register
class MDPIDownloader(PublisherDownloader):
    name = "MDPI"
    doi_prefix = "10.3390"
    domain = "www.mdpi.com"
    test_doi = "10.3390/axioms12080749"

    def _get_pdf_url(self, doi: str) -> Optional[str]:
        """MDPI blocks automated PDF downloads with 403.

        Despite being fully OA, MDPI requires a real browser session.
        ETH auth opens a browser which works around this.
        """
        return None

    def download(self, doi, output_dir, *, session=None):
        """Use ETH institutional auth (browser-based) for MDPI."""
        try:
            from downloader.eth_institutional import download_sync
            return download_sync(doi, output_dir)
        except Exception:
            return None
