"""INFORMS downloader (Mathematics of Operations Research, etc.).

Behind Cloudflare. Uses cloudflare_session.py for cookie-based downloads.
PDF pattern: pubsonline.informs.org/doi/pdf/{doi}
"""
from __future__ import annotations

import logging
from typing import Optional

from downloader.publishers import register
from downloader.publishers.base import PublisherDownloader

logger = logging.getLogger(__name__)


@register
class INFORMSDownloader(PublisherDownloader):
    name = "INFORMS"
    doi_prefix = "10.1287"
    domain = "pubsonline.informs.org"
    test_doi = "10.1287/moor.2023.0211"

    def _get_pdf_url(self, doi: str) -> Optional[str]:
        """Direct PDF URL for INFORMS — but needs Cloudflare cookies."""
        return f"https://pubsonline.informs.org/doi/pdf/{doi}"

    def download(self, doi, output_dir, *, session=None):
        """Try Cloudflare session cookies, then ETH auth."""
        # Try with Cloudflare cookies first
        try:
            from downloader.cloudflare_session import download_with_cookies
            result = download_with_cookies("informs", doi, output_dir)
            if result:
                return result
        except Exception as exc:
            logger.debug("INFORMS cloudflare download failed for %s: %s", doi, exc)

        # Try direct (might work for OA)
        result = super().download(doi, output_dir, session=session)
        if result:
            return result

        # Fall back to ETH auth
        try:
            from downloader.eth_institutional import download_sync
            return download_sync(doi, output_dir)
        except Exception:
            return None
