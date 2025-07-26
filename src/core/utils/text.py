#!/usr/bin/env python3
"""
Text processing utilities
Common text operations used across the system
"""

import re
import unicodedata
from typing import List, Optional


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text."""
    if not text:
        return ""
    
    # Replace multiple whitespace with single space
    text = re.sub(r'\s+', ' ', text)
    
    # Strip leading/trailing whitespace
    return text.strip()


def extract_words(text: str, min_length: int = 2) -> List[str]:
    """Extract words from text, filtering by minimum length."""
    if not text:
        return []
    
    # Split on non-word characters but keep hyphens in words
    words = re.findall(r'\b[\w-]+\b', text.lower())
    
    # Filter by minimum length
    return [word for word in words if len(word) >= min_length]


def clean_author_name(name: str) -> str:
    """Clean and normalize author names."""
    if not name:
        return ""
    
    # Normalize unicode
    name = unicodedata.normalize("NFC", name)
    
    # Remove extra whitespace
    name = normalize_whitespace(name)
    
    # Remove common prefixes/suffixes
    prefixes = ['dr.', 'prof.', 'professor']
    suffixes = ['jr.', 'sr.', 'phd', 'ph.d.']
    
    name_lower = name.lower()
    for prefix in prefixes:
        if name_lower.startswith(prefix):
            name = name[len(prefix):].strip()
            break
    
    for suffix in suffixes:
        if name_lower.endswith(suffix):
            name = name[:-len(suffix)].strip()
            break
    
    return name


def extract_title_from_text(text: str, max_length: int = 200) -> Optional[str]:
    """Extract potential title from text."""
    if not text:
        return None
    
    # Clean the text
    text = normalize_whitespace(text)
    
    # Take first line that looks like a title
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if len(line) > 10 and len(line) <= max_length:
            # Check if it looks like a title (not all caps, has mixed case)
            if not line.isupper() and any(c.isupper() for c in line):
                return line
    
    # Fallback: take first reasonable chunk
    if len(text) <= max_length:
        return text
    
    return text[:max_length].rsplit(' ', 1)[0] + '...'


def extract_dois(text: str) -> List[str]:
    """Extract DOI identifiers from text."""
    if not text:
        return []
    
    # DOI pattern: 10.xxxx/yyyy...
    doi_pattern = r'10\.\d+\/[^\s,;]+[^\s,;.)]'
    
    dois = re.findall(doi_pattern, text, re.IGNORECASE)
    
    # Clean up DOIs
    cleaned_dois = []
    for doi in dois:
        # Remove trailing punctuation
        doi = re.sub(r'[.,:;)}\]]+$', '', doi)
        if doi:
            cleaned_dois.append(doi)
    
    return list(set(cleaned_dois))  # Remove duplicates


def split_author_list(authors_text: str) -> List[str]:
    """Split author list text into individual author names."""
    if not authors_text:
        return []
    
    # Common separators
    separators = [', and ', ' and ', '; ', ', ', '\n']
    
    authors = [authors_text]
    
    for sep in separators:
        new_authors = []
        for author in authors:
            new_authors.extend(author.split(sep))
        authors = new_authors
    
    # Clean and filter authors
    cleaned_authors = []
    for author in authors:
        author = clean_author_name(author)
        if author and len(author) > 2:  # Minimum reasonable author name length
            cleaned_authors.append(author)
    
    return cleaned_authors