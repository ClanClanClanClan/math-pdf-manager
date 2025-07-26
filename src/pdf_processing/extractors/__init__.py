"""
PDF Content Extractors Package

Modular extractors for different types of academic papers.
Refactored from monolithic extractors.py for better maintainability.
"""

from .ssrn_extractor import AdvancedSSRNExtractor
from .arxiv_extractor import AdvancedArxivExtractor
from .journal_extractor import AdvancedJournalExtractor
from .api_client import ArxivAPIClient, _FakeGrobidClient

__all__ = [
    'AdvancedSSRNExtractor',
    'AdvancedArxivExtractor', 
    'AdvancedJournalExtractor',
    'ArxivAPIClient',
    '_FakeGrobidClient'
]

# Backward compatibility - provide same interface as original extractors.py
globals().update(
    AdvancedSSRNExtractor=AdvancedSSRNExtractor,
    AdvancedArxivExtractor=AdvancedArxivExtractor,
    AdvancedJournalExtractor=AdvancedJournalExtractor,
    ArxivAPIClient=ArxivAPIClient,
    _FakeGrobidClient=_FakeGrobidClient,
)