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


# Import all publisher modules to trigger registration.
# Each import is wrapped so a single broken module doesn't break the registry.
_MODULES = [
    # Tier 1: Open access — direct download
    ("downloader.publishers.springer", "SpringerDownloader"),
    ("downloader.publishers.euclid", "EuclidDownloader"),
    ("downloader.publishers.mdpi", "MDPIDownloader"),
    ("downloader.publishers.centre_mersenne", "CentreMersenneDownloader"),
    ("downloader.publishers.edp_sciences", "EDPSciencesDownloader"),
    ("downloader.publishers.ems_press", "EMSPressDownloader"),
    # Tier 2: No Cloudflare — direct or ETH Shibboleth
    ("downloader.publishers.ams", "AMSDownloader"),
    ("downloader.publishers.cambridge", "CambridgeDownloader"),
    ("downloader.publishers.aims", "AIMSDownloader"),
    ("downloader.publishers.iop", "IOPDownloader"),
    ("downloader.publishers.degruyter", "DeGruyterDownloader"),
    ("downloader.publishers.oxford", "OxfordDownloader"),
    ("downloader.publishers.ieee", "IEEEDownloader"),
    # Niche OA publishers
    ("downloader.publishers.alea", "ALEADownloader"),
    ("downloader.publishers.vtex", "VTeXDownloader"),
    # Tier 3: Cloudflare protected — semi-automated
    ("downloader.publishers.siam", "SIAMDownloader"),
    ("downloader.publishers.elsevier", "ElsevierDownloader"),
    ("downloader.publishers.wiley", "WileyDownloader"),
    ("downloader.publishers.taylor_francis", "TaylorFrancisDownloader"),
    ("downloader.publishers.informs", "INFORMSDownloader"),
    ("downloader.publishers.world_scientific", "WorldScientificDownloader"),
]

for _mod_name, _cls_name in _MODULES:
    try:
        _mod = __import__(_mod_name, fromlist=[_cls_name])
        # The @register decorator handles registration on import
    except Exception as _exc:
        logger.warning("Failed to load publisher %s: %s", _cls_name, _exc)
