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
        # Also: edpsciences.org, mmnp-journal.org
        # Pattern: /articles/{journal}/abs/{year}/{issue}/{id}/{id}.pdf
        # or: /articles/{journal}/pdf/{year}/{issue}/{id}/{id}.pdf
        try:
            resp = requests.get(
                f"https://doi.org/{doi}",
                headers=HEADERS, timeout=15, allow_redirects=True,
            )
            final_url = resp.url
            # Replace /abs/ with /pdf/ in the URL
            if "/abs/" in final_url:
                pdf_url = final_url.replace("/abs/", "/pdf/")
                # The PDF URL might need .pdf extension or different path
                return pdf_url
            # Try appending /pdf to the URL
            return final_url.rstrip("/") + "/pdf"
        except Exception:
            pass
        return None
