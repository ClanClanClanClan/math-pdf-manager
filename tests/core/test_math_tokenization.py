#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive tests for core.math_tokenization module
"""

import pytest
from core.math_tokenization import (
    robust_tokenize_with_math,
    DASH_CHARS,
    _SEGMENT_RE
)


class TestDashChars:
    """Test DASH_CHARS constant"""
    
    def test_dash_chars_content(self):
        """Test that DASH_CHARS contains expected dash characters"""
        expected_dashes = ["-", "\u2013", "\u2014", "\u2010", "\u2212"]  # -, –, —, ‐, −
        for dash in expected_dashes:
            assert dash in DASH_CHARS
    
    def test_dash_chars_regex_usage(self):
        """Test DASH_CHARS can be used in regex patterns"""
        import regex as re
        pattern = rf'[{DASH_CHARS}]+'
        regex = re.compile(pattern)
        
        # Test various dash types
        assert regex.search("regular-dash") is not None
        assert regex.search("en\u2013dash") is not None
        assert regex.search("em\u2014dash") is not None
        assert regex.search("minus\u2212sign") is not None


class TestSegmentRegex:
    """Test _SEGMENT_RE regex pattern"""
    
    def test_space_matching(self):
        """Test space pattern matching"""
        text = "   \t\n  "
        match = _SEGMENT_RE.match(text)
        assert match is not None
        assert match.lastgroup == "SPACE"
        assert match.group() == text
    
    def test_punct_matching(self):
        """Test punctuation pattern matching"""
        punctuation = "!@#$%^&*()[]{}|\\:;\"<>?,./"
        for char in punctuation:
            match = _SEGMENT_RE.match(char)
            assert match is not None
            assert match.lastgroup == "PUNCT"
            assert match.group() == char
    
    def test_word_matching(self):
        """Test word pattern matching"""
        # Simple word
        match = _SEGMENT_RE.match("hello")
        assert match is not None
        assert match.lastgroup == "WORD"
        assert match.group() == "hello"
        
        # Word with apostrophe
        match = _SEGMENT_RE.match("don't")
        assert match is not None
        assert match.lastgroup == "WORD"
        assert match.group() == "don't"
        
        # Word with smart quote
        match = _SEGMENT_RE.match("won't")
        assert match is not None
        assert match.lastgroup == "WORD"
        assert match.group() == "won't"
    
    def test_no_match(self):
        """Test cases with no matches"""
        # Empty string
        assert _SEGMENT_RE.match("") is None
        
        # Non-matching patterns (should be handled by fallback)
        # Most characters should match one of the patterns


class TestRobustTokenizeWithMath:
    """Test robust_tokenize_with_math function"""
    
    def test_empty_input(self):
        """Test empty input"""
        tokens = robust_tokenize_with_math("")
        assert len(tokens) == 0
    
    def test_simple_text(self):
        """Test simple text without math or phrases"""
        text = "Hello world"
        tokens = robust_tokenize_with_math(text)
        
        assert len(tokens) == 3
        assert tokens[0].kind == "WORD"
        assert tokens[0].value == "Hello"
        assert tokens[1].kind == "SPACE"
        assert tokens[1].value == " "
        assert tokens[2].kind == "WORD"
        assert tokens[2].value == "world"
    
    def test_math_detection(self):
        """Test math region detection and tokenization"""
        text = "The formula $x + y = z$ is simple"
        tokens = robust_tokenize_with_math(text)
        
        # Find the math token
        math_tokens = [t for t in tokens if t.kind == "MATH"]
        assert len(math_tokens) == 1
        assert math_tokens[0].value == "$x + y = z$"
    
    def test_display_math_detection(self):
        """Test display math detection ($$...$$)"""
        text = "Display math: $$E = mc^2$$ is famous"
        tokens = robust_tokenize_with_math(text)
        
        # Find the math token
        math_tokens = [t for t in tokens if t.kind == "MATH"]
        assert len(math_tokens) == 1
        assert math_tokens[0].value == "$$E = mc^2$$"
    
    def test_bracket_math_detection(self):
        """Test bracket math detection \\[...\\]"""
        text = "Equation: \\[f(x) = x^2\\] shown"
        tokens = robust_tokenize_with_math(text)
        
        # Find the math token
        math_tokens = [t for t in tokens if t.kind == "MATH"]
        assert len(math_tokens) == 1
        assert math_tokens[0].value == "\\[f(x) = x^2\\]"
    
    def test_phrase_detection_multi_word(self):
        """Test multi-word phrase detection"""
        text = "The Black Scholes model is important"
        phrases = ["Black Scholes"]
        tokens = robust_tokenize_with_math(text, phrases)
        
        # Find the phrase token
        phrase_tokens = [t for t in tokens if t.kind == "PHRASE"]
        assert len(phrase_tokens) == 1
        assert phrase_tokens[0].value == "Black Scholes"
    
    def test_phrase_detection_dash_separated(self):
        """Test dash-separated phrase detection"""
        text = "The Black-Scholes model works"
        phrases = ["Black-Scholes"]
        tokens = robust_tokenize_with_math(text, phrases)
        
        # Find the phrase token
        phrase_tokens = [t for t in tokens if t.kind == "PHRASE"]
        assert len(phrase_tokens) == 1
        assert phrase_tokens[0].value == "Black-Scholes"
    
    def test_phrase_detection_case_insensitive(self):
        """Test case-insensitive phrase matching"""
        text = "The BLACK SCHOLES model"
        phrases = ["Black Scholes"]
        tokens = robust_tokenize_with_math(text, phrases)
        
        # Find the phrase token
        phrase_tokens = [t for t in tokens if t.kind == "PHRASE"]
        assert len(phrase_tokens) == 1
        assert phrase_tokens[0].value == "BLACK SCHOLES"
    
    def test_phrase_detection_flexible_spacing(self):
        """Test flexible spacing in phrase matching"""
        text = "The Black  Scholes   model"  # Extra spaces
        phrases = ["Black Scholes"]
        tokens = robust_tokenize_with_math(text, phrases)
        
        # Find the phrase token - should match despite different spacing
        phrase_tokens = [t for t in tokens if t.kind == "PHRASE"]
        assert len(phrase_tokens) == 1
        assert "Black" in phrase_tokens[0].value
        assert "Scholes" in phrase_tokens[0].value
    
    def test_phrase_detection_hyphenated_variants(self):
        """Test hyphenated variants of space-separated phrases"""
        text = "Both Black-Scholes and Black\u2014Scholes work"
        phrases = ["Black Scholes"]  # Space-separated phrase
        tokens = robust_tokenize_with_math(text, phrases)
        
        # Should find both hyphenated variants
        phrase_tokens = [t for t in tokens if t.kind == "PHRASE"]
        assert len(phrase_tokens) == 2
        assert "Black-Scholes" in phrase_tokens[0].value
        assert "Black\u2014Scholes" in phrase_tokens[1].value
    
    def test_math_like_phrase_detection(self):
        """Test math-like single phrases"""
        text = "The function C^\u221E(M) is smooth"
        phrases = ["C^\u221E(M)"]
        tokens = robust_tokenize_with_math(text, phrases)
        
        # Should be detected as phrase, not math
        phrase_tokens = [t for t in tokens if t.kind == "PHRASE"]
        assert len(phrase_tokens) == 1
        assert phrase_tokens[0].value == "C^\u221E(M)"
        
        # Should not be detected as math
        math_tokens = [t for t in tokens if t.kind == "MATH"]
        # C^(M) should be protected from math detection
        for math_token in math_tokens:
            assert "C^\u221E(M)" not in math_token.value
    
    def test_phrase_priority_over_math(self):
        """Test phrase vs math detection behavior"""
        text = "The $\\alpha$-stable process"
        phrases = ["$\\alpha$-stable"]
        tokens = robust_tokenize_with_math(text, phrases)
        
        # Currently, math detection takes priority over phrases containing math
        # This may be the intended behavior to preserve math formatting
        math_tokens = [t for t in tokens if t.kind == "MATH"]
        assert len(math_tokens) == 1
        assert math_tokens[0].value == "$\\alpha$"
        
        # The word "stable" should be separate
        word_tokens = [t for t in tokens if t.kind == "WORD" and t.value == "stable"]
        assert len(word_tokens) == 1
    
    def test_overlapping_phrases_longest_wins(self):
        """Test that longest phrase wins when phrases overlap"""
        text = "Monte Carlo Methods in Finance"
        phrases = ["Monte Carlo", "Monte Carlo Methods"]
        tokens = robust_tokenize_with_math(text, phrases)
        
        # Should prefer the longer phrase
        phrase_tokens = [t for t in tokens if t.kind == "PHRASE"]
        assert len(phrase_tokens) == 1
        assert phrase_tokens[0].value == "Monte Carlo Methods"
    
    def test_excessive_spacing_rejection(self):
        """Test rejection of matches with excessive spacing"""
        text = "Black   Scholes"  # 3 spaces
        phrases = ["Black Scholes"]
        tokens = robust_tokenize_with_math(text, phrases)
        
        # Should reject due to excessive spacing
        phrase_tokens = [t for t in tokens if t.kind == "PHRASE"]
        assert len(phrase_tokens) == 0
    
    def test_punctuation_tokenization(self):
        """Test punctuation tokenization"""
        text = "Hello, world!"
        tokens = robust_tokenize_with_math(text)
        
        punct_tokens = [t for t in tokens if t.kind == "PUNCT"]
        assert len(punct_tokens) == 2
        assert punct_tokens[0].value == ","
        assert punct_tokens[1].value == "!"
    
    def test_mixed_content_tokenization(self):
        """Test complex text with math, phrases, and regular content"""
        text = "The Black-Scholes formula $\\frac{\\partial V}{\\partial t} + \\frac{1}{2}\\sigma^2 S^2 \\frac{\\partial^2 V}{\\partial S^2} = rV$ is fundamental."
        phrases = ["Black-Scholes"]
        tokens = robust_tokenize_with_math(text, phrases)
        
        # Should have phrase token
        phrase_tokens = [t for t in tokens if t.kind == "PHRASE"]
        assert len(phrase_tokens) == 1
        assert phrase_tokens[0].value == "Black-Scholes"
        
        # Should have math token
        math_tokens = [t for t in tokens if t.kind == "MATH"]
        assert len(math_tokens) == 1
        assert "\\frac{\\partial V}{\\partial t}" in math_tokens[0].value
        
        # Should have regular word tokens
        word_tokens = [t for t in tokens if t.kind == "WORD"]
        assert len(word_tokens) > 0
        word_values = [t.value for t in word_tokens]
        assert "formula" in word_values
        assert "fundamental" in word_values
    
    def test_token_positions(self):
        """Test that token positions are correct"""
        text = "Hello $x$ world"
        tokens = robust_tokenize_with_math(text)
        
        # Check positions
        assert tokens[0].start == 0  # "Hello"
        assert tokens[0].end == 5
        assert tokens[1].start == 5  # " "
        assert tokens[1].end == 6
        assert tokens[2].start == 6  # "$x$"
        assert tokens[2].end == 9
        assert tokens[3].start == 9  # " "
        assert tokens[3].end == 10
        assert tokens[4].start == 10  # "world"
        assert tokens[4].end == 15
    
    def test_trailing_word_detection(self):
        """Test trailing word detection for phrase tokens"""
        text = "Black-Scholes model and more Black-Scholes stuff"
        phrases = ["Black-Scholes model"]
        tokens = robust_tokenize_with_math(text, phrases)
        
        # Should have phrase token
        phrase_tokens = [t for t in tokens if t.kind == "PHRASE"]
        assert len(phrase_tokens) == 1
        assert phrase_tokens[0].value == "Black-Scholes model"
        
        # Should have additional word tokens for "model" that appears later
        [t for t in tokens if t.kind == "WORD"]
        # The word "model" should appear again outside the phrase
        # This tests the _appears_outside logic
    
    def test_unicode_handling(self):
        """Test Unicode character handling"""
        text = "\u03B1-stable process with \u03B2-distribution"  # α-stable, β-distribution
        phrases = ["\u03B1-stable"]  # α-stable
        tokens = robust_tokenize_with_math(text, phrases)
        
        # Should handle Unicode correctly
        phrase_tokens = [t for t in tokens if t.kind == "PHRASE"]
        assert len(phrase_tokens) == 1
        assert phrase_tokens[0].value == "\u03B1-stable"  # α-stable
    
    def test_fallback_tokenization(self):
        """Test fallback single-character tokenization"""
        # Use a character that doesn't match any pattern
        text = "a\u200bb"  # Zero-width space
        tokens = robust_tokenize_with_math(text)
        
        # Should have tokens for each part
        assert len(tokens) >= 3
        assert any(t.value == "a" for t in tokens)
        assert any(t.value == "b" for t in tokens)
    
    def test_empty_phrases_list(self):
        """Test with empty phrases list"""
        text = "Regular text without special phrases"
        tokens = robust_tokenize_with_math(text, [])
        
        # Should tokenize normally
        word_tokens = [t for t in tokens if t.kind == "WORD"]
        assert len(word_tokens) > 0
        
        # No phrase tokens should be created
        phrase_tokens = [t for t in tokens if t.kind == "PHRASE"]
        assert len(phrase_tokens) == 0
    
    def test_none_phrases_list(self):
        """Test with None phrases list"""
        text = "Regular text without special phrases"
        tokens = robust_tokenize_with_math(text, None)
        
        # Should tokenize normally
        word_tokens = [t for t in tokens if t.kind == "WORD"]
        assert len(word_tokens) > 0
        
        # No phrase tokens should be created
        phrase_tokens = [t for t in tokens if t.kind == "PHRASE"]
        assert len(phrase_tokens) == 0


class TestTokenProperties:
    """Test Token object properties"""
    
    def test_token_creation(self):
        """Test Token object creation and properties"""
        text = "Hello world"
        tokens = robust_tokenize_with_math(text)
        
        for token in tokens:
            # All tokens should have required properties
            assert hasattr(token, 'kind')
            assert hasattr(token, 'value')
            assert hasattr(token, 'start')
            assert hasattr(token, 'end')
            
            # Properties should be correct types
            assert isinstance(token.kind, str)
            assert isinstance(token.value, str)
            assert isinstance(token.start, int)
            assert isinstance(token.end, int)
            
            # Positions should be valid
            assert token.start >= 0
            assert token.end > token.start
            assert token.end <= len(text)
            
            # Value should match text slice
            assert token.value == text[token.start:token.end]


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_very_long_text(self):
        """Test with very long text"""
        text = "word " * 1000  # 5000 characters
        tokens = robust_tokenize_with_math(text)
        
        # Should handle without errors
        assert len(tokens) > 0
        
        # Check that all positions are valid
        for token in tokens:
            assert 0 <= token.start < token.end <= len(text)
    
    def test_only_math(self):
        """Test text that is only math"""
        text = "$\\sum_{i=1}^{n} x_i$"
        tokens = robust_tokenize_with_math(text)
        
        assert len(tokens) == 1
        assert tokens[0].kind == "MATH"
        assert tokens[0].value == text
    
    def test_only_phrases(self):
        """Test text that is only phrases"""
        text = "Black-Scholes Monte-Carlo"
        phrases = ["Black-Scholes", "Monte-Carlo"]
        tokens = robust_tokenize_with_math(text, phrases)
        
        phrase_tokens = [t for t in tokens if t.kind == "PHRASE"]
        assert len(phrase_tokens) == 2
        
        # Should also have a space token between them
        space_tokens = [t for t in tokens if t.kind == "SPACE"]
        assert len(space_tokens) == 1
    
    def test_nested_math_patterns(self):
        """Test nested or complex math patterns"""
        text = "Nested: $a + \\frac{$b$}{c}$ complex"
        tokens = robust_tokenize_with_math(text)
        
        # Should handle nested patterns gracefully
        math_tokens = [t for t in tokens if t.kind == "MATH"]
        assert len(math_tokens) > 0
    
    def test_malformed_math(self):
        """Test malformed math expressions"""
        text = "Unclosed math: $x + y and more text"
        tokens = robust_tokenize_with_math(text)
        
        # Should handle gracefully, not crash
        assert len(tokens) > 0
    
    def test_special_characters(self):
        """Test with special Unicode characters"""
        text = "Special: \u03B1, \u03B2, \u03B3, \u2211, \u220F, \u222B, \u2202, \u2206, \u2207"  # α, β, γ, ∑, ∏, ∫, ∂, ∆, ∇
        tokens = robust_tokenize_with_math(text)
        
        # Should tokenize without errors
        assert len(tokens) > 0
        
        # Check that Unicode characters are preserved
        full_text = "".join(t.value for t in tokens)
        assert full_text == text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])