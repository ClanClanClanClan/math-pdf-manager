"""Oxford University Press downloader.

PDF URL pattern: academic.oup.com/{journal}/article-pdf/{...}
Most papers are paywalled; needs ETH Shibboleth auth.
"""
from __future__ import annotations

import logging
from typing import Optional

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from downloader.publishers import register
from downloader.publishers.base import PublisherDownloader, HEADERS

logger = logging.getLogger(__name__)


@register
class OxfordDownloader(PublisherDownloader):
    name = "Oxford"
    doi_prefix = "10.1093"
    domain = "academic.oup.com"
    test_doi = "10.1093/imrn/rnae042"

    def _get_pdf_url(self, doi: str) -> Optional[str]:
        """OUP blocks automated requests (403). ETH auth is primary strategy."""
        # OUP returns 403 for requests without institutional cookies.
        # Don't waste time with _get_pdf_url — go straight to ETH auth.
        return None

    def download(self, doi, output_dir, *, session=None):
        """Oxford is paywalled — use ETH institutional auth directly."""
        try:
            from downloader.eth_institutional import download_sync
            return download_sync(doi, output_dir)
        except Exception:
            return None
