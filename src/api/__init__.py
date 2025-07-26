"""
API Clients Module
Extracted from src.parsers.pdf_parser.py to handle external API integrations
"""

from .arxiv_client import ArxivAPIClient
from .xml_parser import XMLParser

__all__ = [
    'ArxivAPIClient',
    'XMLParser'
]