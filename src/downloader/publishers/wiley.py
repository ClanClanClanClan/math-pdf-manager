"""Wiley Online Library downloader.

Behind Cloudflare. Uses cloudflare_session.py for cookie-based downloads.
PDF pattern: onlinelibrary.wiley.com/doi/pdfdirect/{doi}
Wiley uses two DOI prefixes: 10.1111 and 10.1002.
"""
from __future__ import annotations

import logging
from typing import Optional

from downloader.publishers import register
from downloader.publishers.base import PublisherDownloader

logger = logging.getLogger(__name__)


@register
class WileyDownloader(PublisherDownloader):
    name = "Wiley"
    doi_prefix = ("10.1111", "10.1002", "10.1112")
    domain = "onlinelibrary.wiley.com"
    test_doi = "10.1111/mafi.12423"

    def _get_pdf_url(self, doi: str) -> Optional[str]:
        """Direct PDF URL — needs Cloudflare cookies."""
        return f"https://onlinelibrary.wiley.com/doi/pdfdirect/{doi}"

    def download(self, doi, output_dir, *, session=None):
        """Try Cloudflare cookies, then ETH auth."""
        try:
            from downloader.cloudflare_session import download_with_cookies
            result = download_with_cookies("wiley", doi, output_dir)
            if result:
                return result
        except Exception as exc:
            logger.debug("Wiley cloudflare download failed for %s: %s", doi, exc)

        result = super().download(doi, output_dir, session=session)
        if result:
            return result

        try:
            from downloader.eth_institutional import download_sync
            return download_sync(doi, output_dir)
        except Exception:
            return None
