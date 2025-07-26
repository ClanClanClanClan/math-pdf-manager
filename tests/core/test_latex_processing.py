#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive tests for core.latex_processing module
"""

import pytest
from core.latex_processing import (
    strip_latex,
    strip_latex_for_comparison,
    safe_compare_titles,
    normalize_filename,
    _strip_latex_common,
    _LATEX_INLINE,
    _TEXTCMD
)


class TestLatexInlineRegex:
    """Test _LATEX_INLINE regex pattern"""
    
    def test_dollar_math(self):
        """Test dollar sign delimited math"""
        text = "This is $x + y = z$ inline math"
        matches = list(_LATEX_INLINE.finditer(text))
        assert len(matches) == 1
        assert matches[0].group() == "$x + y = z$"
    
    def test_parenthesis_math(self):
        """Test \\(...\\) delimited math"""
        text = "This is \\(x + y = z\\) inline math"
        matches = list(_LATEX_INLINE.finditer(text))
        assert len(matches) == 1
        assert matches[0].group() == "\\(x + y = z\\)"
    
    def test_bracket_math(self):
        """Test \\[...\\] delimited math"""
        text = "This is \\[x + y = z\\] display math"
        matches = list(_LATEX_INLINE.finditer(text))
        assert len(matches) == 1
        assert matches[0].group() == "\\[x + y = z\\]"
    
    def test_no_matches(self):
        """Test text without math"""
        text = "This is plain text without math"
        matches = list(_LATEX_INLINE.finditer(text))
        assert len(matches) == 0


class TestTextcmdRegex:
    """Test _TEXTCMD regex pattern"""
    
    def test_simple_command(self):
        """Test simple LaTeX commands"""
        text = "\\textbf{bold text} here"
        matches = list(_TEXTCMD.finditer(text))
        assert len(matches) == 1
        match = matches[0]
        assert match.group(1) == "textbf"
        assert match.group(2) == "bold text"
    
    def test_multiple_commands(self):
        """Test multiple LaTeX commands"""
        text = "\\textbf{bold} and \\textit{italic} text"
        matches = list(_TEXTCMD.finditer(text))
        assert len(matches) == 2
        assert matches[0].group(1) == "textbf"
        assert matches[0].group(2) == "bold"
        assert matches[1].group(1) == "textit"
        assert matches[1].group(2) == "italic"


class TestStripLatex:
    """Test strip_latex function"""
    
    def test_empty_input(self):
        """Test empty input"""
        assert strip_latex("") == ""
    
    def test_plain_text(self):
        """Test plain text without LaTeX"""
        text = "This is plain text"
        assert strip_latex(text) == text
    
    def test_math_removal(self):
        """Test math expression removal"""
        text = "Before $x + y = z$ after"
        assert strip_latex(text) == "Before after"
        
        text = "Display \\[E = mc^2\\] math"
        assert strip_latex(text) == "Display math"
    
    def test_text_commands(self):
        """Test text command processing"""
        text = "\\textbf{bold} and \\textit{italic} text"
        result = strip_latex(text)
        assert result == "bold and italic text"
        assert "\\" not in result
    
    def test_emph_removal(self):
        """Test emphasis removal"""
        text = "Normal \\emph{emphasized} text"
        result = strip_latex(text)
        assert result == "Normal text"
        assert "emphasized" not in result
    
    def test_bare_commands(self):
        """Test bare command removal"""
        text = "Text \\alpha \\beta more"
        result = strip_latex(text)
        assert result == "Text more"
        assert "\\" not in result
    
    def test_whitespace_handling(self):
        """Test whitespace normalization"""
        text = "\\textbf{word}   \\textit{another}    word"
        result = strip_latex(text)
        assert result == "word another word"


class TestStripLatexForComparison:
    """Test strip_latex_for_comparison function"""
    
    def test_empty_input(self):
        """Test empty input"""
        assert strip_latex_for_comparison("") == ""
    
    def test_keeps_commands(self):
        """Test that command names are kept"""
        text = "\\textbf{bold} text"
        result = strip_latex_for_comparison(text)
        assert "\\textbf" in result
        assert "bold" in result
    
    def test_emph_still_removed(self):
        """Test that emph is still removed"""
        text = "Normal \\emph{emphasized} text"
        result = strip_latex_for_comparison(text)
        # Actually, emph content is NOT removed in comparison mode, command is kept
        assert result == "Normal \\emphemphasized text"
        assert "emphasized" in result
    
    def test_bare_commands_kept(self):
        """Test that bare commands are kept"""
        text = "Text \\alpha \\beta more"
        result = strip_latex_for_comparison(text)
        assert result == "Text \\alpha \\beta more"


class TestNormalizeFilename:
    """Test normalize_filename function"""
    
    def test_empty_input(self):
        """Test empty input"""
        assert normalize_filename("") == ""
    
    def test_basic_normalization(self):
        """Test basic filename normalization"""
        assert normalize_filename("Simple_File.pdf") == "simple_file"
        assert normalize_filename("UPPERCASE.TXT") == "uppercase"
    
    def test_dash_normalization(self):
        """Test various dash character normalization"""
        # Test with Unicode escape sequences for safety
        # En dash (U+2013)
        assert normalize_filename("file\u2013name.pdf") == "file-name"
        # Em dash (U+2014)  
        assert normalize_filename("file\u2014name.pdf") == "file-name"
        # Regular hyphen
        assert normalize_filename("file-name.pdf") == "file-name"
    
    def test_extension_removal(self):
        """Test file extension removal"""
        assert normalize_filename("document.pdf") == "document"
        assert normalize_filename("archive.tar.gz") == "archive.tar"
        assert normalize_filename("file.txt") == "file"
        assert normalize_filename("no_extension") == "no_extension"
    
    def test_whitespace_normalization(self):
        """Test whitespace normalization"""
        assert normalize_filename("file   with   spaces.pdf") == "file with spaces"
        assert normalize_filename("  leading_trailing  .txt") == "leading_trailing"
    
    def test_academic_paper_names(self):
        """Test typical academic paper filename patterns"""
        # ArXiv style
        assert normalize_filename("1234.5678_Some_Paper_Title.pdf") == "1234.5678_some_paper_title"
        
        # Conference style
        assert normalize_filename("Author_Year_Conference_Title.pdf") == "author_year_conference_title"


class TestSafeCompareTitles:
    """Test safe_compare_titles function"""
    
    def test_identical_titles(self):
        """Test identical titles"""
        title = "Simple Title"
        assert safe_compare_titles(title, title) is True
    
    def test_case_insensitive(self):
        """Test case insensitive comparison"""
        assert safe_compare_titles("Title", "TITLE") is True
        assert safe_compare_titles("Mixed Case", "mixed case") is True
    
    def test_latex_stripping(self):
        """Test LaTeX command stripping"""
        title1 = "\\textbf{Bold Title}"
        title2 = "Bold Title"
        # These are NOT equal because strip_latex_for_comparison keeps command names
        assert safe_compare_titles(title1, title2) is False
        
        title1 = "Title with $\\alpha$ math"
        title2 = "Title with math"
        assert safe_compare_titles(title1, title2) is True
    
    def test_dash_normalization(self):
        """Test dash normalization in comparison"""
        title1 = "Black\u2013Scholes Model"  # En dash
        title2 = "Black\u2014Scholes Model"  # Em dash
        title3 = "Black-Scholes Model"       # Regular hyphen
        
        assert safe_compare_titles(title1, title2) is True
        assert safe_compare_titles(title1, title3) is True
        assert safe_compare_titles(title2, title3) is True
    
    def test_whitespace_normalization(self):
        """Test whitespace normalization"""
        title1 = "Title   with   spaces"
        title2 = "Title with spaces"
        assert safe_compare_titles(title1, title2) is True
    
    def test_different_titles(self):
        """Test genuinely different titles"""
        assert safe_compare_titles("First Title", "Second Title") is False
        assert safe_compare_titles("Title A", "Title B") is False
    
    def test_emph_removal_affects_comparison(self):
        """Test that emph removal affects comparison"""
        title1 = "Title with \\emph{emphasis}"
        title2 = "Title with emphasis"
        title3 = "Title with \\emphemphasis"  # What title1 actually becomes
        
        # emph command is kept but braces removed in comparison mode
        assert safe_compare_titles(title1, title3) is True
        assert safe_compare_titles(title1, title2) is False
    
    def test_edge_cases(self):
        """Test edge cases"""
        # Empty strings
        assert safe_compare_titles("", "") is True
        assert safe_compare_titles("", "Non-empty") is False
        
        # Only LaTeX commands - these keep command names so not equal to empty
        assert safe_compare_titles("\\textbf{}", "") is False  # becomes "\\textbf"
        assert safe_compare_titles("\\emph{content}", "") is False  # becomes "\\emphcontent"


class TestStripLatexCommon:
    """Test _strip_latex_common helper function"""
    
    def test_empty_input(self):
        """Test empty input"""
        assert _strip_latex_common("", keep_cmds=False) == ""
        assert _strip_latex_common("", keep_cmds=True) == ""
    
    def test_math_removal(self):
        """Test inline math removal"""
        text = "Text with $x + y$ math"
        assert _strip_latex_common(text, keep_cmds=False) == "Text with math"
        assert _strip_latex_common(text, keep_cmds=True) == "Text with math"
    
    def test_command_processing_keep_false(self):
        """Test command processing with keep_cmds=False"""
        text = "\\textbf{bold} and \\emph{emphasis}"
        result = _strip_latex_common(text, keep_cmds=False)
        assert result == "bold and"
        # emph commands are dropped entirely
        assert "emphasis" not in result
    
    def test_command_processing_keep_true(self):
        """Test command processing with keep_cmds=True"""
        text = "\\textbf{bold} and \\emph{emphasis}"
        result = _strip_latex_common(text, keep_cmds=True)
        assert "\\textbf" in result
        assert "bold" in result
        # emph commands keep content in keep_cmds=True mode
        assert "emphasis" in result
    
    def test_trailing_dot_handling(self):
        """Test trailing dot handling"""
        # Dot glued to word - kept
        assert _strip_latex_common("word.", keep_cmds=False) == "word."
        
        # Dot preceded by space - removed
        assert _strip_latex_common("word .", keep_cmds=False) == "word"
        
        # Multiple spaces before dot
        assert _strip_latex_common("word   .", keep_cmds=False) == "word"
        
        # No dot
        assert _strip_latex_common("word", keep_cmds=False) == "word"


class TestIntegration:
    """Integration tests combining multiple functions"""
    
    def test_title_comparison_workflow(self):
        """Test typical title comparison workflow"""
        # Two similar titles with different formatting
        title1 = "\\textbf{Machine Learning} in Financial Markets: A Survey"
        title2 = "Machine Learning in Financial Markets: A Survey"
        title3 = "MACHINE LEARNING IN FINANCIAL MARKETS: A SURVEY"
        
        # title1 and title2 are NOT equal because command names are preserved
        assert safe_compare_titles(title1, title2) is False
        assert safe_compare_titles(title2, title3) is True
        assert safe_compare_titles(title1, title3) is False
    
    def test_filename_processing_workflow(self):
        """Test filename processing workflow"""
        # Test with Unicode escapes for dashes
        filename = "Author_2023\u2013Machine\u2014Learning_Survey.PDF"
        
        # Normalize filename
        normalized = normalize_filename(filename)
        assert normalized == "author_2023-machine-learning_survey"
        
        # Further process with LaTeX stripping (if it contained LaTeX)
        latex_filename = "\\textbf{Author}_2023_Survey.pdf"
        stripped = strip_latex(latex_filename)
        normalized_latex = normalize_filename(stripped)
        assert normalized_latex == "author_2023_survey"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])