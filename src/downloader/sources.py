#!/usr/bin/env python3
"""
Academic Paper Download Sources
Comprehensive collection of paper sources with priority routing.

Sources:
1. Open Access (no auth required)
2. Publishers (institutional auth)
3. Alternative Access (fallback)
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum
import urllib.parse


class SourceType(Enum):
    """Types of academic sources."""
    OPEN_ACCESS = "open_access"
    PUBLISHER = "publisher"
    PREPRINT = "preprint"
    ALTERNATIVE = "alternative"
    INSTITUTIONAL = "institutional"


@dataclass
class DownloadSource:
    """Information about a download source."""
    name: str
    base_url: str
    source_type: SourceType
    priority: int  # Lower = higher priority
    requires_auth: bool = False
    rate_limit: float = 1.0  # Seconds between requests
    
    def build_url(self, identifier: str) -> Optional[str]:
        """Build download URL for this source."""
        return None  # Override in subclasses


class SourceRegistry:
    """Registry of all download sources."""
    
    def __init__(self):
        self.sources: List[DownloadSource] = []
        self._initialize_sources()
    
    def _initialize_sources(self):
        """Initialize all known sources."""
        
        # Open Access Sources (Priority 1-10)
        self.sources.extend([
            ArXivSource(),
            BioRxivSource(),
            SSRNSource(),
            RePEcSource(),
            PMCSource(),
            OpenAccessButtonSource(),
        ])
        
        # Publisher Sources (Priority 11-20)
        self.sources.extend([
            SpringerSource(),
            ElsevierSource(),
            IEEESource(),
            ACMSource(),
            WileySource(),
            TaylorFrancisSource(),
            NatureSource(),
            ScienceDirectSource(),
            JSторSource(),
            CambridgeSource(),
        ])
        
        # Alternative Access (Priority 21-30)
        self.sources.extend([
            SciHubSource(),
            AnnasArchiveSource(),
            LibGenSource(),
            ZLibrarySource(),
        ])
    
    def get_sources_for_identifier(self, identifier: str) -> List[DownloadSource]:
        """Get applicable sources for an identifier, sorted by priority."""
        applicable = []
        
        for source in self.sources:
            if source.can_handle(identifier):
                applicable.append(source)
        
        # Sort by priority (lower number = higher priority)
        applicable.sort(key=lambda s: s.priority)
        return applicable


# Base Classes

class BaseSource(DownloadSource):
    """Base class for download sources."""
    
    def can_handle(self, identifier: str) -> bool:
        """Check if this source can handle the identifier."""
        return False  # Override in subclasses


# Open Access Sources

class ArXivSource(BaseSource):
    def __init__(self):
        super().__init__(
            name="ArXiv",
            base_url="https://arxiv.org",
            source_type=SourceType.OPEN_ACCESS,
            priority=1,
            requires_auth=False,
            rate_limit=1.0
        )
    
    def can_handle(self, identifier: str) -> bool:
        return bool(re.search(r'arxiv|(\d{4}\.\d{4,5})', identifier.lower()))
    
    def build_url(self, identifier: str) -> Optional[str]:
        # Extract ArXiv ID
        match = re.search(r'(\d{4}\.\d{4,5})', identifier)
        if match:
            arxiv_id = match.group(1)
            return f"{self.base_url}/pdf/{arxiv_id}.pdf"
        return None


class BioRxivSource(BaseSource):
    def __init__(self):
        super().__init__(
            name="bioRxiv",
            base_url="https://www.biorxiv.org",
            source_type=SourceType.PREPRINT,
            priority=2,
            requires_auth=False,
            rate_limit=1.0
        )
    
    def can_handle(self, identifier: str) -> bool:
        return 'biorxiv' in identifier.lower()


class SSRNSource(BaseSource):
    def __init__(self):
        super().__init__(
            name="SSRN",
            base_url="https://papers.ssrn.com",
            source_type=SourceType.PREPRINT,
            priority=3,
            requires_auth=False,
            rate_limit=1.5
        )
    
    def can_handle(self, identifier: str) -> bool:
        return 'ssrn' in identifier.lower() or bool(re.search(r'abstract=\d+', identifier))


class RePEcSource(BaseSource):
    def __init__(self):
        super().__init__(
            name="RePEc",
            base_url="https://ideas.repec.org",
            source_type=SourceType.OPEN_ACCESS,
            priority=4,
            requires_auth=False,
            rate_limit=1.0
        )
    
    def can_handle(self, identifier: str) -> bool:
        return 'repec' in identifier.lower()


class PMCSource(BaseSource):
    def __init__(self):
        super().__init__(
            name="PubMed Central",
            base_url="https://www.ncbi.nlm.nih.gov/pmc",
            source_type=SourceType.OPEN_ACCESS,
            priority=5,
            requires_auth=False,
            rate_limit=1.0
        )
    
    def can_handle(self, identifier: str) -> bool:
        return 'pmc' in identifier.lower() or 'pubmed' in identifier.lower()


class OpenAccessButtonSource(BaseSource):
    def __init__(self):
        super().__init__(
            name="Open Access Button",
            base_url="https://openaccessbutton.org",
            source_type=SourceType.OPEN_ACCESS,
            priority=6,
            requires_auth=False,
            rate_limit=2.0
        )
    
    def can_handle(self, identifier: str) -> bool:
        # Can try any DOI or title
        return 'doi' in identifier.lower() or '10.' in identifier


# Publisher Sources (require institutional login)

class SpringerSource(BaseSource):
    def __init__(self):
        super().__init__(
            name="Springer",
            base_url="https://link.springer.com",
            source_type=SourceType.PUBLISHER,
            priority=11,
            requires_auth=True,
            rate_limit=2.0
        )
    
    def can_handle(self, identifier: str) -> bool:
        return 'springer' in identifier.lower() or '10.1007' in identifier
    
    def build_url(self, identifier: str) -> Optional[str]:
        # Handle Springer DOIs
        if '10.1007' in identifier:
            # DOI format: 10.1007/978-3-319-12345-6_7
            doi_part = identifier.split('10.1007/')[-1]
            return f"https://link.springer.com/content/pdf/10.1007/{doi_part}.pdf"
        elif 'springer' in identifier.lower():
            # Try to use as-is if it's already a Springer URL
            if 'link.springer.com' in identifier:
                return identifier.replace('/chapter/', '/content/pdf/').replace('/article/', '/content/pdf/') + '.pdf'
        return None


class ElsevierSource(BaseSource):
    def __init__(self):
        super().__init__(
            name="Elsevier",
            base_url="https://www.sciencedirect.com",
            source_type=SourceType.PUBLISHER,
            priority=12,
            requires_auth=True,
            rate_limit=2.0
        )
    
    def can_handle(self, identifier: str) -> bool:
        return 'elsevier' in identifier.lower() or 'sciencedirect' in identifier.lower()


class IEEESource(BaseSource):
    def __init__(self):
        super().__init__(
            name="IEEE Xplore",
            base_url="https://ieeexplore.ieee.org",
            source_type=SourceType.PUBLISHER,
            priority=13,
            requires_auth=True,
            rate_limit=2.0
        )
    
    def can_handle(self, identifier: str) -> bool:
        return 'ieee' in identifier.lower() or '10.1109' in identifier
    
    def build_url(self, identifier: str) -> Optional[str]:
        # Extract IEEE DOI or paper ID
        if '10.1109' in identifier:
            # DOI format: try direct PDF access
            return f"https://ieeexplore.ieee.org/stampPDF/getPDF.jsp?tp=&isnumber=&arnumber=&ref="
        elif 'ieee' in identifier.lower():
            # Try to extract paper number
            import re
            match = re.search(r'(\d{6,8})', identifier)
            if match:
                paper_id = match.group(1)
                return f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={paper_id}"
        return None


class ACMSource(BaseSource):
    def __init__(self):
        super().__init__(
            name="ACM Digital Library",
            base_url="https://dl.acm.org",
            source_type=SourceType.PUBLISHER,
            priority=14,
            requires_auth=True,
            rate_limit=2.0
        )
    
    def can_handle(self, identifier: str) -> bool:
        return 'acm.org' in identifier.lower() or '10.1145' in identifier


class WileySource(BaseSource):
    def __init__(self):
        super().__init__(
            name="Wiley",
            base_url="https://onlinelibrary.wiley.com",
            source_type=SourceType.PUBLISHER,
            priority=15,
            requires_auth=True,
            rate_limit=2.0
        )
    
    def can_handle(self, identifier: str) -> bool:
        return 'wiley' in identifier.lower() or '10.1002' in identifier


class TaylorFrancisSource(BaseSource):
    def __init__(self):
        super().__init__(
            name="Taylor & Francis",
            base_url="https://www.tandfonline.com",
            source_type=SourceType.PUBLISHER,
            priority=16,
            requires_auth=True,
            rate_limit=2.0
        )
    
    def can_handle(self, identifier: str) -> bool:
        return 'tandfonline' in identifier.lower() or '10.1080' in identifier


class NatureSource(BaseSource):
    def __init__(self):
        super().__init__(
            name="Nature",
            base_url="https://www.nature.com",
            source_type=SourceType.PUBLISHER,
            priority=17,
            requires_auth=True,
            rate_limit=2.0
        )
    
    def can_handle(self, identifier: str) -> bool:
        return 'nature.com' in identifier.lower() or '10.1038' in identifier


class ScienceDirectSource(BaseSource):
    def __init__(self):
        super().__init__(
            name="ScienceDirect",
            base_url="https://www.sciencedirect.com",
            source_type=SourceType.PUBLISHER,
            priority=18,
            requires_auth=True,
            rate_limit=2.0
        )
    
    def can_handle(self, identifier: str) -> bool:
        return 'sciencedirect' in identifier.lower()


class JSторSource(BaseSource):
    def __init__(self):
        super().__init__(
            name="JSTOR",
            base_url="https://www.jstor.org",
            source_type=SourceType.PUBLISHER,
            priority=19,
            requires_auth=True,
            rate_limit=2.0
        )
    
    def can_handle(self, identifier: str) -> bool:
        return 'jstor' in identifier.lower()


class CambridgeSource(BaseSource):
    def __init__(self):
        super().__init__(
            name="Cambridge",
            base_url="https://www.cambridge.org",
            source_type=SourceType.PUBLISHER,
            priority=20,
            requires_auth=True,
            rate_limit=2.0
        )
    
    def can_handle(self, identifier: str) -> bool:
        return 'cambridge.org' in identifier.lower() or '10.1017' in identifier


# Alternative Access Sources

class SciHubSource(BaseSource):
    def __init__(self):
        super().__init__(
            name="Sci-Hub",
            base_url="https://sci-hub.se",  # Current mirror
            source_type=SourceType.ALTERNATIVE,
            priority=21,
            requires_auth=False,
            rate_limit=3.0  # Be respectful
        )
        # Alternative mirrors
        self.mirrors = [
            "https://sci-hub.se",
            "https://sci-hub.st",
            "https://sci-hub.ru",
        ]
    
    def can_handle(self, identifier: str) -> bool:
        # Sci-Hub can handle DOIs and many URLs
        return 'doi' in identifier.lower() or '10.' in identifier or 'http' in identifier
    
    def build_url(self, identifier: str) -> Optional[str]:
        # Sci-Hub accepts DOIs and URLs directly
        return f"{self.base_url}/{identifier}"


class AnnasArchiveSource(BaseSource):
    def __init__(self):
        super().__init__(
            name="Anna's Archive",
            base_url="https://annas-archive.org",
            source_type=SourceType.ALTERNATIVE,
            priority=22,
            requires_auth=False,
            rate_limit=3.0
        )
    
    def can_handle(self, identifier: str) -> bool:
        # Can search by DOI, title, or other identifiers
        return True  # Universal fallback


class LibGenSource(BaseSource):
    def __init__(self):
        super().__init__(
            name="Library Genesis",
            base_url="https://libgen.is",
            source_type=SourceType.ALTERNATIVE,
            priority=23,
            requires_auth=False,
            rate_limit=3.0
        )
        self.mirrors = [
            "https://libgen.is",
            "https://libgen.rs",
            "https://libgen.st",
        ]
    
    def can_handle(self, identifier: str) -> bool:
        return True  # Universal fallback


class ZLibrarySource(BaseSource):
    def __init__(self):
        super().__init__(
            name="Z-Library",
            base_url="https://singlelogin.re",  # Current domain
            source_type=SourceType.ALTERNATIVE,
            priority=24,
            requires_auth=False,
            rate_limit=3.0
        )
    
    def can_handle(self, identifier: str) -> bool:
        return True  # Universal fallback


def get_download_sources(identifier: str) -> List[DownloadSource]:
    """Get prioritized list of download sources for an identifier."""
    registry = SourceRegistry()
    return registry.get_sources_for_identifier(identifier)