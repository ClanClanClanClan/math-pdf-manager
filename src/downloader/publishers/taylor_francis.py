"""Taylor & Francis downloader.

Behind Cloudflare. Uses cloudflare_session.py for cookie-based downloads.
PDF pattern: tandfonline.com/doi/pdf/{doi}
"""
from __future__ import annotations

import logging
from typing import Optional

from downloader.publishers import register
from downloader.publishers.base import PublisherDownloader

logger = logging.getLogger(__name__)


@register
class TaylorFrancisDownloader(PublisherDownloader):
    name = "Taylor & Francis"
    doi_prefix = "10.1080"
    domain = "tandfonline.com"
    test_doi = "10.1080/03605302.2024.2389372"

    def _get_pdf_url(self, doi: str) -> Optional[str]:
        """Direct PDF URL — needs Cloudflare cookies."""
        return f"https://www.tandfonline.com/doi/pdf/{doi}"

    def download(self, doi, output_dir, *, session=None):
        """Try Cloudflare cookies, then ETH auth."""
        try:
            from downloader.cloudflare_session import download_with_cookies
            result = download_with_cookies("taylor_francis", doi, output_dir)
            if result:
                return result
        except Exception as exc:
            logger.debug("Taylor & Francis cloudflare download failed for %s: %s", doi, exc)

        result = super().download(doi, output_dir, session=session)
        if result:
            return result

        try:
            from downloader.eth_institutional import download_sync
            return download_sync(doi, output_dir)
        except Exception:
            return None
