"""
Author extraction and parsing

This module handles extraction of author information from various sources
including filenames, PDF metadata, and content.
"""
import re
from typing import List, Optional
import logging

from core.models import Author

logger = logging.getLogger(__name__)


class AuthorExtractor:
    """Extract and parse author information"""
    
    # Common author patterns
    PATTERNS = {
        'last_first': re.compile(
            r'(?P<last>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*'
            r'(?P<first>[A-Z](?:[a-z]+|\.)(?:\s+[A-Z](?:[a-z]+|\.))*)'
        ),
        'first_last': re.compile(
            r'(?P<first>[A-Z](?:[a-z]+|\.)(?:\s+[A-Z](?:[a-z]+|\.))*)\s+'
            r'(?P<last>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        ),
        'initials_last': re.compile(
            r'(?P<initials>(?:[A-Z]\.(?:\s*[A-Z]\.)*)+)\s*'
            r'(?P<last>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        ),
    }
    
    def extract_from_filename(self, filename: str) -> List[Author]:
        """Extract authors from filename"""
        # Assume "Authors - Title.pdf" format
        if ' - ' not in filename:
            return []
        
        author_part = filename.split(' - ')[0]
        return self.parse_author_string(author_part)
    
    def parse_author_string(self, author_string: str) -> List[Author]:
        """Parse a string containing one or more authors"""
        authors = []
        
        # Split by common separators
        parts = re.split(r',\s*and\s*|;\s*|\s+and\s+|\s*&\s*', author_string)
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            author = self._parse_single_author(part)
            if author:
                authors.append(author)
        
        return authors
    
    def _parse_single_author(self, author_str: str) -> Optional[Author]:
        """Parse a single author string"""
        author_str = author_str.strip()
        
        # Try each pattern
        for pattern_name, pattern in self.PATTERNS.items():
            match = pattern.match(author_str)
            if match:
                return self._create_author_from_match(match, pattern_name)
        
        # Fallback: treat as full name
        return Author(full_name=author_str)
    
    def _create_author_from_match(self, match, pattern_name: str) -> Author:
        """Create Author object from regex match"""
        groups = match.groupdict()
        
        if pattern_name == 'last_first':
            return Author(
                family_name=groups['last'],
                given_name=groups['first'],
                full_name=match.group(0)
            )
        elif pattern_name == 'first_last':
            return Author(
                given_name=groups['first'],
                family_name=groups['last'],
                full_name=match.group(0)
            )
        elif pattern_name == 'initials_last':
            return Author(
                initials=groups['initials'],
                family_name=groups['last'],
                full_name=match.group(0)
            )
        
        return Author(full_name=match.group(0))
