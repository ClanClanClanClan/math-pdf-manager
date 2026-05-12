"""
Academic Paper Downloader Module
=====================================

Downloads published academic papers via multiple strategies:

1. Publisher-specific downloaders (19 publishers, DOI-based)
2. DOI downloader (Unpaywall → Publisher → Sci-Hub → ETH Auth)
3. Cloudflare session (semi-automated for SIAM, Elsevier, etc.)
4. ETH institutional auth (Playwright + Shibboleth)

Usage::

    from downloader.doi_downloader import DOIDownloader

    dl = DOIDownloader(unpaywall_email="your@email.com")
    path = dl.download("10.1007/s00245-023-10001-5", Path("/tmp"))
"""

# DOI downloader is the main entry point
try:
    from .doi_downloader import DOIDownloader
except ImportError:
    DOIDownloader = None

# Legacy systems — only import if aiohttp available
try:
    from .proper_downloader import ProperAcademicDownloader, Downloader, DownloadResult
    from .open_access_sources import get_open_access_sources
    LEGACY_AVAILABLE = True
except ImportError:
    LEGACY_AVAILABLE = False

__all__ = ['DOIDownloader']

if LEGACY_AVAILABLE:
    __all__.extend([
        'ProperAcademicDownloader',
        'Downloader',
        'DownloadResult',
        'get_open_access_sources',
    ])
