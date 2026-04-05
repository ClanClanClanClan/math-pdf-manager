"""Project Euclid / IMS downloader.

Many papers are open access. Direct download button on article page.
Paywalled papers: ETH institutional login via Shibboleth.

Tested: ✅ OA download works headless (561 KB).
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from downloader.publishers import register
from downloader.publishers.base import PublisherDownloader


@register
class EuclidDownloader(PublisherDownloader):
    name = "Project Euclid"
    doi_prefix = ("10.1214", "10.3150")  # IMS + Bernoulli Society
    domain = "projecteuclid.org"
    test_doi = "10.1214/24-ejp1229"  # OA paper

    def _get_pdf_url(self, doi: str) -> Optional[str]:
        # Euclid uses a download endpoint with the DOI
        encoded = doi.replace("/", "%2F")
        return f"https://projecteuclid.org/journalArticle/Download?urlid={encoded}"
