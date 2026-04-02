#!/usr/bin/env python3
"""
ArXiv API Client
Extracted from parsers.pdf_parser.py - Handles ArXiv API integration
"""

import logging
import re
import time
from typing import Optional, Dict, Any, List
from urllib.parse import quote
from urllib.request import urlopen
from urllib.error import HTTPError, URLError
import defusedxml.ElementTree as ET

from .xml_parser import XMLParser

logger = logging.getLogger(__name__)


class ArxivAPIClient:
    """Enhanced ArXiv API client with caching and error handling"""
    
    def __init__(self, api_available: bool = True):
        """Initialize ArXiv API client"""
        self.api_available = api_available
        self.base_url = "http://export.arxiv.org/api/query"
        self.xml_parser = XMLParser()
        self.cache = {}
        self.request_delay = 1.0  # Rate limiting
        self.last_request_time = 0.0
        
        if not api_available:
            logger.info("ArXiv API disabled by configuration")
    
    def search_by_title(self, title: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search ArXiv by title
        
        Args:
            title: Paper title to search for
            max_results: Maximum number of results to return
            
        Returns:
            List of paper metadata dictionaries
        """
        if not self.api_available:
            return []
        
        # Clean title for search
        clean_title = self._clean_title_for_search(title)
        if not clean_title:
            return []
        
        # Check cache first
        cache_key = f"title:{clean_title}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            # Rate limiting
            self._wait_for_rate_limit()
            
            # Build query
            query = f"ti:\"{clean_title}\""
            url = f"{self.base_url}?search_query={quote(query)}&start=0&max_results={max_results}"
            
            logger.debug(f"Searching ArXiv with query: {query}")
            
            # Validate URL scheme for security
            if not url.startswith(('http://', 'https://')):
                raise ValueError("Only HTTP(S) URLs are allowed")
            
            # Make request
            response = urlopen(url, timeout=10)  # nosec B310 - URL validated above for HTTP/HTTPS only
            xml_content = response.read().decode('utf-8')
            
            # Parse results
            results = self._parse_search_results(xml_content)
            
            # Cache results
            self.cache[cache_key] = results
            
            return results
            
        except (HTTPError, URLError) as e:
            logger.warning(f"ArXiv API request failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in ArXiv search: {e}")
            return []
    
    def search_by_id(self, arxiv_id: str) -> Optional[Dict[str, Any]]:
        """
        Search ArXiv by ArXiv ID
        
        Args:
            arxiv_id: ArXiv paper ID (e.g., "1234.5678" or "math.GT/0309136")
            
        Returns:
            Paper metadata dictionary or None
        """
        if not self.api_available:
            return None
        
        # Clean and validate ArXiv ID
        clean_id = self._clean_arxiv_id(arxiv_id)
        if not clean_id:
            return None
        
        # Check cache first
        cache_key = f"id:{clean_id}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            # Rate limiting
            self._wait_for_rate_limit()
            
            # Build query
            query = f"id:{clean_id}"
            url = f"{self.base_url}?search_query={quote(query)}&start=0&max_results=1"
            
            logger.debug(f"Searching ArXiv with ID: {clean_id}")
            
            # Validate URL scheme for security
            if not url.startswith(('http://', 'https://')):
                raise ValueError("Only HTTP(S) URLs are allowed")
            
            # Make request
            response = urlopen(url, timeout=10)  # nosec B310 - URL validated above for HTTP/HTTPS only
            xml_content = response.read().decode('utf-8')
            
            # Parse results
            results = self._parse_search_results(xml_content)
            result = results[0] if results else None
            
            # Cache result
            self.cache[cache_key] = result
            
            return result
            
        except (HTTPError, URLError) as e:
            logger.warning(f"ArXiv API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in ArXiv search: {e}")
            return None
    
    def _clean_title_for_search(self, title: str) -> str:
        """Clean title for ArXiv search"""
        if not title:
            return ""
        
        # Remove common artifacts
        title = re.sub(r'\[.*?\]', '', title)  # Remove [cs.LG] etc.
        title = re.sub(r'\(.*?\)', '', title)  # Remove parentheses
        title = re.sub(r'\s+', ' ', title)     # Normalize whitespace
        title = title.strip()
        
        # Remove non-alphanumeric except spaces, hyphens, colons
        title = re.sub(r'[^a-zA-Z0-9\s\-:]+', '', title)
        
        return title
    
    def _clean_arxiv_id(self, arxiv_id: str) -> str:
        """Clean and validate ArXiv ID"""
        if not arxiv_id:
            return ""
        
        # Remove common prefixes
        arxiv_id = re.sub(r'^arxiv:', '', arxiv_id, flags=re.IGNORECASE)
        arxiv_id = re.sub(r'^arXiv:', '', arxiv_id)
        
        # Validate format
        # New format: YYMM.NNNN[vN]
        if re.match(r'^\d{4}\.\d{4}(v\d+)?$', arxiv_id):
            return arxiv_id
        
        # Old format: subject-class/YYMMnnn
        if re.match(r'^[a-z-]+(\.[A-Z]{2})?/\d{7}$', arxiv_id):
            return arxiv_id
        
        logger.warning(f"Invalid ArXiv ID format: {arxiv_id}")
        return ""
    
    def _wait_for_rate_limit(self):
        """Implement rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.request_delay:
            time.sleep(self.request_delay - time_since_last)
        
        self.last_request_time = time.time()
    
    def _parse_search_results(self, xml_content: str) -> List[Dict[str, Any]]:
        """Parse ArXiv API XML response"""
        try:
            root = ET.fromstring(xml_content)
            results = []
            
            # Find all entry elements
            entries = root.findall('.//{http://www.w3.org/2005/Atom}entry')
            
            for entry in entries:
                paper_data = self.xml_parser.parse_arxiv_entry(entry)
                if paper_data:
                    results.append(paper_data)
            
            return results
            
        except ET.ParseError as e:
            logger.error(f"Failed to parse ArXiv XML: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error parsing ArXiv results: {e}")
            return []
    
    def extract_arxiv_id_from_text(self, text: str) -> Optional[str]:
        """Extract ArXiv ID from text"""
        if not text:
            return None
        
        # Look for various ArXiv ID patterns
        patterns = [
            r'arxiv:(\d{4}\.\d{4}(?:v\d+)?)',          # New format with prefix
            r'arXiv:(\d{4}\.\d{4}(?:v\d+)?)',          # New format with prefix
            r'(\d{4}\.\d{4}(?:v\d+)?)',                # New format without prefix
            r'arxiv:([a-z-]+(?:\.[A-Z]{2})?/\d{7})',   # Old format with prefix
            r'arXiv:([a-z-]+(?:\.[A-Z]{2})?/\d{7})',   # Old format with prefix
            r'([a-z-]+(?:\.[A-Z]{2})?/\d{7})',         # Old format without prefix
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                arxiv_id = match.group(1)
                # Validate the extracted ID
                if self._clean_arxiv_id(arxiv_id):
                    return arxiv_id
        
        return None
    
    def clear_cache(self):
        """Clear the API cache"""
        self.cache.clear()
    
    def get_cache_size(self) -> int:
        """Get current cache size"""
        return len(self.cache)