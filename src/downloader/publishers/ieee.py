"""IEEE downloader.

PDF URL pattern: ieeexplore.ieee.org/stampPDF/getPDF.jsp?tp=&arnumber={id}
Also: ieeexplore.ieee.org/stamp/stamp.jsp?arnumber={id}
IEEE often has open access for conference proceedings.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

import requests

from downloader.publishers import register
from downloader.publishers.base import PublisherDownloader, HEADERS

logger = logging.getLogger(__name__)


@register
class IEEEDownloader(PublisherDownloader):
    name = "IEEE"
    doi_prefix = "10.1109"
    domain = "ieeexplore.ieee.org"
    test_doi = "10.1109/TAC.2024.3394273"

    def _get_pdf_url(self, doi: str) -> Optional[str]:
        """Try to extract IEEE article number from CrossRef API.

        IEEE has bot protection on its site, so DOI resolution often fails.
        Use CrossRef to get the article URL, then extract arnumber.
        """
        try:
            # Strategy 1: CrossRef API to find IEEE URL with arnumber
            cr_resp = requests.get(
                f"https://api.crossref.org/works/{doi}",
                headers=HEADERS, timeout=10,
            )
            if cr_resp.status_code == 200:
                data = cr_resp.json().get("message", {})
                # Check resource link
                for link in data.get("link", []):
                    url = link.get("URL", "")
                    match = re.search(r"/document/(\d+)", url)
                    if match:
                        arnumber = match.group(1)
                        return f"https://ieeexplore.ieee.org/stampPDF/getPDF.jsp?tp=&arnumber={arnumber}"

                # Check URL field
                url = data.get("URL", "")
                match = re.search(r"arnumber=(\d+)|/document/(\d+)", url)
                if match:
                    arnumber = match.group(1) or match.group(2)
                    return f"https://ieeexplore.ieee.org/stampPDF/getPDF.jsp?tp=&arnumber={arnumber}"

            # Strategy 2: Try DOI resolution (may fail with bot protection)
            resp = requests.get(
                f"https://doi.org/{doi}", headers=HEADERS,
                timeout=15, allow_redirects=True,
            )
            if resp.status_code == 200 and "ieee.org" in resp.url:
                match = re.search(r"/document/(\d+)", resp.url)
                if match:
                    arnumber = match.group(1)
                    return f"https://ieeexplore.ieee.org/stampPDF/getPDF.jsp?tp=&arnumber={arnumber}"

        except Exception as exc:
            logger.debug("IEEE failed for %s: %s", doi, exc)
        return None

    def download(self, doi, output_dir, *, session=None):
        """Try direct first, fall back to ETH institutional."""
        result = super().download(doi, output_dir, session=session)
        if result:
            return result

        try:
            from downloader.eth_institutional import download_sync
            return download_sync(doi, output_dir)
        except Exception:
            return None
