"""
Text Cleaning Utilities
Consolidates text cleaning functions found throughout the codebase.
"""

import re
import html
from typing import Optional, Dict, List
from functools import lru_cache
from dataclasses import dataclass

@dataclass
class CleanerConfig:
    """Configuration for text cleaning operations."""
    remove_html: bool = True
    remove_latex: bool = False
    remove_citations: bool = False
    remove_urls: bool = False
    remove_emails: bool = False
    normalize_whitespace: bool = True
    normalize_quotes: bool = True
    normalize_dashes: bool = True
    remove_control_chars: bool = True
    preserve_line_breaks: bool = True
    max_consecutive_spaces: int = 1
    strip_outer_whitespace: bool = True

class TextCleaner:
    """
    Consolidated text cleaning utility.
    
    This class consolidates text cleaning functions found throughout
    the codebase, particularly for academic document processing.
    """
    
    def __init__(self, config: Optional[CleanerConfig] = None):
        self.config = config or CleanerConfig()
        self._setup_patterns()
    
    def _setup_patterns(self):
        """Setup compiled regex patterns for cleaning."""
        
        # HTML patterns
        self.html_tag_pattern = re.compile(r'<[^>]+>', re.IGNORECASE)
        self.html_entity_pattern = re.compile(r'&[a-zA-Z0-9#]+;')
        
        # LaTeX patterns
        self.latex_math_pattern = re.compile(r'\$[^$]*\$|\\\[[^\]]*\\\]|\\\([^)]*\\\)', re.DOTALL)
        self.latex_command_pattern = re.compile(r'\\[a-zA-Z]+(?:\s*\{[^}]*\})?', re.UNICODE)
        self.latex_comment_pattern = re.compile(r'%.*$', re.MULTILINE)
        
        # Citation patterns
        self.citation_patterns = [
            re.compile(r'\\cite\{[^}]+\}', re.UNICODE),
            re.compile(r'\\citep?\{[^}]+\}', re.UNICODE),
            re.compile(r'\[[^\]]*\d+[^\]]*\]', re.UNICODE),
            re.compile(r'\([^)]*\d{4}[^)]*\)', re.UNICODE)  # (Author, 2024)
        ]
        
        # URL and email patterns
        self.url_pattern = re.compile(
            r'https?://[^\s<>"{}|\\^`\[\]]+|www\.[^\s<>"{}|\\^`\[\]]+',
            re.IGNORECASE
        )
        
        self.email_pattern = re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            re.IGNORECASE
        )
        
        # Quote normalization patterns
        self.quote_patterns = [
            (re.compile(r'[""''‚„‹›«»]'), '"'),  # Smart quotes to straight
            (re.compile(r'[`´]'), "'"),  # Backticks to apostrophe
        ]
        
        # Dash normalization patterns
        self.dash_patterns = [
            (re.compile(r'[‒–—―]'), '-'),  # Various dashes to hyphen
            (re.compile(r'[-]{2,}'), '-'),  # Multiple hyphens to single
        ]
        
        # Whitespace patterns
        self.whitespace_pattern = re.compile(r'\s+')
        self.line_break_pattern = re.compile(r'\n\s*\n')
        
        # Control character patterns
        self.control_chars = re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]')
        self.zero_width_chars = re.compile(r'[\u200b-\u200f\u202a-\u202e\u2060-\u206f]')
        
        # Academic-specific patterns
        self.figure_caption_pattern = re.compile(r'Figure\s+\d+[:.][^\n]*', re.IGNORECASE)
        self.table_caption_pattern = re.compile(r'Table\s+\d+[:.][^\n]*', re.IGNORECASE)
        self.equation_pattern = re.compile(r'Equation\s+\d+', re.IGNORECASE)
        
        # Common academic artifacts
        self.page_number_pattern = re.compile(r'^\s*\d+\s*$', re.MULTILINE)
        self.header_footer_pattern = re.compile(r'^[A-Z\s]+$', re.MULTILINE)
    
    @lru_cache(maxsize=500)
    def clean_text(self, text: str) -> str:
        """
        Comprehensive text cleaning.
        
        Applies all configured cleaning operations to the input text.
        """
        if not text:
            return text
        
        cleaned = text
        
        # Remove HTML if configured
        if self.config.remove_html:
            cleaned = self._remove_html(cleaned)
        
        # Remove LaTeX if configured
        if self.config.remove_latex:
            cleaned = self._remove_latex(cleaned)
        
        # Remove citations if configured
        if self.config.remove_citations:
            cleaned = self._remove_citations(cleaned)
        
        # Remove URLs if configured
        if self.config.remove_urls:
            cleaned = self._remove_urls(cleaned)
        
        # Remove emails if configured
        if self.config.remove_emails:
            cleaned = self._remove_emails(cleaned)
        
        # Normalize quotes if configured
        if self.config.normalize_quotes:
            cleaned = self._normalize_quotes(cleaned)
        
        # Normalize dashes if configured
        if self.config.normalize_dashes:
            cleaned = self._normalize_dashes(cleaned)
        
        # Remove control characters if configured
        if self.config.remove_control_chars:
            cleaned = self._remove_control_chars(cleaned)
        
        # Normalize whitespace if configured
        if self.config.normalize_whitespace:
            cleaned = self._normalize_whitespace(cleaned)
        
        # Strip outer whitespace if configured
        if self.config.strip_outer_whitespace:
            cleaned = cleaned.strip()
        
        return cleaned
    
    def _remove_html(self, text: str) -> str:
        """Remove HTML tags and entities."""
        # Remove HTML tags
        text = self.html_tag_pattern.sub('', text)
        
        # Decode HTML entities
        text = html.unescape(text)
        
        return text
    
    def _remove_latex(self, text: str) -> str:
        """Remove LaTeX commands and math expressions."""
        # Remove math expressions
        text = self.latex_math_pattern.sub('', text)
        
        # Remove LaTeX commands
        text = self.latex_command_pattern.sub('', text)
        
        # Remove LaTeX comments
        text = self.latex_comment_pattern.sub('', text)
        
        return text
    
    def _remove_citations(self, text: str) -> str:
        """Remove various citation formats."""
        for pattern in self.citation_patterns:
            text = pattern.sub('', text)
        return text
    
    def _remove_urls(self, text: str) -> str:
        """Remove URLs from text."""
        return self.url_pattern.sub('', text)
    
    def _remove_emails(self, text: str) -> str:
        """Remove email addresses from text."""
        return self.email_pattern.sub('', text)
    
    def _normalize_quotes(self, text: str) -> str:
        """Normalize various quote characters."""
        for pattern, replacement in self.quote_patterns:
            text = pattern.sub(replacement, text)
        return text
    
    def _normalize_dashes(self, text: str) -> str:
        """Normalize various dash characters."""
        for pattern, replacement in self.dash_patterns:
            text = pattern.sub(replacement, text)
        return text
    
    def _remove_control_chars(self, text: str) -> str:
        """Remove control and zero-width characters."""
        # Remove control characters
        text = self.control_chars.sub('', text)
        
        # Remove zero-width characters
        text = self.zero_width_chars.sub('', text)
        
        return text
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace characters."""
        if self.config.preserve_line_breaks:
            # Preserve line breaks but normalize other whitespace
            lines = text.split('\n')
            normalized_lines = []
            
            for line in lines:
                # Normalize whitespace within each line
                normalized_line = self.whitespace_pattern.sub(' ', line).strip()
                normalized_lines.append(normalized_line)
            
            # Join lines back together
            text = '\n'.join(normalized_lines)
            
            # Normalize multiple consecutive line breaks
            text = self.line_break_pattern.sub('\n\n', text)
        else:
            # Replace all whitespace with single spaces
            text = self.whitespace_pattern.sub(' ', text)
        
        return text
    
    def clean_academic_text(self, text: str) -> str:
        """
        Clean academic text with specific academic document handling.
        
        Removes common academic artifacts like figure captions, page numbers, etc.
        """
        cleaned = self.clean_text(text)
        
        # Remove figure captions
        cleaned = self.figure_caption_pattern.sub('', cleaned)
        
        # Remove table captions
        cleaned = self.table_caption_pattern.sub('', cleaned)
        
        # Remove equation references
        cleaned = self.equation_pattern.sub('', cleaned)
        
        # Remove page numbers
        cleaned = self.page_number_pattern.sub('', cleaned)
        
        # Remove headers/footers (lines with only uppercase letters)
        cleaned = self.header_footer_pattern.sub('', cleaned)
        
        # Final whitespace normalization
        if self.config.normalize_whitespace:
            cleaned = self._normalize_whitespace(cleaned)
        
        return cleaned.strip()
    
    def clean_filename(self, filename: str) -> str:
        """
        Clean filename for safe filesystem use.
        
        Removes or replaces characters that are problematic in filenames.
        """
        cleaned = filename
        
        # Remove HTML and LaTeX
        cleaned = self._remove_html(cleaned)
        cleaned = self._remove_latex(cleaned)
        
        # Normalize quotes and dashes
        cleaned = self._normalize_quotes(cleaned)
        cleaned = self._normalize_dashes(cleaned)
        
        # Remove control characters
        cleaned = self._remove_control_chars(cleaned)
        
        # Replace filesystem-unsafe characters
        unsafe_chars = r'[<>:"/\\|?*]'
        cleaned = re.sub(unsafe_chars, '_', cleaned)
        
        # Normalize whitespace to single spaces
        cleaned = self.whitespace_pattern.sub(' ', cleaned)
        
        # Remove leading/trailing whitespace and dots
        cleaned = cleaned.strip('. ')
        
        return cleaned
    
    def extract_clean_sentences(self, text: str) -> List[str]:
        """
        Extract clean sentences from text.
        
        Returns list of cleaned sentences with proper punctuation.
        """
        cleaned = self.clean_text(text)
        
        # Split into sentences (basic sentence boundary detection)
        sentence_pattern = re.compile(r'[.!?]+\s+', re.UNICODE)
        sentences = sentence_pattern.split(cleaned)
        
        clean_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence) > 5:  # Filter out very short fragments
                clean_sentences.append(sentence)
        
        return clean_sentences
    
    def get_cleaning_stats(self, original: str, cleaned: str) -> Dict[str, any]:
        """
        Get statistics about the cleaning operation.
        
        Returns information about what was removed/changed.
        """
        return {
            'original_length': len(original),
            'cleaned_length': len(cleaned),
            'reduction_ratio': 1 - (len(cleaned) / len(original)) if original else 0,
            'html_tags_removed': len(self.html_tag_pattern.findall(original)),
            'latex_commands_removed': len(self.latex_command_pattern.findall(original)),
            'urls_removed': len(self.url_pattern.findall(original)),
            'emails_removed': len(self.email_pattern.findall(original)),
            'lines_original': original.count('\n'),
            'lines_cleaned': cleaned.count('\n'),
        }
    
    def get_stats(self) -> Dict[str, any]:
        """Get cleaner statistics."""
        return {
            'config': self.config,
            'clean_text_cache_info': self.clean_text.cache_info(),
            'patterns_loaded': sum([
                1 if hasattr(self, attr) else 0
                for attr in ['html_tag_pattern', 'latex_math_pattern', 'url_pattern',
                           'email_pattern', 'whitespace_pattern', 'control_chars']
            ])
        }

# Create default cleaner instance
default_cleaner = TextCleaner()

# Convenience functions for backward compatibility
def clean_text(text: str) -> str:
    """Convenience function for text cleaning."""
    return default_cleaner.clean_text(text)

def clean_academic_text(text: str) -> str:
    """Convenience function for academic text cleaning."""
    return default_cleaner.clean_academic_text(text)

def clean_filename(filename: str) -> str:
    """Convenience function for filename cleaning."""
    return default_cleaner.clean_filename(filename)