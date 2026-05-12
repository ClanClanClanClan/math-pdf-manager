"""Cambridge University Press downloader.

Most papers are paywalled — needs ETH Shibboleth auth.
PDF URL pattern: /core/services/aop-cambridge-core/content/view/{pii}/pdf
Direct construction: cambridge.org/core/journals/.../doi/{doi}

Tested: Paywalled papers need ETH institutional login.
"""
from __future__ import annotations

import logging
from typing import Optional

import requests

from downloader.publishers import register
from downloader.publishers.base import PublisherDownloader, HEADERS

logger = logging.getLogger(__name__)


@register
class CambridgeDownloader(PublisherDownloader):
    name = "Cambridge"
    doi_prefix = "10.1017"
    domain = "cambridge.org"
    test_doi = "10.1017/fms.2024.26"  # Forum of Mathematics, Sigma — OA

    def _get_pdf_url(self, doi: str) -> Optional[str]:
        """Resolve DOI and extract PDF link from Cambridge article page.

        Cambridge PDF links use the pattern:
        /core/services/aop-cambridge-core/content/view/{hash}/{pii}.pdf/title.pdf
        We look for 'save pdf' or 'view pdf' link text.
        """
        try:
            resp = requests.get(
                f"https://doi.org/{doi}", headers=HEADERS,
                timeout=15, allow_redirects=True,
            )
            if resp.status_code != 200 or "cambridge.org" not in resp.url:
                return None

            from bs4 import BeautifulSoup
            from urllib.parse import urljoin

            soup = BeautifulSoup(resp.text, "html.parser")

            # Look for "Save PDF" or "View PDF" link (contains full path)
            for a in soup.find_all("a", href=True):
                href = a["href"]
                text = a.get_text(strip=True).lower()
                if ("save pdf" in text or "view pdf" in text) and ".pdf" in href:
                    return urljoin(resp.url, href)

            # Fallback: any link with /content/view/ and .pdf
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "content/view" in href and ".pdf" in href:
                    return urljoin(resp.url, href)

        except Exception as exc:
            logger.debug("Cambridge failed for %s: %s", doi, exc)
        return None

    def download(self, doi, output_dir, *, session=None):
        """Try direct first, fall back to ETH institutional."""
        result = super().download(doi, output_dir, session=session)
        if result:
            return result

        # Paywalled → ETH auth
        try:
            from downloader.eth_institutional import download_sync
            return download_sync(doi, output_dir)
        except Exception:
            return None
