"""EDP Sciences downloader. Many papers are open access (ESAIM journals)."""
from __future__ import annotations

from typing import Optional

import requests

from downloader.publishers import register
from downloader.publishers.base import PublisherDownloader, HEADERS


@register
class EDPSciencesDownloader(PublisherDownloader):
    name = "EDP Sciences"
    doi_prefix = "10.1051"
    domain = "edpsciences.org"
    test_doi = "10.1051/cocv/2023065"

    def _get_pdf_url(self, doi: str) -> Optional[str]:
        # EDP Sciences hosts multiple domains:
        # esaim-cocv.org, esaim-ps.org, esaim-m2an.org, etc.
        # PDF link is on the article page as a relative href like:
        # /articles/cocv/pdf/2023/01/cocv220118.pdf
        try:
            resp = requests.get(
                f"https://doi.org/{doi}",
                headers=HEADERS, timeout=15, allow_redirects=True,
            )
            if resp.status_code != 200:
                return None

            from bs4 import BeautifulSoup
            from urllib.parse import urljoin

            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                text = a.get_text(strip=True).lower()
                if href.lower().endswith(".pdf") and "pdf" in text:
                    return urljoin(resp.url, href)

        except Exception:
            pass
        return None
