"""Standardized publisher download registry.

Every publisher implements the same interface:
- can_handle(doi) — does this publisher handle this DOI?
- download(doi, output_path) — download the PDF
- test() — self-test with a known DOI

Usage::

    from downloader.publishers import get_publisher, download_by_publisher

    # Get specific publisher
    pub = get_publisher("10.1007/s00245-025-10368-x")
    if pub:
        path = pub.download(doi, output_dir)

    # Or try all matching publishers
    path = download_by_publisher(doi, output_dir)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Registry of all publisher downloaders
_REGISTRY: list = []


def register(publisher_class):
    """Register a publisher downloader class."""
    _REGISTRY.append(publisher_class())
    return publisher_class


def get_publisher(doi: str):
    """Get the publisher downloader that handles this DOI."""
    for pub in _REGISTRY:
        if pub.can_handle(doi):
            return pub
    return None


def download_by_publisher(doi: str, output_dir: Path) -> Optional[Path]:
    """Try to download a PDF using the matching publisher."""
    pub = get_publisher(doi)
    if pub:
        return pub.download(doi, output_dir)
    return None


def list_publishers() -> list:
    """List all registered publishers."""
    return [(p.name, p.doi_prefix, p.domain) for p in _REGISTRY]


# Import all publisher modules to trigger registration
from downloader.publishers.springer import SpringerDownloader  # noqa: F401, E402
from downloader.publishers.euclid import EuclidDownloader  # noqa: F401, E402
from downloader.publishers.mdpi import MDPIDownloader  # noqa: F401, E402
from downloader.publishers.centre_mersenne import CentreMersenneDownloader  # noqa: F401, E402
from downloader.publishers.edp_sciences import EDPSciencesDownloader  # noqa: F401, E402
from downloader.publishers.ams import AMSDownloader  # noqa: F401, E402
