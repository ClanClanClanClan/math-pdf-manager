"""Springer Nature downloader.

OA papers: direct PDF link (no auth).
Paywalled: ETH institutional login via WAYF → aai-logon.ethz.ch.

Tested: ✅ Both OA and paywalled downloads work headless.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import requests

from downloader.publishers import register
from downloader.publishers.base import PublisherDownloader, HEADERS


@register
class SpringerDownloader(PublisherDownloader):
    name = "Springer"
    doi_prefix = "10.1007"
    domain = "link.springer.com"
    test_doi = "10.1007/s10690-025-09545-3"  # OA paper

    def _get_pdf_url(self, doi: str) -> Optional[str]:
        return f"https://link.springer.com/content/pdf/{doi}.pdf"

    def download(self, doi, output_dir, *, session=None):
        # Try direct first (works for OA)
        result = super().download(doi, output_dir, session=session)
        if result:
            return result

        # If direct fails, try ETH institutional auth
        try:
            from downloader.eth_institutional import download_sync
            return download_sync(doi, output_dir)
        except Exception:
            return None
