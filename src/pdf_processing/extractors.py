"""
PDF Content Extractors - Compatibility Wrapper

This file maintains backward compatibility after refactoring the monolithic
extractors.py into specialized modules.

Original 1,038-line file has been split into:
- extractors/ssrn_extractor.py (SSRN papers)
- extractors/arxiv_extractor.py (ArXiv papers) 
- extractors/journal_extractor.py (Journal papers)
- extractors/api_client.py (ArXiv API and external services)

All imports and functionality remain the same for existing code.
"""

# Import all classes from the new modular structure
from .extractors import (
    AdvancedSSRNExtractor,
    AdvancedArxivExtractor,
    AdvancedJournalExtractor,
    ArxivAPIClient,
    _FakeGrobidClient
)

# Maintain exact same interface as original file
__all__ = [
    'AdvancedSSRNExtractor',
    'AdvancedArxivExtractor',
    'AdvancedJournalExtractor', 
    'ArxivAPIClient',
    '_FakeGrobidClient'
]

# NOTE: Original 1,038-line extractors.py has been successfully refactored
# into 4 specialized modules for better maintainability and testing.
# This wrapper ensures zero breaking changes for existing imports.