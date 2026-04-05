"""AMS (American Mathematical Society) downloader.

AMS pages have PDF buttons with onclick='downloadVolume("URL")'.
No Cloudflare. Some papers behind paywall (ETH Shibboleth).
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
        # AMS: resolve DOI, extract article ID, construct PDF URL.
        # URL pattern: pubs.ams.org/journals/{journal}/{year}-{vol}-{issue}/S{issn}-{year}-{id}-{check}
        # PDF pattern: www.ams.org/journals/{journal}/{year}-{vol}-{issue}/{article_id}/{article_id}.pdf
        try:
            resp = requests.get(
                f"https://doi.org/{doi}",
                headers=HEADERS, timeout=15, allow_redirects=True,
            )
            if "ams.org" not in resp.url:
                return None

            # Extract article ID from URL
            match = re.search(r"(S\d{4}-\d{4}-\d{4}-\d{5}-\w+)", resp.url)
            if match:
                article_id = match.group(1)
                # Build the PDF URL using the path from the resolved URL
                # From: https://pubs.ams.org/journals/proc/2025-153-09/S0002-9939-2025-16801-0
                # To:   https://www.ams.org/journals/proc/2025-153-09/S0002-9939-2025-16801-0/S0002-9939-2025-16801-0.pdf
                path_match = re.search(r"(/journals/.+/" + re.escape(article_id) + r")", resp.url)
                if path_match:
                    return f"https://www.ams.org{path_match.group(1)}/{article_id}.pdf"

        except Exception:
            pass
        return None
