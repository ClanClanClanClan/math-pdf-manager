#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive tests for core.text_canonicalization module
"""

import pytest
from core.text_canonicalization import (
    canonicalize,
    build_canonical_exceptions,
    normalize_token,
    _CONTROL_CHARS
)


class TestCanonicalize:
    """Test canonicalize function"""
    
    def test_empty_and_none_inputs(self):
        """Test empty, None, and non-string inputs"""
        assert canonicalize(None) == ""
        assert canonicalize("") == ""
        assert canonicalize(123) == ""
        assert canonicalize([]) == ""
        assert canonicalize({}) == ""
    
    def test_basic_text_normalization(self):
        """Test basic text normalization"""
        assert canonicalize("Hello World") == "hello world"
        assert canonicalize("UPPERCASE") == "uppercase"
        assert canonicalize("   spaces   ") == "spaces"
    
    def test_dash_normalization(self):
        """Test various dash characters are normalized to hyphen"""
        # En dash
        assert canonicalize("Black–Scholes") == "black-scholes"
        # Em dash
        assert canonicalize("Black—Scholes") == "black-scholes"
        # Minus sign
        assert canonicalize("Black−Scholes") == "black-scholes"
        # Regular hyphen (unchanged)
        assert canonicalize("Black-Scholes") == "black-scholes"
    
    def test_multiple_dash_collapse(self):
        """Test that multiple consecutive dashes are collapsed"""
        assert canonicalize("a--b") == "a-b"
        assert canonicalize("a---b") == "a-b"
        assert canonicalize("a----b") == "a-b"
        # Mixed dash types
        assert canonicalize("a–—b") == "a-b"
    
    def test_bom_removal(self):
        """Test BOM (Byte Order Mark) removal"""
        assert canonicalize("\ufeffHello") == "hello"
        assert canonicalize("Hello\ufeff") == "hello"
        assert canonicalize("\ufeff\ufeffHello") == "hello"
    
    def test_control_character_removal(self):
        """Test removal of various control characters"""
        # Zero-width space
        assert canonicalize("Hello\u200bWorld") == "helloworld"
        # Zero-width non-joiner
        assert canonicalize("Hello\u200cWorld") == "helloworld"
        # Zero-width joiner
        assert canonicalize("Hello\u200dWorld") == "helloworld"
        # Left-to-right mark
        assert canonicalize("Hello\u200eWorld") == "helloworld"
        # Right-to-left mark
        assert canonicalize("Hello\u200fWorld") == "helloworld"
        # Word joiner
        assert canonicalize("Hello\u2060World") == "helloworld"
    
    def test_unicode_normalization_nfkd(self):
        """Test NFKD normalization"""
        # Composed characters decomposed
        assert canonicalize("café") == "cafe"  # é -> e
        assert canonicalize("naïve") == "naive"  # ï -> i
        assert canonicalize("Zürich") == "zurich"  # ü -> u
        
        # Ligatures expanded
        assert canonicalize("ﬁle") == "file"  # ﬁ ligature -> fi
        assert canonicalize("ﬂag") == "flag"  # ﬂ ligature -> fl
    
    def test_combining_character_removal(self):
        """Test removal of combining characters"""
        # Combining acute accent
        text_with_combining = "e\u0301"  # e + combining acute
        assert canonicalize(text_with_combining) == "e"
        
        # Multiple combining marks
        text_multiple = "a\u0300\u0301\u0302"  # a + grave + acute + circumflex
        assert canonicalize(text_multiple) == "a"
    
    def test_complex_real_world_examples(self):
        """Test complex real-world text"""
        # Academic author name with diacritics
        assert canonicalize("Müller, J.") == "muller, j."
        assert canonicalize("François") == "francois"
        assert canonicalize("Bjørn") == "bjørn"
        
        # Mixed punctuation and spaces
        assert canonicalize("  Black -- Scholes  Model  ") == "black - scholes  model"
        
        # Unicode mess (using escape sequences for mathematical italic letters)
        # Mathematical italic "Hello"
        assert canonicalize("\U0001D43B\U0001D452\U0001D459\U0001D459\U0001D45C") == "hello"
    
    def test_edge_cases(self):
        """Test edge cases"""
        # Only dashes
        assert canonicalize("---") == "-"
        assert canonicalize("–—−") == "-"
        
        # Only spaces
        assert canonicalize("   ") == ""
        
        # Only control chars
        assert canonicalize("\u200b\u200c\u200d") == ""
        
        # Mixed edge cases
        assert canonicalize("  –  ") == "-"


class TestBuildCanonicalExceptions:
    """Test build_canonical_exceptions function"""
    
    def test_empty_inputs(self):
        """Test with empty or None inputs"""
        assert build_canonical_exceptions(None, None) == {}
        assert build_canonical_exceptions([], []) == {}
        assert build_canonical_exceptions([], None) == {}
        assert build_canonical_exceptions(None, []) == {}
    
    def test_cap_list_only(self):
        """Test with only capitalization list"""
        cap = ["PyTorch", "TensorFlow", "LaTeX"]
        exceptions = build_canonical_exceptions(cap, None)
        
        assert exceptions["pytorch"] == "PyTorch"
        assert exceptions["tensorflow"] == "TensorFlow"
        assert exceptions["latex"] == "LaTeX"
    
    def test_dash_list_only(self):
        """Test with only dash list"""
        dash = ["Black-Scholes", "McKean-Vlasov", "Monte-Carlo"]
        exceptions = build_canonical_exceptions(None, dash)
        
        assert exceptions["black-scholes"] == "Black-Scholes"
        assert exceptions["mckean-vlasov"] == "McKean-Vlasov"
        assert exceptions["monte-carlo"] == "Monte-Carlo"
    
    def test_both_lists(self):
        """Test with both cap and dash lists"""
        cap = ["COVID-19", "AI"]
        dash = ["Itô-Doeblin", "Black-Scholes"]
        exceptions = build_canonical_exceptions(cap, dash)
        
        assert exceptions["covid-19"] == "COVID-19"
        assert exceptions["ai"] == "AI"
        assert exceptions["ito-doeblin"] == "Itô-Doeblin"
        assert exceptions["black-scholes"] == "Black-Scholes"
    
    def test_unicode_in_exceptions(self):
        """Test exceptions with unicode characters"""
        cap = ["naïve", "café", "Zürich"]
        exceptions = build_canonical_exceptions(cap, None)
        
        # These get canonicalized as keys
        assert exceptions["naive"] == "naïve"
        assert exceptions["cafe"] == "café"
        assert exceptions["zurich"] == "Zürich"
    
    def test_duplicate_handling(self):
        """Test handling of duplicates across lists"""
        cap = ["Test-Case", "Example"]
        dash = ["Test-Case", "Another-Example"]
        exceptions = build_canonical_exceptions(cap, dash)
        
        # Should handle duplicates gracefully
        assert exceptions["test-case"] == "Test-Case"
        assert exceptions["example"] == "Example"
        assert exceptions["another-example"] == "Another-Example"
    
    def test_dash_variants(self):
        """Test different dash types in input"""
        dash = ["Black–Scholes", "Monte—Carlo", "Itô−Doeblin"]
        exceptions = build_canonical_exceptions(None, dash)
        
        # All normalized to hyphen in keys
        assert exceptions["black-scholes"] == "Black–Scholes"
        assert exceptions["monte-carlo"] == "Monte—Carlo"
        assert exceptions["ito-doeblin"] == "Itô−Doeblin"


class TestNormalizeToken:
    """Test normalize_token function"""
    
    def test_empty_and_none_inputs(self):
        """Test empty and None inputs"""
        assert normalize_token(None) == ""
        assert normalize_token("") == ""
    
    def test_basic_normalization(self):
        """Test basic token normalization"""
        assert normalize_token("Hello") == "hello"
        assert normalize_token("WORLD") == "world"
        assert normalize_token("  test  ") == "test"
    
    def test_unicode_normalization(self):
        """Test NFKD normalization"""
        assert normalize_token("café") == "cafe"
        assert normalize_token("naïve") == "naive"
        assert normalize_token("Zürich") == "zurich"
    
    def test_combining_character_removal(self):
        """Test removal of combining characters"""
        assert normalize_token("e\u0301") == "e"
        assert normalize_token("a\u0300\u0301") == "a"
    
    def test_special_character_removal(self):
        """Test BOM and zero-width space removal"""
        assert normalize_token("\ufefftest") == "test"
        assert normalize_token("test\ufeff") == "test"
        assert normalize_token("te\u200bst") == "test"
    
    def test_strip_behavior(self):
        """Test stripping of dashes and spaces"""
        assert normalize_token("- test -") == "test"
        assert normalize_token("-- test --") == "test"
        assert normalize_token("  - test -  ") == "test"
        assert normalize_token("test-") == "test"
        assert normalize_token("-test") == "test"
    
    def test_no_dash_collapse(self):
        """Test that normalize_token doesn't collapse multiple dashes"""
        # Unlike canonicalize, normalize_token doesn't collapse dashes
        assert normalize_token("a--b") == "a--b"
        assert normalize_token("test--case") == "test--case"
    
    def test_preserve_internal_structure(self):
        """Test that internal structure is preserved"""
        assert normalize_token("Black-Scholes") == "black-scholes"
        assert normalize_token("test_case") == "test_case"
        assert normalize_token("file.txt") == "file.txt"
    
    def test_edge_cases(self):
        """Test edge cases"""
        # Only dashes
        assert normalize_token("---") == ""
        assert normalize_token("- - -") == ""
        
        # Mixed special chars
        assert normalize_token("\ufeff-\u200b-") == ""
        assert normalize_token("  -  ") == ""


class TestControlCharsRegex:
    """Test _CONTROL_CHARS regex pattern"""
    
    def test_control_chars_pattern(self):
        """Test that control chars regex matches expected characters"""
        # Test individual control characters
        assert _CONTROL_CHARS.search("\u200b") is not None  # Zero-width space
        assert _CONTROL_CHARS.search("\u200c") is not None  # Zero-width non-joiner
        assert _CONTROL_CHARS.search("\u200d") is not None  # Zero-width joiner
        assert _CONTROL_CHARS.search("\u200e") is not None  # Left-to-right mark
        assert _CONTROL_CHARS.search("\u200f") is not None  # Right-to-left mark
        assert _CONTROL_CHARS.search("\u202a") is not None  # Left-to-right embedding
        assert _CONTROL_CHARS.search("\u202e") is not None  # Right-to-left override
        assert _CONTROL_CHARS.search("\u2060") is not None  # Word joiner
        assert _CONTROL_CHARS.search("\u206f") is not None  # Nominal digit shapes
    
    def test_control_chars_non_matches(self):
        """Test that normal characters don't match"""
        assert _CONTROL_CHARS.search("a") is None
        assert _CONTROL_CHARS.search("1") is None
        assert _CONTROL_CHARS.search(" ") is None
        assert _CONTROL_CHARS.search("-") is None
        assert _CONTROL_CHARS.search("é") is None
    
    def test_control_chars_substitution(self):
        """Test control character substitution"""
        text = "Hello\u200bWorld\u200cTest\u2060End"
        result = _CONTROL_CHARS.sub("", text)
        assert result == "HelloWorldTestEnd"
        
        # Multiple consecutive control chars
        text = "Start\u200b\u200c\u200dEnd"
        result = _CONTROL_CHARS.sub("", text)
        assert result == "StartEnd"


class TestIntegration:
    """Integration tests combining multiple functions"""
    
    def test_canonicalize_and_exceptions(self):
        """Test canonicalize with build_canonical_exceptions"""
        cap = ["PyTorch", "COVID-19"]
        dash = ["Black-Scholes", "McKean-Vlasov"]
        exceptions = build_canonical_exceptions(cap, dash)
        
        # Test lookups
        assert exceptions.get(canonicalize("pytorch")) == "PyTorch"
        assert exceptions.get(canonicalize("PYTORCH")) == "PyTorch"
        assert exceptions.get(canonicalize("Black-Scholes")) == "Black-Scholes"
        assert exceptions.get(canonicalize("black–scholes")) == "Black-Scholes"
    
    def test_normalize_vs_canonicalize(self):
        """Test differences between normalize_token and canonicalize"""
        text = "Black--Scholes"
        
        # normalize_token preserves double dashes
        assert normalize_token(text) == "black--scholes"
        
        # canonicalize collapses them
        assert canonicalize(text) == "black-scholes"
        
        # Both handle unicode similarly
        unicode_text = "café–naïve"
        assert normalize_token(unicode_text) == "cafe–naive"
        assert canonicalize(unicode_text) == "cafe-naive"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])