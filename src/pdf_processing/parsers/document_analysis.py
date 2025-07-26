#!/usr/bin/env python3
"""
Document Analysis Methods
Extracted from monolithic parsers.py for better modularity
"""

import logging
from typing import List, Dict, Any
import regex as re

from ..models import TextBlock, DocumentStructure

# Get logger
logger = logging.getLogger(__name__)


def analyze_document_structure(
    full_text: str, text_blocks: List[TextBlock], patterns: Dict[str, Any]
) -> DocumentStructure:
    """Analyze document structure with improved repository detection"""
    structure = DocumentStructure()

    if not full_text:
        return structure

    text_lower = full_text.lower()

    # More aggressive repository type detection
    for repo_type, repo_patterns in patterns["repository_patterns"].items():
        for pattern in repo_patterns:
            if re.search(pattern, text_lower):
                structure.repository_type = repo_type
                logger.debug(
                    f"Detected repository type: {repo_type} using pattern: {pattern}"
                )
                break
        if structure.repository_type:
            break

    # Additional repository detection based on content structure
    if not structure.repository_type:
        # Check for arXiv patterns
        if re.search(r"arxiv:\d{4}\.\d{4,5}", text_lower):
            structure.repository_type = "arxiv"
            logger.debug("Detected arXiv from arxiv: identifier")
        # Check for journal patterns
        elif any(
            journal in text_lower
            for journal in ["nature", "ieee", "acm", "springer"]
        ):
            structure.repository_type = "journal"
            logger.debug("Detected journal from journal indicators")
        # Check for SSRN patterns
        elif any(
            ssrn in text_lower
            for ssrn in ["ssrn", "social science research network"]
        ):
            structure.repository_type = "ssrn"
            logger.debug("Detected SSRN from indicators")

    # Detect if published
    published_indicators = [
        r"journal\s+of",
        r"proceedings\s+of",
        r"published\s+in",
        r"copyright.*\d{4}",
        r"doi:\s*10\.\d+",
        r"©\s*\d{4}",
    ]
    structure.is_published = any(
        re.search(pattern, text_lower) for pattern in published_indicators
    )

    # Calculate text quality
    structure.text_quality = calculate_text_quality(full_text)

    # Detect extraction challenges
    if len(text_blocks) < 5:
        structure.extraction_challenges.append("Very few text blocks detected")

    if structure.text_quality < 0.5:
        structure.extraction_challenges.append("Low text quality detected")

    logger.debug(
        f"Document structure: repo={structure.repository_type}, published={structure.is_published}"
    )

    return structure


def calculate_text_quality(text: str) -> float:
    """Calculate text extraction quality score"""
    if not text:
        return 0.0

    score = 0.0

    # Length score
    if 500 <= len(text) <= 100000:
        score += 0.3
    elif 100 <= len(text) < 500:
        score += 0.2

    # Character diversity
    unique_chars = len(set(text.lower()))
    if unique_chars > 15:
        score += 0.2

    # Word coherence
    words = text.split()
    if len(words) > 5:
        avg_word_length = sum(len(word) for word in words) / len(words)
        if 2 <= avg_word_length <= 10:
            score += 0.2

    # Academic content indicators
    academic_words = ["analysis", "research", "study", "method", "results"]
    academic_score = sum(1 for word in academic_words if word in text.lower())
    score += min(0.3, academic_score * 0.1)

    return min(1.0, score)


def detect_document_language(text: str) -> str:
    """Detect document language from text content"""
    if not text:
        return "unknown"
    
    # Simple language detection based on common words
    text_lower = text.lower()
    
    # English indicators
    english_indicators = ['the', 'and', 'of', 'to', 'in', 'a', 'is', 'that', 'for', 'with']
    english_score = sum(1 for word in english_indicators if word in text_lower)
    
    # German indicators
    german_indicators = ['der', 'die', 'das', 'und', 'ist', 'in', 'den', 'von', 'zu', 'mit']
    german_score = sum(1 for word in german_indicators if word in text_lower)
    
    # French indicators
    french_indicators = ['le', 'de', 'et', 'à', 'un', 'il', 'être', 'et', 'en', 'avoir']
    french_score = sum(1 for word in french_indicators if word in text_lower)
    
    # Spanish indicators
    spanish_indicators = ['el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se']
    spanish_score = sum(1 for word in spanish_indicators if word in text_lower)
    
    # Determine language based on highest score
    scores = {
        'en': english_score,
        'de': german_score,
        'fr': french_score,
        'es': spanish_score
    }
    
    max_score = max(scores.values())
    if max_score >= 3:  # Minimum threshold
        return max(scores, key=scores.get)
    
    return "en"  # Default to English


def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """Extract potential keywords from text"""
    if not text:
        return []
    
    # Simple keyword extraction based on frequency and academic relevance
    text_lower = text.lower()
    
    # Common academic keywords
    academic_keywords = {
        'algorithm', 'analysis', 'approach', 'application', 'architecture',
        'classification', 'clustering', 'comparison', 'complexity', 'computation',
        'dataset', 'deep', 'detection', 'evaluation', 'experimental', 'extraction',
        'framework', 'generation', 'implementation', 'learning', 'machine',
        'method', 'model', 'network', 'optimization', 'performance', 'prediction',
        'problem', 'processing', 'recognition', 'regression', 'research',
        'segmentation', 'study', 'system', 'technique', 'theory', 'training'
    }
    
    # Find academic keywords that appear in the text
    found_keywords = []
    for keyword in academic_keywords:
        if keyword in text_lower:
            # Count occurrences
            count = text_lower.count(keyword)
            if count >= 2:  # Minimum frequency
                found_keywords.append((keyword, count))
    
    # Sort by frequency and return top keywords
    found_keywords.sort(key=lambda x: x[1], reverse=True)
    return [keyword for keyword, _ in found_keywords[:max_keywords]]


def extract_abstract(text: str) -> str:
    """Extract abstract from text if present"""
    if not text:
        return ""
    
    # Look for abstract section
    abstract_patterns = [
        r"abstract\s*[:\-]?\s*\n(.*?)(?:\n\s*\n|\n\s*(?:keywords|introduction|1\.|i\.)|$)",
        r"summary\s*[:\-]?\s*\n(.*?)(?:\n\s*\n|\n\s*(?:keywords|introduction|1\.|i\.)|$)",
        r"résumé\s*[:\-]?\s*\n(.*?)(?:\n\s*\n|\n\s*(?:keywords|introduction|1\.|i\.)|$)",
    ]
    
    for pattern in abstract_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            abstract = match.group(1).strip()
            # Clean up the abstract
            abstract = re.sub(r'\s+', ' ', abstract)
            abstract = re.sub(r'\n+', ' ', abstract)
            
            # Validate length
            if 50 <= len(abstract) <= 2000:
                return abstract
    
    return ""


def detect_citations(text: str) -> List[str]:
    """Detect and extract citations from text"""
    if not text:
        return []
    
    citations = []
    
    # DOI patterns
    doi_pattern = r"doi:\s*10\.\d+/[^\s]+"
    dois = re.findall(doi_pattern, text, re.IGNORECASE)
    citations.extend(dois)
    
    # ArXiv patterns
    arxiv_pattern = r"arxiv:\d{4}\.\d{4,5}(?:v\d+)?"
    arxivs = re.findall(arxiv_pattern, text, re.IGNORECASE)
    citations.extend(arxivs)
    
    # ISBN patterns
    isbn_pattern = r"isbn[:\s]*(?:97[89])?\d{1,5}[-\s]?\d{1,7}[-\s]?\d{1,7}[-\s]?[\dxX]"
    isbns = re.findall(isbn_pattern, text, re.IGNORECASE)
    citations.extend(isbns)
    
    # URL patterns (academic URLs)
    url_pattern = r"https?://(?:www\.)?(?:arxiv\.org|doi\.org|pubmed\.ncbi\.nlm\.nih\.gov|ieeexplore\.ieee\.org|dl\.acm\.org)[^\s]+"
    urls = re.findall(url_pattern, text, re.IGNORECASE)
    citations.extend(urls)
    
    return list(set(citations))  # Remove duplicates


def extract_publication_info(text: str) -> Dict[str, str]:
    """Extract publication information from text"""
    info = {}
    
    if not text:
        return info
    
    text.lower()
    
    # Extract year
    year_pattern = r"(?:19|20)\d{2}"
    years = re.findall(year_pattern, text)
    if years:
        # Take the most recent year that's not in the future
        import datetime
        current_year = datetime.datetime.now().year
        valid_years = [int(year) for year in years if int(year) <= current_year]
        if valid_years:
            info['year'] = str(max(valid_years))
    
    # Extract DOI
    doi_pattern = r"doi:\s*(10\.\d+/[^\s]+)"
    doi_match = re.search(doi_pattern, text, re.IGNORECASE)
    if doi_match:
        info['doi'] = doi_match.group(1)
    
    # Extract journal/venue
    journal_patterns = [
        r"published\s+in\s+([^,.\n]+)",
        r"journal\s+of\s+([^,.\n]+)",
        r"proceedings\s+of\s+([^,.\n]+)",
        r"in\s+([^,.\n]*(?:journal|proceedings|conference|workshop)[^,.\n]*)",
    ]
    
    for pattern in journal_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            journal = match.group(1).strip()
            if 5 <= len(journal) <= 100:
                info['journal'] = journal
                break
    
    # Extract pages
    page_pattern = r"pages?\s*[:\-]?\s*(\d+(?:\s*[-–]\s*\d+)?)"
    page_match = re.search(page_pattern, text, re.IGNORECASE)
    if page_match:
        info['pages'] = page_match.group(1)
    
    return info


# Export functions
__all__ = [
    'analyze_document_structure',
    'calculate_text_quality',
    'detect_document_language',
    'extract_keywords',
    'extract_abstract',
    'detect_citations',
    'extract_publication_info'
]