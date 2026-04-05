"""Centre Mersenne downloader. Open access — direct PDF URL."""
from __future__ import annotations

from typing import Optional

import requests

from downloader.publishers import register
from downloader.publishers.base import PublisherDownloader, HEADERS


@register
class CentreMersenneDownloader(PublisherDownloader):
    name = "Centre Mersenne"
    doi_prefix = "10.5802"
    domain = "centre-mersenne.org"
    test_doi = "10.5802/igt.7"

    def _get_pdf_url(self, doi: str) -> Optional[str]:
        # Centre Mersenne: resolve DOI, then append .pdf
        # Example: 10.5802/igt.7 → https://igt.centre-mersenne.org/item/10.5802/igt.7.pdf
        try:
            resp = requests.get(
                f"https://doi.org/{doi}",
                headers=HEADERS, timeout=15, allow_redirects=True,
            )
            if "centre-mersenne.org" in resp.url:
                # Try /item/{doi}.pdf pattern
                return f"https://{resp.url.split('/')[2]}/item/{doi}.pdf"
        except Exception:
            pass
        return None
