#!/usr/bin/env python3
"""
XML Parser for ArXiv API
Extracted from src.parsers.pdf_parser.py - Handles XML parsing for ArXiv API responses
"""

import logging
import re
from typing import Optional, Dict, Any, List
import defusedxml.ElementTree as ET

logger = logging.getLogger(__name__)


class XMLParser:
    """XML parser for ArXiv API responses"""
    
    def __init__(self):
        """Initialize XML parser"""
        self.namespaces = {
            'atom': 'http://www.w3.org/2005/Atom',
            'arxiv': 'http://arxiv.org/schemas/atom'
        }
    
    def parse_arxiv_entry(self, entry: ET.Element) -> Optional[Dict[str, Any]]:
        """
        Parse a single ArXiv entry from XML
        
        Args:
            entry: XML entry element from ArXiv API
            
        Returns:
            Dictionary with paper metadata or None
        """
        try:
            paper_data = {}
            
            # Extract ID
            id_elem = entry.find('atom:id', self.namespaces)
            if id_elem is not None:
                paper_data['id'] = id_elem.text
                # Extract clean ArXiv ID from URL
                match = re.search(r'abs/(.+)$', id_elem.text)
                if match:
                    paper_data['arxiv_id'] = match.group(1)
            
            # Extract title
            title_elem = entry.find('atom:title', self.namespaces)
            if title_elem is not None:
                title = title_elem.text.strip()
                # Clean title
                title = re.sub(r'\s+', ' ', title)
                paper_data['title'] = title
            
            # Extract authors
            authors = []
            author_elems = entry.findall('atom:author', self.namespaces)
            for author_elem in author_elems:
                name_elem = author_elem.find('atom:name', self.namespaces)
                if name_elem is not None:
                    authors.append(name_elem.text.strip())
            
            if authors:
                paper_data['authors'] = ', '.join(authors)
            
            # Extract summary/abstract
            summary_elem = entry.find('atom:summary', self.namespaces)
            if summary_elem is not None:
                abstract = summary_elem.text.strip()
                # Clean abstract
                abstract = re.sub(r'\s+', ' ', abstract)
                paper_data['abstract'] = abstract
            
            # Extract published date
            published_elem = entry.find('atom:published', self.namespaces)
            if published_elem is not None:
                paper_data['published'] = published_elem.text
            
            # Extract updated date
            updated_elem = entry.find('atom:updated', self.namespaces)
            if updated_elem is not None:
                paper_data['updated'] = updated_elem.text
            
            # Extract categories
            categories = []
            category_elems = entry.findall('atom:category', self.namespaces)
            for category_elem in category_elems:
                term = category_elem.get('term')
                if term:
                    categories.append(term)
            
            if categories:
                paper_data['categories'] = categories
            
            # Extract DOI if available
            doi_elem = entry.find('arxiv:doi', self.namespaces)
            if doi_elem is not None:
                paper_data['doi'] = doi_elem.text
            
            # Extract journal reference if available
            journal_elem = entry.find('arxiv:journal_ref', self.namespaces)
            if journal_elem is not None:
                paper_data['journal'] = journal_elem.text
            
            # Extract comment if available
            comment_elem = entry.find('arxiv:comment', self.namespaces)
            if comment_elem is not None:
                paper_data['comment'] = comment_elem.text
            
            # Extract PDF link
            links = entry.findall('atom:link', self.namespaces)
            for link in links:
                if link.get('type') == 'application/pdf':
                    paper_data['pdf_url'] = link.get('href')
                elif link.get('rel') == 'alternate':
                    paper_data['abs_url'] = link.get('href')
            
            return paper_data
            
        except Exception as e:
            logger.error(f"Failed to parse ArXiv entry: {e}")
            return None
    
    def extract_text_from_element(self, element: ET.Element) -> str:
        """Extract text content from XML element"""
        if element is None:
            return ""
        
        text = element.text or ""
        
        # Handle nested elements
        for child in element:
            if child.tail:
                text += child.tail
        
        return text.strip()
    
    def clean_text(self, text: str) -> str:
        """Clean text extracted from XML"""
        if not text:
            return ""
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common artifacts
        text = re.sub(r'\n+', ' ', text)
        text = re.sub(r'\t+', ' ', text)
        
        return text.strip()
    
    def parse_author_list(self, authors_text: str) -> List[str]:
        """Parse author list from text"""
        if not authors_text:
            return []
        
        # Split by common delimiters
        authors = re.split(r'[,;&]|\sand\s', authors_text)
        
        # Clean each author name
        cleaned_authors = []
        for author in authors:
            author = author.strip()
            if author:
                # Remove common prefixes/suffixes
                author = re.sub(r'^(Dr\.|Prof\.|Mr\.|Ms\.|Mrs\.)\s*', '', author)
                author = re.sub(r'\s*(Jr\.|Sr\.|III|IV|V)\.?$', '', author)
                cleaned_authors.append(author)
        
        return cleaned_authors
    
    def extract_categories(self, text: str) -> List[str]:
        """Extract subject categories from text"""
        if not text:
            return []
        
        # Look for category patterns
        categories = []
        
        # ArXiv category patterns
        category_patterns = [
            r'\b([a-z-]+\.[A-Z]{2})\b',  # New format: cs.LG, math.GT
            r'\b([a-z-]+)\b',            # Subject areas: cs, math, physics
        ]
        
        for pattern in category_patterns:
            matches = re.findall(pattern, text)
            categories.extend(matches)
        
        # Remove duplicates and return
        return list(set(categories))
    
    def parse_date(self, date_str: str) -> Optional[str]:
        """Parse date string to standardized format"""
        if not date_str:
            return None
        
        # Try to extract date from various formats
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2})',        # YYYY-MM-DD
            r'(\d{2}/\d{2}/\d{4})',        # MM/DD/YYYY
            r'(\d{4}/\d{2}/\d{2})',        # YYYY/MM/DD
            r'(\d{1,2}\s+\w+\s+\d{4})',   # 1 Jan 2021
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, date_str)
            if match:
                return match.group(1)
        
        return None