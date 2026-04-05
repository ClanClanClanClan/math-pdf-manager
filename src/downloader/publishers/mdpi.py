"""MDPI downloader. Open access — direct PDF URL."""
from __future__ import annotations

import re
from typing import Optional

import requests

from downloader.publishers import register
from downloader.publishers.base import PublisherDownloader, HEADERS


@register
class MDPIDownloader(PublisherDownloader):
    name = "MDPI"
    doi_prefix = "10.3390"
    domain = "www.mdpi.com"
    test_doi = "10.3390/axioms12080749"

    def _get_pdf_url(self, doi: str) -> Optional[str]:
        # MDPI blocks /pdf without a version param.
        # The download link on the page is: /path/pdf?version=timestamp
        # We can try the CrossRef API to get the PDF link directly.
        try:
            # Try CrossRef for PDF link
            cr_resp = requests.get(
                f"https://api.crossref.org/works/{doi}",
                headers=HEADERS, timeout=10,
            )
            if cr_resp.status_code == 200:
                links = cr_resp.json().get("message", {}).get("link", [])
                for link in links:
                    if link.get("content-type") == "application/pdf":
                        return link["URL"]

            # Fallback: resolve DOI and try with a fake version
            resp = requests.get(
                f"https://doi.org/{doi}",
                headers=HEADERS, timeout=15, allow_redirects=True,
            )
            if "mdpi.com" in resp.url:
                return resp.url.rstrip("/") + "/pdf?version=1"
        except Exception:
            pass
        return None
