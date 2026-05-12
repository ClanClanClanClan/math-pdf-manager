"""World Scientific downloader.

Behind Cloudflare. Uses cloudflare_session.py for cookie-based downloads.
PDF pattern: worldscientific.com/doi/pdf/{doi}
"""
from __future__ import annotations

import logging
from typing import Optional

from downloader.publishers import register
from downloader.publishers.base import PublisherDownloader

logger = logging.getLogger(__name__)


@register
class WorldScientificDownloader(PublisherDownloader):
    name = "World Scientific"
    doi_prefix = "10.1142"
    domain = "worldscientific.com"
    test_doi = "10.1142/S0219199724500573"

    def _get_pdf_url(self, doi: str) -> Optional[str]:
        """Direct PDF URL — but needs Cloudflare cookies."""
        return f"https://www.worldscientific.com/doi/pdf/{doi}"

    def download(self, doi, output_dir, *, session=None):
        """Try Cloudflare cookies, then ETH auth."""
        try:
            from downloader.cloudflare_session import download_with_cookies
            result = download_with_cookies("world_scientific", doi, output_dir)
            if result:
                return result
        except Exception as exc:
            logger.debug("World Scientific cloudflare download failed for %s: %s", doi, exc)

        result = super().download(doi, output_dir, session=session)
        if result:
            return result

        try:
            from downloader.eth_institutional import download_sync
            return download_sync(doi, output_dir)
        except Exception:
            return None
