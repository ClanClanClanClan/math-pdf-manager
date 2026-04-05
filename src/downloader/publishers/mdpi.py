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
        # MDPI blocks /pdf endpoint for automated requests.
        # But CrossRef often has a direct "unspecified" content-type link
        # that actually serves the PDF. Also try the /pdf endpoint with
        # a version parameter.
        try:
            # Strategy 1: CrossRef API for PDF link
            cr_resp = requests.get(
                f"https://api.crossref.org/works/{doi}",
                headers=HEADERS, timeout=10,
            )
            if cr_resp.status_code == 200:
                links = cr_resp.json().get("message", {}).get("link", [])
                for link in links:
                    # MDPI lists links as "unspecified" content-type
                    url = link.get("URL", "")
                    if "mdpi.com" in url and "pdf" in url:
                        return url

            # Strategy 2: Resolve DOI, construct PDF URL
            resp = requests.get(
                f"https://doi.org/{doi}",
                headers=HEADERS, timeout=15, allow_redirects=True,
            )
            if resp.status_code == 200 and "mdpi.com" in resp.url:
                # Try /pdf with version=1 (may work)
                return resp.url.rstrip("/") + "/pdf?version=1"

        except requests.RequestException as exc:
            logger.debug("MDPI request failed for %s: %s", doi, exc)
        except Exception as exc:
            logger.debug("MDPI failed for %s: %s", doi, exc)
        return None
