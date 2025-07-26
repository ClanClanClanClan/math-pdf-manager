#!/usr/bin/env python3
"""
Additional Repository-Specific Extractors for Ultra-Enhanced PDF Parser

This module provides specialized extractors for additional academic repositories
and publication platforms beyond the core SSRN, arXiv, and journal extractors.

Supported repositories:
- NBER (National Bureau of Economic Research)
- PubMed/PMC (PubMed Central)
- RePEc (Research Papers in Economics)
- IEEE Xplore
- ACM Digital Library
- SpringerLink
- Working Paper Series (Generic)
"""

import regex as re
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass
from pathlib import Path


class NBERExtractor:
    """Enhanced NBER (National Bureau of Economic Research) extractor"""
    
    def __init__(self):
        self.nber_patterns = {
            'header_indicators': [
                r'national\s+bureau\s+of\s+economic\s+research',
                r'nber\.org',
                r'working\s+paper\s+series',
                r'massachusetts\s+avenue.*cambridge',
                r'nber\s+working\s+paper\s+no\.\s*\d+'
            ],
            'working_paper_pattern': r'nber\s+working\s+paper\s+no\.\s*(\d+)',
            'institutional_indicators': [
                'massachusetts avenue', 'cambridge', 'working paper', 'series',
                'bureau', 'economic', 'research', 'national'
            ]
        }
    
    def extract_title(self, text: str, text_blocks: List) -> Tuple[Optional[str], float]:
        """Extract title from NBER working paper"""
        lines = text.split('\n')
        
        # Skip NBER headers and metadata
        content_start = self._find_nber_content_start(lines)
        
        for i in range(content_start, min(content_start + 15, len(lines))):
            if i >= len(lines):
                break
                
            line = lines[i].strip()
            if not line or len(line) < 15:
                continue
            
            # Skip author-like lines
            if self._looks_like_nber_authors(line):
                continue
            
            # Check if this looks like a title
            if self._is_nber_title_candidate(line):
                # NBER titles are often in ALL CAPS
                title = line.title() if line.isupper() else line
                return self._clean_nber_title(title), 0.8
        
        return None, 0.0
    
    def extract_authors(self, text: str, text_blocks: List) -> Tuple[Optional[str], float]:
        """Extract authors from NBER working paper"""
        lines = text.split('\n')
        
        # Look for author section after title
        for i, line in enumerate(lines[5:35], 5):
            line = line.strip()
            if not line:
                continue
            
            # Skip NBER metadata
            if any(indicator in line.lower() for indicator in self.nber_patterns['institutional_indicators']):
                continue
            
            if self._looks_like_nber_authors(line):
                authors = self._extract_nber_authors(line)
                if authors:
                    return authors, 0.75
        
        return None, 0.0
    
    def _find_nber_content_start(self, lines: List[str]) -> int:
        """Find where actual content starts after NBER headers"""
        for i, line in enumerate(lines[:25]):
            line_lower = line.lower()
            if any(re.search(pattern, line_lower) for pattern in self.nber_patterns['header_indicators']):
                return i + 1
        return 0
    
    def _is_nber_title_candidate(self, line: str) -> bool:
        """Check if line could be NBER paper title"""
        line_lower = line.lower()
        
        # Should not be NBER metadata
        if any(indicator in line_lower for indicator in self.nber_patterns['institutional_indicators']):
            return False
        
        # Should be substantial
        if len(line) < 20 or len(line) > 250:
            return False
        
        # NBER papers often have economic content
        economic_keywords = [
            'economic', 'financial', 'monetary', 'fiscal', 'market', 'trade',
            'labor', 'employment', 'growth', 'productivity', 'inflation',
            'recession', 'policy', 'regulation', 'banking', 'investment'
        ]
        
        has_economic_content = any(keyword in line_lower for keyword in economic_keywords)
        
        # Or general academic content
        academic_keywords = [
            'analysis', 'evidence', 'study', 'investigation', 'empirical',
            'theoretical', 'model', 'framework', 'approach', 'methodology'
        ]
        
        has_academic_content = any(keyword in line_lower for keyword in academic_keywords)
        
        return has_economic_content or has_academic_content
    
    def _looks_like_nber_authors(self, line: str) -> bool:
        """Check if line contains NBER author format"""
        # Look for multiple names with separators
        name_pattern = r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'
        names = re.findall(name_pattern, line)
        
        has_names = len(names) >= 1
        has_separators = any(sep in line for sep in [', ', ' and ', '\n'])
        not_institutional = not any(inst in line.lower() for inst in ['working', 'paper', 'bureau'])
        
        return has_names and has_separators and not_institutional
    
    def _extract_nber_authors(self, line: str) -> Optional[str]:
        """Extract clean author names from NBER format"""
        # Remove any NBER-specific prefixes
        line = re.sub(r'^(?:by|authors?)\s*:?\s*', '', line, flags=re.IGNORECASE)
        
        # Extract name patterns
        name_patterns = [
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',
            r'\b[A-Z]\.\s*[A-Z]\.\s*[A-Z][a-z]+\b'
        ]
        
        found_names = []
        for pattern in name_patterns:
            matches = re.findall(pattern, line)
            found_names.extend(matches)
        
        # Filter institutional contamination
        clean_names = []
        for name in found_names:
            name_lower = name.lower()
            if not any(inst in name_lower for inst in [
                'working', 'paper', 'bureau', 'economic', 'research',
                'national', 'massachusetts', 'cambridge'
            ]):
                clean_names.append(name.strip())
        
        if clean_names:
            # Remove duplicates
            unique_names = list(dict.fromkeys(clean_names))
            if len(unique_names) > 5:  # Apply et al. for NBER papers
                return ', '.join(unique_names[:5]) + ', et al.'
            else:
                return ', '.join(unique_names)
        
        return None
    
    def _clean_nber_title(self, title: str) -> str:
        """Clean NBER title"""
        # Remove NBER-specific artifacts
        title = re.sub(r'nber\s+working\s+paper\s+no\.\s*\d+', '', title, flags=re.IGNORECASE)
        title = re.sub(r'working\s+paper\s+series', '', title, flags=re.IGNORECASE)
        
        # Clean whitespace and formatting
        title = re.sub(r'\s+', ' ', title).strip()
        title = title.strip('.,;:-')
        
        return title


class PubMedExtractor:
    """PubMed/PMC (PubMed Central) extractor for medical literature"""
    
    def __init__(self):
        self.pubmed_patterns = {
            'identifiers': [
                r'pmid:\s*\d+',
                r'pmc\d+',
                r'pubmed\.ncbi\.nlm\.nih\.gov',
                r'www\.ncbi\.nlm\.nih\.gov/pmc'
            ],
            'medical_journals': [
                'nature medicine', 'cell', 'science translational medicine',
                'new england journal of medicine', 'lancet', 'jama',
                'nature biotechnology', 'nature genetics', 'plos medicine'
            ],
            'medical_keywords': [
                'clinical', 'medical', 'therapeutic', 'diagnosis', 'treatment',
                'patient', 'disease', 'syndrome', 'pathology', 'biomedical',
                'pharmaceutical', 'drug', 'therapy', 'intervention', 'trial'
            ]
        }
    
    def extract_title(self, text: str, text_blocks: List) -> Tuple[Optional[str], float]:
        """Extract title from PubMed paper"""
        lines = text.split('\n')
        
        # Skip PubMed metadata
        content_start = 0
        for i, line in enumerate(lines[:15]):
            line_lower = line.lower()
            if any(re.search(pattern, line_lower) for pattern in self.pubmed_patterns['identifiers']):
                content_start = i + 1
                break
        
        # Look for medical paper title
        for i in range(content_start, min(content_start + 12, len(lines))):
            if i >= len(lines):
                break
                
            line = lines[i].strip()
            if 20 <= len(line) <= 200 and self._is_medical_title(line):
                return line, 0.85
        
        return None, 0.0
    
    def extract_authors(self, text: str, text_blocks: List) -> Tuple[Optional[str], float]:
        """Extract authors from PubMed paper"""
        lines = text.split('\n')
        
        for i, line in enumerate(lines[3:20], 3):
            line = line.strip()
            if line and self._looks_like_medical_authors(line):
                authors = self._extract_medical_authors(line)
                if authors:
                    return authors, 0.8
        
        return None, 0.0
    
    def _is_medical_title(self, line: str) -> bool:
        """Check if line looks like medical paper title"""
        line_lower = line.lower()
        
        # Should not be metadata
        if any(pattern in line_lower for pattern in ['pmid:', 'pmc', 'pubmed', 'doi:']):
            return False
        
        # Should have medical content
        has_medical_content = any(keyword in line_lower for keyword in self.pubmed_patterns['medical_keywords'])
        
        # Or be from medical journal
        from_medical_journal = any(journal in line_lower for journal in self.pubmed_patterns['medical_journals'])
        
        return has_medical_content or from_medical_journal
    
    def _looks_like_medical_authors(self, line: str) -> bool:
        """Check if line contains medical paper authors"""
        # Medical papers often have many authors
        name_count = len(re.findall(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', line))
        has_separators = ', ' in line or ' and ' in line
        
        # May include degrees (MD, PhD, etc.)
        has_degrees = bool(re.search(r'\b(MD|PhD|DVM|DO|PharmD|RN)\b', line))
        
        return name_count >= 1 and has_separators
    
    def _extract_medical_authors(self, line: str) -> Optional[str]:
        """Extract authors from medical paper format"""
        # Remove degrees for cleaner extraction
        line_cleaned = re.sub(r'\b(MD|PhD|DVM|DO|PharmD|RN|MSc|MPH)\b', '', line)
        
        # Extract names
        names = re.findall(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', line_cleaned)
        
        if names:
            # Medical papers often have many authors
            if len(names) > 8:
                return ', '.join(names[:8]) + ', et al.'
            else:
                return ', '.join(names)
        
        return None


class RepEcExtractor:
    """RePEc (Research Papers in Economics) extractor"""
    
    def __init__(self):
        self.repec_patterns = {
            'identifiers': [
                r'repec\.org',
                r'ideas\.repec\.org',
                r'econpapers\.repec\.org',
                r'research\s+papers\s+in\s+economics'
            ],
            'series_patterns': [
                r'working\s+papers?\s+series',
                r'discussion\s+papers?\s+series',
                r'working\s+paper\s+no\.\s*\d+'
            ],
            'economic_institutions': [
                'federal reserve', 'central bank', 'world bank', 'imf',
                'oecd', 'european central bank', 'bank of england'
            ]
        }
    
    def extract_title(self, text: str, text_blocks: List) -> Tuple[Optional[str], float]:
        """Extract title from RePEc paper"""
        lines = text.split('\n')
        
        # Skip RePEc metadata
        content_start = 0
        for i, line in enumerate(lines[:20]):
            line_lower = line.lower()
            if any(re.search(pattern, line_lower) for pattern in self.repec_patterns['identifiers']):
                content_start = i + 1
                break
        
        # Look for economics paper title
        for i in range(content_start, min(content_start + 10, len(lines))):
            if i >= len(lines):
                break
                
            line = lines[i].strip()
            if 25 <= len(line) <= 200 and self._is_economics_title(line):
                return line, 0.8
        
        return None, 0.0
    
    def extract_authors(self, text: str, text_blocks: List) -> Tuple[Optional[str], float]:
        """Extract authors from RePEc paper"""
        lines = text.split('\n')
        
        for i, line in enumerate(lines[5:25], 5):
            line = line.strip()
            if line and self._looks_like_economics_authors(line):
                authors = self._extract_economics_authors(line)
                if authors:
                    return authors, 0.75
        
        return None, 0.0
    
    def _is_economics_title(self, line: str) -> bool:
        """Check if line looks like economics paper title"""
        line_lower = line.lower()
        
        economics_keywords = [
            'economic', 'monetary', 'fiscal', 'macroeconomic', 'microeconomic',
            'econometric', 'financial', 'banking', 'trade', 'market', 'policy',
            'growth', 'development', 'inflation', 'unemployment', 'productivity'
        ]
        
        return any(keyword in line_lower for keyword in economics_keywords)
    
    def _looks_like_economics_authors(self, line: str) -> bool:
        """Check if line contains economics paper authors"""
        name_count = len(re.findall(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', line))
        has_separators = any(sep in line for sep in [', ', ' and ', ' & '])
        not_institutional = not any(inst in line.lower() for inst in ['working', 'paper', 'series'])
        
        return name_count >= 1 and has_separators and not_institutional
    
    def _extract_economics_authors(self, line: str) -> Optional[str]:
        """Extract authors from economics paper format"""
        names = re.findall(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', line)
        
        # Filter out institutional names
        clean_names = []
        for name in names:
            name_lower = name.lower()
            if not any(inst in name_lower for inst in [
                'working', 'paper', 'series', 'federal', 'reserve',
                'central', 'bank', 'research', 'economics'
            ]):
                clean_names.append(name)
        
        if clean_names:
            if len(clean_names) > 6:
                return ', '.join(clean_names[:6]) + ', et al.'
            else:
                return ', '.join(clean_names)
        
        return None


class IEEEExtractor:
    """IEEE Xplore extractor for engineering and computer science papers"""
    
    def __init__(self):
        self.ieee_patterns = {
            'identifiers': [
                r'ieee\.org',
                r'ieeexplore\.ieee\.org',
                r'ieee\s+transactions?\s+on',
                r'ieee\s+conference',
                r'ieee\s+international\s+conference'
            ],
            'publication_types': [
                'transactions on', 'proceedings of', 'conference on',
                'symposium on', 'workshop on', 'journal of'
            ],
            'technical_keywords': [
                'algorithm', 'system', 'method', 'technique', 'approach',
                'implementation', 'optimization', 'performance', 'efficiency',
                'scalability', 'framework', 'architecture', 'design'
            ]
        }
    
    def extract_title(self, text: str, text_blocks: List) -> Tuple[Optional[str], float]:
        """Extract title from IEEE paper"""
        lines = text.split('\n')
        
        # Skip IEEE headers
        content_start = 0
        for i, line in enumerate(lines[:15]):
            line_lower = line.lower()
            if any(re.search(pattern, line_lower) for pattern in self.ieee_patterns['identifiers']):
                content_start = i + 1
                break
        
        # Look for technical paper title
        for i in range(content_start, min(content_start + 8, len(lines))):
            if i >= len(lines):
                break
                
            line = lines[i].strip()
            if 20 <= len(line) <= 180 and self._is_technical_title(line):
                return line, 0.85
        
        return None, 0.0
    
    def extract_authors(self, text: str, text_blocks: List) -> Tuple[Optional[str], float]:
        """Extract authors from IEEE paper"""
        lines = text.split('\n')
        
        for i, line in enumerate(lines[3:15], 3):
            line = line.strip()
            if line and self._looks_like_ieee_authors(line):
                authors = self._extract_ieee_authors(line)
                if authors:
                    return authors, 0.8
        
        return None, 0.0
    
    def _is_technical_title(self, line: str) -> bool:
        """Check if line looks like technical paper title"""
        line_lower = line.lower()
        
        # Should not be IEEE metadata
        if any(pattern in line_lower for pattern in ['ieee', 'transactions', 'proceedings']):
            return False
        
        # Should have technical content
        return any(keyword in line_lower for keyword in self.ieee_patterns['technical_keywords'])
    
    def _looks_like_ieee_authors(self, line: str) -> bool:
        """Check if line contains IEEE author format"""
        # IEEE papers often list authors with affiliations
        name_count = len(re.findall(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', line))
        has_separators = ', ' in line or ' and ' in line
        
        return name_count >= 1 and has_separators
    
    def _extract_ieee_authors(self, line: str) -> Optional[str]:
        """Extract authors from IEEE format"""
        names = re.findall(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', line)
        
        # IEEE papers can have many authors
        clean_names = []
        for name in names:
            if not any(inst in name.lower() for inst in ['ieee', 'university', 'institute']):
                clean_names.append(name)
        
        if clean_names:
            if len(clean_names) > 10:
                return ', '.join(clean_names[:10]) + ', et al.'
            else:
                return ', '.join(clean_names)
        
        return None


class ACMExtractor:
    """ACM Digital Library extractor for computer science papers"""
    
    def __init__(self):
        self.acm_patterns = {
            'identifiers': [
                r'acm\.org',
                r'dl\.acm\.org',
                r'acm\s+digital\s+library',
                r'association\s+for\s+computing\s+machinery'
            ],
            'publication_types': [
                'proceedings of', 'transactions on', 'communications of',
                'journal of', 'acm conference', 'sigmod', 'sigchi', 'siggraph'
            ],
            'cs_keywords': [
                'computer', 'computing', 'software', 'hardware', 'algorithm',
                'programming', 'database', 'machine learning', 'artificial intelligence',
                'human computer interaction', 'graphics', 'security', 'network'
            ]
        }
    
    def extract_title(self, text: str, text_blocks: List) -> Tuple[Optional[str], float]:
        """Extract title from ACM paper"""
        lines = text.split('\n')
        
        # Skip ACM headers
        content_start = 0
        for i, line in enumerate(lines[:15]):
            line_lower = line.lower()
            if any(re.search(pattern, line_lower) for pattern in self.acm_patterns['identifiers']):
                content_start = i + 1
                break
        
        # Look for CS paper title
        for i in range(content_start, min(content_start + 10, len(lines))):
            if i >= len(lines):
                break
                
            line = lines[i].strip()
            if 15 <= len(line) <= 200 and self._is_cs_title(line):
                return line, 0.8
        
        return None, 0.0
    
    def extract_authors(self, text: str, text_blocks: List) -> Tuple[Optional[str], float]:
        """Extract authors from ACM paper"""
        lines = text.split('\n')
        
        for i, line in enumerate(lines[3:20], 3):
            line = line.strip()
            if line and self._looks_like_acm_authors(line):
                authors = self._extract_acm_authors(line)
                if authors:
                    return authors, 0.75
        
        return None, 0.0
    
    def _is_cs_title(self, line: str) -> bool:
        """Check if line looks like computer science paper title"""
        line_lower = line.lower()
        
        # Should not be ACM metadata
        if any(pattern in line_lower for pattern in ['acm', 'digital library', 'proceedings']):
            return False
        
        # Should have CS content
        return any(keyword in line_lower for keyword in self.acm_patterns['cs_keywords'])
    
    def _looks_like_acm_authors(self, line: str) -> bool:
        """Check if line contains ACM author format"""
        name_count = len(re.findall(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', line))
        has_separators = any(sep in line for sep in [', ', ' and ', ' & '])
        
        return name_count >= 1 and has_separators
    
    def _extract_acm_authors(self, line: str) -> Optional[str]:
        """Extract authors from ACM format"""
        names = re.findall(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', line)
        
        clean_names = []
        for name in names:
            if not any(inst in name.lower() for inst in ['acm', 'university', 'institute']):
                clean_names.append(name)
        
        if clean_names:
            if len(clean_names) > 8:
                return ', '.join(clean_names[:8]) + ', et al.'
            else:
                return ', '.join(clean_names)
        
        return None


class SpringerExtractor:
    """Springer/SpringerLink extractor"""
    
    def __init__(self):
        self.springer_patterns = {
            'identifiers': [
                r'springer\.com',
                r'link\.springer\.com',
                r'springer\s+nature',
                r'springer[-\s]verlag'
            ],
            'publication_indicators': [
                'lecture notes', 'proceedings', 'advances in', 'studies in',
                'communications in', 'applied mathematics', 'theoretical computer science'
            ]
        }
    
    def extract_title(self, text: str, text_blocks: List) -> Tuple[Optional[str], float]:
        """Extract title from Springer paper"""
        lines = text.split('\n')
        
        # Skip Springer headers
        content_start = 0
        for i, line in enumerate(lines[:15]):
            line_lower = line.lower()
            if any(re.search(pattern, line_lower) for pattern in self.springer_patterns['identifiers']):
                content_start = i + 1
                break
        
        for i in range(content_start, min(content_start + 12, len(lines))):
            if i >= len(lines):
                break
                
            line = lines[i].strip()
            if 20 <= len(line) <= 200 and self._is_springer_title(line):
                return line, 0.75
        
        return None, 0.0
    
    def extract_authors(self, text: str, text_blocks: List) -> Tuple[Optional[str], float]:
        """Extract authors from Springer paper"""
        lines = text.split('\n')
        
        for i, line in enumerate(lines[5:25], 5):
            line = line.strip()
            if line and self._looks_like_springer_authors(line):
                authors = self._extract_springer_authors(line)
                if authors:
                    return authors, 0.7
        
        return None, 0.0
    
    def _is_springer_title(self, line: str) -> bool:
        """Check if line looks like Springer paper title"""
        line_lower = line.lower()
        
        # Should not be Springer metadata
        if any(pattern in line_lower for pattern in ['springer', 'lecture notes', 'proceedings']):
            return False
        
        # Should be academic content
        academic_indicators = [
            'analysis', 'study', 'method', 'algorithm', 'theory', 'approach',
            'investigation', 'research', 'model', 'framework'
        ]
        
        return any(indicator in line_lower for indicator in academic_indicators)
    
    def _looks_like_springer_authors(self, line: str) -> bool:
        """Check if line contains Springer authors"""
        name_count = len(re.findall(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', line))
        has_separators = any(sep in line for sep in [', ', ' and ', ' & '])
        
        return name_count >= 1 and has_separators
    
    def _extract_springer_authors(self, line: str) -> Optional[str]:
        """Extract authors from Springer format"""
        names = re.findall(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', line)
        
        clean_names = []
        for name in names:
            if not any(inst in name.lower() for inst in ['springer', 'university', 'institute']):
                clean_names.append(name)
        
        if clean_names:
            if len(clean_names) > 6:
                return ', '.join(clean_names[:6]) + ', et al.'
            else:
                return ', '.join(clean_names)
        
        return None


class GenericWorkingPaperExtractor:
    """Generic extractor for working papers from various institutions"""
    
    def __init__(self):
        self.working_paper_patterns = {
            'indicators': [
                r'working\s+papers?\s+series',
                r'discussion\s+papers?\s+series',
                r'working\s+paper\s+no\.\s*\d+',
                r'wp\s*[-:]?\s*\d+',
                r'discussion\s+paper\s+no\.\s*\d+'
            ],
            'institutions': [
                'federal reserve', 'central bank', 'research department',
                'economics department', 'business school', 'policy research'
            ]
        }
    
    def extract_title(self, text: str, text_blocks: List) -> Tuple[Optional[str], float]:
        """Extract title from generic working paper"""
        lines = text.split('\n')
        
        # Look for working paper title
        for i, line in enumerate(lines[:20]):
            line = line.strip()
            if 20 <= len(line) <= 200 and self._is_working_paper_title(line):
                return line, 0.7
        
        return None, 0.0
    
    def extract_authors(self, text: str, text_blocks: List) -> Tuple[Optional[str], float]:
        """Extract authors from generic working paper"""
        lines = text.split('\n')
        
        for i, line in enumerate(lines[5:25], 5):
            line = line.strip()
            if line and self._looks_like_working_paper_authors(line):
                authors = self._extract_working_paper_authors(line)
                if authors:
                    return authors, 0.7
        
        return None, 0.0
    
    def _is_working_paper_title(self, line: str) -> bool:
        """Check if line could be working paper title"""
        line_lower = line.lower()
        
        # Should not be working paper metadata
        if any(pattern in line_lower for pattern in ['working paper', 'discussion paper', 'wp-']):
            return False
        
        # Should have academic content
        academic_indicators = [
            'analysis', 'evidence', 'study', 'investigation', 'empirical',
            'policy', 'economic', 'financial', 'social', 'political'
        ]
        
        return any(indicator in line_lower for indicator in academic_indicators)
    
    def _looks_like_working_paper_authors(self, line: str) -> bool:
        """Check if line contains working paper authors"""
        name_count = len(re.findall(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', line))
        has_separators = any(sep in line for sep in [', ', ' and ', ' & '])
        
        return name_count >= 1 and has_separators
    
    def _extract_working_paper_authors(self, line: str) -> Optional[str]:
        """Extract authors from working paper format"""
        names = re.findall(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', line)
        
        if names:
            if len(names) > 4:
                return ', '.join(names[:4]) + ', et al.'
            else:
                return ', '.join(names)
        
        return None


# Factory function to get appropriate extractor
def get_repository_extractor(repository_type: str):
    """Get the appropriate extractor for a repository type"""
    extractors = {
        'nber': NBERExtractor(),
        'pubmed': PubMedExtractor(),
        'repec': RepEcExtractor(),
        'ieee': IEEEExtractor(),
        'acm': ACMExtractor(),
        'springer': SpringerExtractor(),
        'working_paper': GenericWorkingPaperExtractor()
    }
    
    return extractors.get(repository_type.lower())


# Enhanced repository detection
def detect_repository_type_extended(text: str) -> Optional[str]:
    """Extended repository type detection"""
    text_lower = text.lower()
    
    # NBER detection
    nber_indicators = [
        r'nber\.org', r'national\s+bureau.*economic\s+research',
        r'massachusetts\s+avenue.*cambridge', r'nber\s+working\s+paper'
    ]
    if any(re.search(pattern, text_lower) for pattern in nber_indicators):
        return 'nber'
    
    # PubMed detection
    pubmed_indicators = [
        r'pmid:\s*\d+', r'pmc\d+', r'pubmed\.ncbi\.nlm\.nih\.gov',
        r'www\.ncbi\.nlm\.nih\.gov/pmc'
    ]
    if any(re.search(pattern, text_lower) for pattern in pubmed_indicators):
        return 'pubmed'
    
    # RePEc detection
    repec_indicators = [
        r'repec\.org', r'ideas\.repec\.org', r'econpapers\.repec\.org',
        r'research\s+papers\s+in\s+economics'
    ]
    if any(re.search(pattern, text_lower) for pattern in repec_indicators):
        return 'repec'
    
    # IEEE detection
    ieee_indicators = [
        r'ieee\.org', r'ieeexplore\.ieee\.org',
        r'ieee\s+transactions?\s+on', r'ieee\s+conference'
    ]
    if any(re.search(pattern, text_lower) for pattern in ieee_indicators):
        return 'ieee'
    
    # ACM detection
    acm_indicators = [
        r'acm\.org', r'dl\.acm\.org', r'acm\s+digital\s+library',
        r'association\s+for\s+computing\s+machinery'
    ]
    if any(re.search(pattern, text_lower) for pattern in acm_indicators):
        return 'acm'
    
    # Springer detection
    springer_indicators = [
        r'springer\.com', r'link\.springer\.com',
        r'springer\s+nature', r'springer[-\s]verlag'
    ]
    if any(re.search(pattern, text_lower) for pattern in springer_indicators):
        return 'springer'
    
    # Generic working paper detection
    working_paper_indicators = [
        r'working\s+papers?\s+series', r'discussion\s+papers?\s+series',
        r'working\s+paper\s+no\.\s*\d+', r'wp\s*[-:]?\s*\d+'
    ]
    if any(re.search(pattern, text_lower) for pattern in working_paper_indicators):
        return 'working_paper'
    
    return None


if __name__ == "__main__":
    # Test the extractors
    test_texts = {
        'nber': """NBER WORKING PAPER SERIES
        
        ARTIFICIAL INTELLIGENCE AND LABOR MARKET DYNAMICS
        
        David Robinson
        Jennifer Kim
        
        Working Paper 32157
        http://www.nber.org/papers/w32157""",
        
        'pubmed': """PMID: 12345678
        
        Clinical Trial of Novel Therapeutic Approach
        
        John Smith MD, Jane Doe PhD, Robert Johnson DVM
        
        Background: This randomized controlled trial...""",
        
        'ieee': """IEEE Transactions on Pattern Analysis and Machine Intelligence
        
        Deep Learning Architecture for Computer Vision
        
        Alex Chen, Maria Garcia, Wei Zhang
        
        Abstract: We propose a novel deep learning...""",
        
        'acm': """ACM Digital Library
        
        Efficient Graph Algorithms for Large-Scale Networks
        
        Sarah Johnson, Michael Brown, Lisa Wang
        
        Abstract: In this paper, we present..."""
    }
    
    for repo_type, text in test_texts.items():
        print(f"\nTesting {repo_type.upper()} extractor:")
        extractor = get_repository_extractor(repo_type)
        if extractor:
            title, title_conf = extractor.extract_title(text, [])
            authors, author_conf = extractor.extract_authors(text, [])
            print(f"Title: {title} (confidence: {title_conf})")
            print(f"Authors: {authors} (confidence: {author_conf})")
        else:
            print(f"No extractor found for {repo_type}")
    
    # Test repository detection
    print(f"\nTesting repository detection:")
    for repo_type, text in test_texts.items():
        detected = detect_repository_type_extended(text)
        print(f"{repo_type}: detected as {detected}")