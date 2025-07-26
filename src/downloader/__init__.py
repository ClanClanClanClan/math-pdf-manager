"""
Academic Paper Downloader Module
=====================================

PROPER IMPLEMENTATION - No placeholders, only working sources:

1. Open Access: ArXiv, SSRN, HAL, bioRxiv, PMC (real implementations)
2. Institutional: IEEE, SIAM (existing Shibboleth authentication)
3. Removed: 22 placeholder publisher implementations

This is the honest, working system.
"""

# Main proper implementation
from .proper_downloader import ProperAcademicDownloader, Downloader, DownloadResult
from .open_access_sources import get_open_access_sources

# Legacy systems (deprecated - contain placeholders)
try:
    from .integrated_downloader import IntegratedAcademicDownloader
    from .academic_downloader import AcademicDownloader
    from .sources import get_download_sources, SourceType
    LEGACY_AVAILABLE = True
except ImportError:
    LEGACY_AVAILABLE = False

__all__ = [
    'ProperAcademicDownloader',
    'Downloader', 
    'DownloadResult',
    'get_open_access_sources'
]

# Add legacy exports if available (not recommended)
if LEGACY_AVAILABLE:
    __all__.extend([
        'IntegratedAcademicDownloader',
        'AcademicDownloader', 
        'get_download_sources', 
        'SourceType'
    ])