"""AMS (American Mathematical Society) downloader.

AMS PDF URLs redirect to LibLynx WAYF for institutional access.
Direct PDF pattern: www.ams.org/journals/{journal}/{year}-{vol}-{issue}/{id}/{id}.pdf
Paywalled papers need ETH auth via ETH institutional downloader.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import requests

from downloader.publishers import register
from downloader.publishers.base import PublisherDownloader, HEADERS


@register
class AMSDownloader(PublisherDownloader):
    name = "AMS"
    doi_prefix = "10.1090"
    domain = "pubs.ams.org"
    test_doi = "10.1090/proc/16801"

    def _get_pdf_url(self, doi: str) -> Optional[str]:
        """Build AMS PDF URL from DOI.

        Pattern: www.ams.org/journals/{journal}/{year}-{vol}-{issue}/{id}/{id}.pdf
        Note: this URL will redirect to LibLynx WAYF if paywalled.
        """
        try:
            resp = requests.get(
                f"https://doi.org/{doi}",
                headers=HEADERS, timeout=15, allow_redirects=True,
            )
            if resp.status_code != 200 or "ams.org" not in resp.url:
                return None

            match = re.search(r"(S\d{4}-\d{4}-\d{4}-\d{5}-\w+)", resp.url)
            if match:
                article_id = match.group(1)
                path_match = re.search(
                    r"(/journals/.+/" + re.escape(article_id) + r")", resp.url
                )
                if path_match:
                    return f"https://www.ams.org{path_match.group(1)}/{article_id}.pdf"
        except Exception as exc:
            logger.debug("AMS URL construction failed for %s: %s", doi, exc)
        return None

    def download(self, doi, output_dir, *, session=None):
        """Try direct first, fall back to ETH institutional."""
        result = super().download(doi, output_dir, session=session)
        if result:
            return result

        # AMS paywalled → try ETH auth
        try:
            from downloader.eth_institutional import download_sync
            return download_sync(doi, output_dir)
        except Exception:
            return None
