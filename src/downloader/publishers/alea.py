"""ALEA (Latin American Journal of Probability) downloader.

Fully open access. DOI resolves directly to PDF.
"""
from __future__ import annotations

import logging
from typing import Optional

import requests

from downloader.publishers import register
from downloader.publishers.base import PublisherDownloader, HEADERS

logger = logging.getLogger(__name__)


@register
class ALEADownloader(PublisherDownloader):
    name = "ALEA"
    doi_prefix = "10.30757"
    domain = "alea.impa.br"
    test_doi = "10.30757/ALEA.v20-62"

    def _get_pdf_url(self, doi: str) -> Optional[str]:
        """ALEA DOI resolves directly to PDF — just follow the redirect."""
        try:
            resp = requests.head(
                f"https://doi.org/{doi}", headers=HEADERS,
                timeout=15, allow_redirects=True,
            )
            if resp.status_code == 200 and "alea.impa.br" in resp.url:
                return resp.url
        except Exception as exc:
            logger.debug("ALEA failed for %s: %s", doi, exc)
        # Fallback: construct from DOI
        return f"https://doi.org/{doi}"
