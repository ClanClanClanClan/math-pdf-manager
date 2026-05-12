"""EMS Press downloader. Direct PDF link on article page."""
from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from downloader.publishers import register
from downloader.publishers.base import PublisherDownloader, HEADERS

logger = logging.getLogger(__name__)


@register
class EMSPressDownloader(PublisherDownloader):
    name = "EMS Press"
    doi_prefix = "10.4171"
    domain = "ems.press"
    test_doi = "10.4171/jems/1554"

    def _get_pdf_url(self, doi: str) -> Optional[str]:
        try:
            resp = requests.get(
                f"https://doi.org/{doi}", headers=HEADERS,
                timeout=15, allow_redirects=True,
            )
            if resp.status_code != 200 or "ems.press" not in resp.url:
                return None

            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                text = a.get_text(strip=True).lower()
                if "download pdf" in text or "pdf" in text:
                    href = a["href"]
                    if "content" in href or "pdf" in href:
                        return urljoin(resp.url, href)
        except Exception as exc:
            logger.debug("EMS Press failed for %s: %s", doi, exc)
        return None
