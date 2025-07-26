#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive tests for core.tokenization module
"""

import pytest
from unittest.mock import patch
from core.tokenization import (
    Token,
    _phrase_regex,
    mask_math_regions,
    iterate_nonmath_segments,
    _SEGMENT_RE
)


class TestToken:
    """Test Token dataclass"""
    
    def test_token_creation(self):
        """Test Token object creation"""
        token = Token("WORD", "hello", 0, 5)
        assert token.kind == "WORD"
        assert token.value == "hello"
        assert token.start == 0
        assert token.end == 5
    
    def test_token_immutability(self):
        """Test that Token is immutable (frozen)"""
        token = Token("WORD", "hello", 0, 5)
        
        # Should not be able to modify attributes
        with pytest.raises(AttributeError):
            token.kind = "PUNCT"
        with pytest.raises(AttributeError):
            token.value = "world"
        with pytest.raises(AttributeError):
            token.start = 10
        with pytest.raises(AttributeError):
            token.end = 15
    
    def test_token_equality(self):
        """Test Token equality comparison"""
        token1 = Token("WORD", "hello", 0, 5)
        token2 = Token("WORD", "hello", 0, 5)
        token3 = Token("WORD", "world", 0, 5)
        
        assert token1 == token2
        assert token1 != token3
    
    def test_token_hash(self):
        """Test Token is hashable"""
        token1 = Token("WORD", "hello", 0, 5)
        token2 = Token("WORD", "hello", 0, 5)
        token3 = Token("WORD", "world", 0, 5)
        
        # Can be used in sets and as dict keys
        token_set = {token1, token2, token3}
        assert len(token_set) == 2  # token1 and token2 are same
        
        token_dict = {token1: "value"}
        assert token_dict[token2] == "value"  # Same hash
    
    def test_token_repr(self):
        """Test Token string representation"""
        token = Token("WORD", "hello", 0, 5)
        repr_str = repr(token)
        assert "Token" in repr_str
        assert "WORD" in repr_str
        assert "hello" in repr_str
        assert "0" in repr_str
        assert "5" in repr_str
    
    def test_token_different_kinds(self):
        """Test Token with different kinds"""
        test_cases = [
            ("WORD", "hello", 0, 5),
            ("SPACE", " ", 5, 6),
            ("PUNCT", "!", 6, 7),
            ("MATH", "$x$", 7, 10),
            ("PHRASE", "Black-Scholes", 10, 23)
        ]
        
        for kind, value, start, end in test_cases:
            token = Token(kind, value, start, end)
            assert token.kind == kind
            assert token.value == value
            assert token.start == start
            assert token.end == end


class TestSegmentRegex:
    """Test _SEGMENT_RE regex pattern"""
    
    def test_space_patterns(self):
        """Test space pattern matching"""
        test_cases = [
            " ",           # Single space
            "  ",          # Multiple spaces
            "\t",          # Tab
            "\n",          # Newline
            "\r\n",        # Windows line ending
            " \t\n ",      # Mixed whitespace
        ]
        
        for text in test_cases:
            match = _SEGMENT_RE.match(text)
            assert match is not None
            assert match.lastgroup == "SPACE"
            assert match.group() == text
    
    def test_word_patterns(self):
        """Test word pattern matching"""
        test_cases = [
            "hello",       # Simple word
            "Hello",       # Capitalized
            "HELLO",       # All caps
            "hello123",    # With numbers
            "don't",       # With apostrophe
            "won't",       # With smart quote
            # Note: Unicode characters might not match as single words depending on regex
        ]
        
        for text in test_cases:
            match = _SEGMENT_RE.match(text)
            assert match is not None
            assert match.lastgroup == "WORD"
            assert match.group() == text
    
    def test_punctuation_patterns(self):
        """Test punctuation pattern matching"""
        test_cases = [
            "!",           # Exclamation
            "?",           # Question mark
            ".",           # Period
            ",",           # Comma
            ";",           # Semicolon
            ":",           # Colon
            "(",           # Parentheses
            ")",
            "[",           # Brackets
            "]",
            "{",           # Braces
            "}",
            "\"",          # Quotes
            "@",           # Symbols
            "#",
            "$",
            "%",
            "^",
            "&",
            "*",
            "+",
            "=",
            "|",
            "\\",
            "/",
            "<",
            ">",
            "~",
            "`",
        ]
        
        for text in test_cases:
            match = _SEGMENT_RE.match(text)
            assert match is not None
            assert match.lastgroup == "PUNCT"
            assert match.group() == text
    
    def test_no_match_cases(self):
        """Test cases that don't match"""
        # Empty string should not match
        assert _SEGMENT_RE.match("") is None
    
    def test_match_precedence(self):
        """Test that patterns match in correct order"""
        # Space should match before punctuation
        match = _SEGMENT_RE.match(" ")
        assert match.lastgroup == "SPACE"
        
        # Word should match alphanumeric
        match = _SEGMENT_RE.match("abc123")
        assert match.lastgroup == "WORD"
        
        # Punctuation should match symbols
        match = _SEGMENT_RE.match("!")
        assert match.lastgroup == "PUNCT"


class TestPhraseRegex:
    """Test _phrase_regex function"""
    
    def test_simple_phrase(self):
        """Test simple phrase regex creation"""
        regex = _phrase_regex("Black Scholes")
        
        # Should match exact phrase
        assert regex.search("Black Scholes") is not None
        assert regex.search("black scholes") is not None  # Case insensitive
        assert regex.search("BLACK SCHOLES") is not None
        
        # Should match at word boundaries
        assert regex.search("The Black Scholes model") is not None
        assert regex.search("Black Scholes theory") is not None
        
        # Should not match partial words
        assert regex.search("Blackscholes") is None
        assert regex.search("BlackScholes") is None
    
    def test_flexible_whitespace(self):
        """Test flexible whitespace matching"""
        regex = _phrase_regex("Monte Carlo")
        
        # Should match various spacing
        assert regex.search("Monte Carlo") is not None
        assert regex.search("Monte  Carlo") is not None
        assert regex.search("Monte\tCarlo") is not None
        assert regex.search("Monte\nCarlo") is not None
        assert regex.search("Monte   Carlo") is not None
    
    def test_dash_flexibility(self):
        """Test dash character flexibility"""
        regex = _phrase_regex("Black Scholes")
        
        # Should match various dash types
        assert regex.search("Black-Scholes") is not None
        assert regex.search("Black\u2013Scholes") is not None  # En dash
        assert regex.search("Black\u2014Scholes") is not None  # Em dash
    
    def test_phrase_with_special_chars(self):
        """Test phrases containing regex special characters"""
        # Test with parentheses  
        regex = _phrase_regex("C programming")
        assert regex.search("C programming") is not None
        assert regex.search("The C programming language") is not None
        
        # Test with dots
        regex = _phrase_regex("Dr. Smith")
        assert regex.search("Dr. Smith") is not None
        assert regex.search("Meet Dr. Smith today") is not None
    
    def test_phrase_normalization(self):
        """Test that input phrases are normalized"""
        # Multiple spaces should be normalized
        regex = _phrase_regex("Black   Scholes")
        assert regex.search("Black Scholes") is not None
        assert regex.search("Black-Scholes") is not None
        
        # Leading/trailing spaces should be stripped
        regex = _phrase_regex("  Monte Carlo  ")
        assert regex.search("Monte Carlo") is not None
    
    def test_caching(self):
        """Test that _phrase_regex caches results"""
        # Clear cache first
        _phrase_regex.cache_clear()
        
        # First call
        regex1 = _phrase_regex("test phrase")
        info1 = _phrase_regex.cache_info()
        assert info1.hits == 0
        assert info1.misses == 1
        
        # Second call with same phrase should hit cache
        regex2 = _phrase_regex("test phrase")
        info2 = _phrase_regex.cache_info()
        assert info2.hits == 1
        assert info2.misses == 1
        
        # Should be same object
        assert regex1 is regex2
    
    def test_word_boundaries(self):
        """Test word boundary enforcement"""
        regex = _phrase_regex("cat")
        
        # Should match whole words
        assert regex.search("cat") is not None
        assert regex.search("the cat") is not None
        assert regex.search("cat food") is not None
        
        # Should not match partial words
        assert regex.search("category") is None
        assert regex.search("concatenate") is None
        assert regex.search("bobcat") is None
    
    def test_unicode_support(self):
        """Test Unicode character support"""
        regex = _phrase_regex("caf\u00e9 na\u00efve")
        
        assert regex.search("caf\u00e9 na\u00efve") is not None
        assert regex.search("CAF\u00c9 NA\u00cfVE") is not None
        assert regex.search("the caf\u00e9 na\u00efve approach") is not None
    
    def test_empty_phrase(self):
        """Test behavior with empty phrase"""
        regex = _phrase_regex("")
        # Empty phrase should match word boundaries
        assert regex.search("hello world") is not None
    
    def test_single_word_phrase(self):
        """Test single word phrases"""
        regex = _phrase_regex("hello")
        
        assert regex.search("hello") is not None
        assert regex.search("hello world") is not None
        assert regex.search("say hello") is not None
        assert regex.search("helloing") is None


class TestMaskMathRegions:
    """Test mask_math_regions function"""
    
    @patch('core.tokenization.math_detector.find_math_regions')
    def test_empty_text(self, mock_find_math):
        """Test with empty text"""
        mock_find_math.return_value = []
        result = mask_math_regions("")
        assert result == ""
        mock_find_math.assert_called_once_with("")
    
    @patch('core.tokenization.math_detector.find_math_regions')
    def test_no_math_regions(self, mock_find_math):
        """Test text without math regions"""
        text = "This is regular text without math"
        mock_find_math.return_value = []
        result = mask_math_regions(text)
        assert result == text
        mock_find_math.assert_called_once_with(text)
    
    @patch('core.tokenization.math_detector.find_math_regions')
    def test_single_math_region(self, mock_find_math):
        """Test text with single math region"""
        text = "Before $x + y$ after"
        mock_find_math.return_value = [(7, 14)]  # "$x + y$"
        result = mask_math_regions(text)
        expected = "Before \u00a4\u00a4\u00a4\u00a4\u00a4\u00a4\u00a4 after"
        assert result == expected
        mock_find_math.assert_called_once_with(text)
    
    @patch('core.tokenization.math_detector.find_math_regions')
    def test_multiple_math_regions(self, mock_find_math):
        """Test text with multiple math regions"""
        text = "First $a$ and second $b$ math"
        mock_find_math.return_value = [(6, 9), (21, 24)]  # "$a$" and "$b$"
        result = mask_math_regions(text)
        expected = "First \u00a4\u00a4\u00a4 and second \u00a4\u00a4\u00a4 math"
        assert result == expected
        mock_find_math.assert_called_once_with(text)
    
    @patch('core.tokenization.math_detector.find_math_regions')
    def test_custom_mask_character(self, mock_find_math):
        """Test with custom mask character"""
        text = "Math $x$ here"
        mock_find_math.return_value = [(5, 8)]  # "$x$"
        result = mask_math_regions(text, mask="X")
        expected = "Math XXX here"
        assert result == expected
        mock_find_math.assert_called_once_with(text)
    
    @patch('core.tokenization.math_detector.find_math_regions')
    def test_adjacent_math_regions(self, mock_find_math):
        """Test adjacent math regions"""
        text = "$a$$b$"
        mock_find_math.return_value = [(0, 3), (3, 6)]  # "$a$" and "$b$"
        result = mask_math_regions(text)
        expected = "\u00a4\u00a4\u00a4\u00a4\u00a4\u00a4"
        assert result == expected
        mock_find_math.assert_called_once_with(text)
    
    @patch('core.tokenization.math_detector.find_math_regions')
    def test_overlapping_math_regions(self, mock_find_math):
        """Test overlapping math regions"""
        text = "Complex $nested$math$ case"
        mock_find_math.return_value = [(8, 16), (15, 21)]  # Overlapping regions
        result = mask_math_regions(text)
        expected = "Complex \u00a4\u00a4\u00a4\u00a4\u00a4\u00a4\u00a4\u00a4\u00a4\u00a4\u00a4\u00a4\u00a4 case"
        assert result == expected
        mock_find_math.assert_called_once_with(text)
    
    @patch('core.tokenization.math_detector.find_math_regions')
    def test_math_at_boundaries(self, mock_find_math):
        """Test math regions at text boundaries"""
        # Math at start
        text = "$start$ and end"
        mock_find_math.return_value = [(0, 7)]
        result = mask_math_regions(text)
        expected = "\u00a4\u00a4\u00a4\u00a4\u00a4\u00a4\u00a4 and end"
        assert result == expected
        
        # Math at end
        text = "start and $end$"
        mock_find_math.return_value = [(10, 15)]
        result = mask_math_regions(text)
        expected = "start and \u00a4\u00a4\u00a4\u00a4\u00a4"
        assert result == expected
        
        # Entire text is math
        text = "$entire$"
        mock_find_math.return_value = [(0, 8)]
        result = mask_math_regions(text)
        expected = "\u00a4\u00a4\u00a4\u00a4\u00a4\u00a4\u00a4\u00a4"
        assert result == expected
    
    @patch('core.tokenization.math_detector.find_math_regions')
    def test_unicode_text(self, mock_find_math):
        """Test with Unicode text"""
        text = "Fran\u00e7ais $\u03b1 + \u03b2$ math\u00e9matiques"
        mock_find_math.return_value = [(9, 16)]  # "$\u03b1 + \u03b2$"
        result = mask_math_regions(text)
        expected = "Fran\u00e7ais \u00a4\u00a4\u00a4\u00a4\u00a4\u00a4\u00a4 math\u00e9matiques"
        assert result == expected
        mock_find_math.assert_called_once_with(text)


class TestIterateNonmathSegments:
    """Test iterate_nonmath_segments function"""
    
    def test_empty_text_no_regions(self):
        """Test empty text with no regions"""
        result = list(iterate_nonmath_segments("", []))
        assert result == []
    
    def test_empty_text_with_regions(self):
        """Test empty text with regions (should be ignored)"""
        result = list(iterate_nonmath_segments("", [(0, 5), (10, 15)]))
        assert result == []
    
    def test_no_math_regions(self):
        """Test text without math regions"""
        text = "This is regular text"
        result = list(iterate_nonmath_segments(text, []))
        expected = [(0, len(text), text)]
        assert result == expected
    
    def test_single_math_region_middle(self):
        """Test single math region in middle of text"""
        text = "Before $math$ after"
        regions = [(7, 13)]  # "$math$"
        result = list(iterate_nonmath_segments(text, regions))
        expected = [
            (0, 7, "Before "),
            (13, 19, " after")
        ]
        assert result == expected
    
    def test_math_region_at_start(self):
        """Test math region at start of text"""
        text = "$math$ after"
        regions = [(0, 6)]  # "$math$"
        result = list(iterate_nonmath_segments(text, regions))
        expected = [(6, 12, " after")]
        assert result == expected
    
    def test_math_region_at_end(self):
        """Test math region at end of text"""
        text = "Before $math$"
        regions = [(7, 13)]  # "$math$"
        result = list(iterate_nonmath_segments(text, regions))
        expected = [(0, 7, "Before ")]
        assert result == expected
    
    def test_entire_text_is_math(self):
        """Test when entire text is math"""
        text = "$math$"
        regions = [(0, 6)]
        result = list(iterate_nonmath_segments(text, regions))
        assert result == []
    
    def test_multiple_math_regions(self):
        """Test multiple math regions"""
        text = "Start $a$ middle $b$ end"
        regions = [(6, 9), (17, 20)]  # "$a$" and "$b$"
        result = list(iterate_nonmath_segments(text, regions))
        expected = [
            (0, 6, "Start "),
            (9, 17, " middle "),
            (20, 24, " end")
        ]
        assert result == expected
    
    def test_adjacent_math_regions(self):
        """Test adjacent math regions"""
        text = "Start $a$$b$ end"
        regions = [(6, 9), (9, 12)]  # "$a$" and "$b$"
        result = list(iterate_nonmath_segments(text, regions))
        expected = [
            (0, 6, "Start "),
            (12, 16, " end")
        ]
        assert result == expected
    
    def test_overlapping_regions_merged(self):
        """Test that overlapping regions are merged"""
        text = "Start $nested$math$ end"
        regions = [(6, 14), (13, 19)]  # Overlapping regions
        result = list(iterate_nonmath_segments(text, regions))
        expected = [
            (0, 6, "Start "),
            (19, 23, " end")
        ]
        assert result == expected
    
    def test_invalid_regions_clamped(self):
        """Test that invalid regions are clamped to text bounds"""
        text = "Short text"
        regions = [
            (-5, 3),    # Negative start
            (2, 50),    # End beyond text
            (-10, -5),  # Entirely negative
            (20, 25),   # Entirely beyond text
            (5, 3),     # End before start
        ]
        result = list(iterate_nonmath_segments(text, regions))
        # After merging all overlapping regions, entire text is covered
        # The regions (-5,3), (2,50) get clamped and merged to cover (0,10)
        expected = []  # No non-math segments remain
        assert result == expected
    
    def test_empty_regions_ignored(self):
        """Test that empty regions (start == end) are ignored"""
        text = "Test text"
        regions = [(0, 0), (5, 5), (9, 9), (2, 5)]  # Some empty, one valid
        result = list(iterate_nonmath_segments(text, regions))
        expected = [
            (0, 2, "Te"),
            (5, 9, "text")  # Note: no leading space in slice
        ]
        assert result == expected
    
    def test_regions_unsorted(self):
        """Test that unsorted regions are handled correctly"""
        text = "First $b$ middle $a$ end"
        regions = [(17, 20), (6, 9)]  # Reverse order: "$a$", "$b$"
        result = list(iterate_nonmath_segments(text, regions))
        expected = [
            (0, 6, "First "),
            (9, 17, " middle "),
            (20, 24, " end")
        ]
        assert result == expected
    
    def test_duplicate_regions(self):
        """Test handling of duplicate regions"""
        text = "Start $math$ end"
        regions = [(6, 12), (6, 12), (6, 12)]  # Same region repeated
        result = list(iterate_nonmath_segments(text, regions))
        expected = [
            (0, 6, "Start "),
            (12, 16, " end")
        ]
        assert result == expected
    
    def test_complex_merging_scenario(self):
        """Test complex scenario with multiple overlapping regions"""
        text = "A $1$ B $2$ C $3$ D"
        regions = [
            (2, 5),   # "$1$"
            (8, 11),  # "$2$"
            (14, 17), # "$3$"
            (1, 9),   # Overlaps with first two
            (10, 18), # Overlaps with last two
        ]
        result = list(iterate_nonmath_segments(text, regions))
        # After merging: (1, 18) covers almost everything
        expected = [
            (0, 1, "A"),
            (18, 19, "D")
        ]
        assert result == expected
    
    def test_unicode_text(self):
        """Test with Unicode text"""
        text = "Fran\u00e7ais $\u03b1 + \u03b2$ texte"
        regions = [(9, 16)]  # "$\u03b1 + \u03b2$"
        result = list(iterate_nonmath_segments(text, regions))
        expected = [
            (0, 9, "Fran\u00e7ais "),
            (16, 22, " texte")
        ]
        assert result == expected


class TestIntegration:
    """Integration tests combining multiple functions"""
    
    @patch('core.tokenization.math_detector.find_math_regions')
    def test_mask_and_iterate_consistency(self, mock_find_math):
        """Test that mask_math_regions and iterate_nonmath_segments are consistent"""
        text = "Before $x + y$ middle $z$ after"
        regions = [(7, 14), (22, 25)]  # "$x + y$" and "$z$"
        mock_find_math.return_value = regions
        
        # Mask the regions
        masked = mask_math_regions(text)
        
        # Get non-math segments
        segments = list(iterate_nonmath_segments(text, regions))
        
        # Reconstruct non-math parts
        nonmath_text = "".join(segment[2] for segment in segments)
        
        # Should match the non-masked parts
        expected_nonmath = "Before  middle  after"
        assert nonmath_text == expected_nonmath
        
        # Masked version should have correct structure
        expected_masked = "Before \u00a4\u00a4\u00a4\u00a4\u00a4\u00a4\u00a4 middle \u00a4\u00a4\u00a4 after"
        assert masked == expected_masked
    
    def test_phrase_regex_with_tokenization_workflow(self):
        """Test phrase regex in typical tokenization workflow"""
        text = "The Black-Scholes model and Monte Carlo method"
        
        # Create regexes for phrases
        bs_regex = _phrase_regex("Black Scholes")
        mc_regex = _phrase_regex("Monte Carlo")
        
        # Find matches
        bs_match = bs_regex.search(text)
        mc_match = mc_regex.search(text)
        
        assert bs_match is not None
        assert bs_match.group() == "Black-Scholes"
        assert bs_match.span() == (4, 17)
        
        assert mc_match is not None
        assert mc_match.group() == "Monte Carlo"
        assert mc_match.span() == (28, 39)
    
    def test_segment_regex_full_tokenization(self):
        """Test full tokenization using _SEGMENT_RE"""
        text = "Hello, world! How are you?"
        tokens = []
        pos = 0
        
        while pos < len(text):
            match = _SEGMENT_RE.match(text, pos)
            if match:
                kind = match.lastgroup or "UNKNOWN"
                tokens.append(Token(kind, match.group(), pos, match.end()))
                pos = match.end()
            else:
                # Fallback for unmatched characters
                tokens.append(Token("UNKNOWN", text[pos], pos, pos + 1))
                pos += 1
        
        # Check token sequence
        expected_kinds = ["WORD", "PUNCT", "SPACE", "WORD", "PUNCT", "SPACE", 
                         "WORD", "SPACE", "WORD", "SPACE", "WORD", "PUNCT"]
        expected_values = ["Hello", ",", " ", "world", "!", " ", 
                          "How", " ", "are", " ", "you", "?"]
        
        assert len(tokens) == len(expected_kinds)
        for i, (token, exp_kind, exp_value) in enumerate(zip(tokens, expected_kinds, expected_values)):
            assert token.kind == exp_kind, f"Token {i}: expected {exp_kind}, got {token.kind}"
            assert token.value == exp_value, f"Token {i}: expected {exp_value}, got {token.value}"


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_very_long_text(self):
        """Test with very long text"""
        text = "word " * 1000  # 5000 characters
        
        # Should handle without errors
        masked = mask_math_regions(text)
        assert len(masked) == len(text)
        
        segments = list(iterate_nonmath_segments(text, []))
        assert len(segments) == 1
        assert segments[0][2] == text
    
    def test_special_unicode_characters(self):
        """Test with special Unicode characters"""
        text = "Math: \u03b1 + \u03b2 = \u03b3, \u2211\u2202\u2206\u2207"
        
        # Should handle Unicode gracefully
        masked = mask_math_regions(text)
        assert len(masked) == len(text)
        
        segments = list(iterate_nonmath_segments(text, []))
        assert segments[0][2] == text
    
    def test_regex_special_characters_in_phrases(self):
        """Test phrase regex with all regex special characters"""
        special_chars = r".*+?^${}()|[]\\"
        phrase = f"test {special_chars} phrase"
        
        # Should not raise exception
        regex = _phrase_regex(phrase)
        assert regex is not None
        
        # Should match the exact phrase
        assert regex.search(phrase) is not None
    
    def test_extremely_large_regions(self):
        """Test with extremely large region coordinates"""
        text = "small text"
        large_regions = [(0, 1000000), (2000000, 3000000)]
        
        # Should handle gracefully by clamping
        segments = list(iterate_nonmath_segments(text, large_regions))
        # First region should be clamped to (0, len(text))
        # Second region should be ignored (entirely out of bounds)
        assert segments == []  # Entire text covered by clamped first region
    
    def test_negative_region_coordinates(self):
        """Test with negative region coordinates"""
        text = "test text"
        negative_regions = [(-100, -50), (-10, 5), (3, 6)]
        
        segments = list(iterate_nonmath_segments(text, negative_regions))
        # After clamping and merging: (-10,5) becomes (0,5), overlaps with (3,6)
        # Final merged region is (0,6), leaving only the end uncovered
        expected = [
            (6, 9, "ext")   # After the merged region (0, 6)
        ]
        assert segments == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])