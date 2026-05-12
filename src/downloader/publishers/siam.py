"""SIAM downloader (Society for Industrial and Applied Mathematics).

Behind Cloudflare. Uses cloudflare_session.py for cookie-based downloads.
PDF pattern: epubs.siam.org/doi/pdf/{doi}
"""
from __future__ import annotations

import logging
from typing import Optional

from downloader.publishers import register
from downloader.publishers.base import PublisherDownloader

logger = logging.getLogger(__name__)


@register
class SIAMDownloader(PublisherDownloader):
    name = "SIAM"
    doi_prefix = "10.1137"
    domain = "epubs.siam.org"
    test_doi = "10.1137/23M1622660"

    def _get_pdf_url(self, doi: str) -> Optional[str]:
        """Direct PDF URL — needs Cloudflare cookies."""
        return f"https://epubs.siam.org/doi/pdf/{doi}"

    def download(self, doi, output_dir, *, session=None):
        """Try Cloudflare session cookies, then ETH auth."""
        try:
            from downloader.cloudflare_session import download_with_cookies
            result = download_with_cookies("siam", doi, output_dir)
            if result:
                return result
        except Exception as exc:
            logger.debug("SIAM cloudflare download failed for %s: %s", doi, exc)

        result = super().download(doi, output_dir, session=session)
        if result:
            return result

        try:
            from downloader.eth_institutional import download_sync
            return download_sync(doi, output_dir)
        except Exception:
            return None
