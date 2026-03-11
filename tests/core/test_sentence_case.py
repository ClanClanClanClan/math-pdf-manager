#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive tests for core.sentence_case module
"""

import pytest
from unittest.mock import patch
from core.sentence_case import (
    to_sentence_case_academic,
    extract_title_words,
    filter_relevant_whitelist_terms,
    _load_sentence_case_config,
    MATH_TECHNICAL_PREFIXES,
    NUMBERS
)


class TestSentenceCaseConfig:
    """Test configuration loading"""
    
    def test_config_loading_with_cache(self):
        """Test that config is cached after first load"""
        # Clear cache first
        import core.sentence_case
        core.sentence_case._CONFIG_CACHE = {}
        
        # First load
        config1 = _load_sentence_case_config()
        assert isinstance(config1, dict)
        assert 'mixed_case_words' in config1
        
        # Second load should use cache
        config2 = _load_sentence_case_config()
        assert config1 is config2  # Same object reference
    
    @patch('core.sentence_case.load_yaml_config')
    @patch('os.path.exists')
    def test_config_loading_fallback(self, mock_exists, mock_load_yaml):
        """Test config loading with fallback to defaults"""
        import core.sentence_case
        core.sentence_case._CONFIG_CACHE = {}
        
        # Simulate no config file found
        mock_exists.return_value = False
        mock_load_yaml.side_effect = Exception("File not found")
        
        config = _load_sentence_case_config()
        
        # Should have default values
        assert 'mixed_case_words' in config
        assert 'LaTeX' in config['mixed_case_words']
        assert 'iPhone' in config['mixed_case_words']
        assert 'proper_adjectives' in config
        assert 'Bayesian' in config['proper_adjectives']


class TestExtractTitleWords:
    """Test title word extraction"""
    
    def test_simple_words(self):
        """Test extraction of simple words"""
        words = extract_title_words("Hello World")
        assert 'hello' in words
        assert 'world' in words
    
    def test_compound_terms(self):
        """Test extraction of compound terms with dashes"""
        words = extract_title_words("McKean-Vlasov SDEs")
        assert 'mckean-vlasov' in words
        assert 'mckean' in words
        assert 'vlasov' in words
        assert 'sdes' in words
    
    def test_multi_word_phrases(self):
        """Test extraction of multi-word phrases"""
        words = extract_title_words("Monte Carlo Methods")
        assert 'monte' in words
        assert 'carlo' in words
        assert 'methods' in words
        assert 'monte carlo' in words  # 2-word phrase
        assert 'carlo methods' in words  # 2-word phrase
        
    def test_apostrophes(self):
        """Test words with apostrophes"""
        words = extract_title_words("It's Ito's Lemma")
        assert "it's" in words
        assert "ito's" in words
        assert 'lemma' in words
    
    def test_unicode_dashes(self):
        """Test different dash types"""
        words = extract_title_words("Black–Scholes Model")  # en-dash
        assert 'black-scholes' in words  # normalized to hyphen
        assert 'model' in words


class TestFilterRelevantWhitelistTerms:
    """Test whitelist filtering optimization"""
    
    def test_exact_match_filtering(self):
        """Test exact word matching"""
        title = "Using PyTorch for ML"
        cap_whitelist = ["PyTorch", "TensorFlow", "Keras"]
        
        filtered_cap, _, _ = filter_relevant_whitelist_terms(
            title, cap_whitelist, [], []
        )
        
        assert "PyTorch" in filtered_cap
        assert "TensorFlow" not in filtered_cap  # Not in title
        assert "Keras" not in filtered_cap  # Not in title
    
    def test_dash_normalization_filtering(self):
        """Test filtering with dash normalization"""
        title = "McKean-Vlasov Equations"  # Regular hyphen
        dash_whitelist = ["McKean–Vlasov", "Black–Scholes"]  # En-dashes
        
        _, filtered_dash, _ = filter_relevant_whitelist_terms(
            title, [], dash_whitelist, []
        )
        
        assert "McKean–Vlasov" in filtered_dash  # Matched despite different dash
        assert "Black–Scholes" not in filtered_dash
    
    def test_compound_word_filtering(self):
        """Test filtering of compound terms"""
        title = "The Black Scholes Model"  # Space instead of dash
        cap_whitelist = ["Black-Scholes", "Monte-Carlo"]
        
        filtered_cap, _, _ = filter_relevant_whitelist_terms(
            title, cap_whitelist, [], []
        )
        
        assert "Black-Scholes" in filtered_cap  # Parts match
    
    def test_technical_prefix_filtering(self):
        """Test technical prefix filtering"""
        title = "g-expectation in finance"
        tech_whitelist = ["g", "h", "l^2"]
        
        _, _, filtered_tech = filter_relevant_whitelist_terms(
            title, [], [], tech_whitelist
        )
        
        assert "g" in filtered_tech
        assert "h" not in filtered_tech
        assert "l^2" not in filtered_tech


class TestToSentenceCaseAcademic:
    """Test main sentence case conversion function"""
    
    def test_empty_input(self):
        """Test empty and whitespace inputs"""
        assert to_sentence_case_academic("")[0] == "X"
        assert to_sentence_case_academic("   ")[0] == "X"
        assert to_sentence_case_academic("\n\t")[0] == "X"
    
    def test_debug_mode(self):
        """Test debug mode activation"""
        with patch('core.sentence_case.debug_print') as mock_debug:
            result, _ = to_sentence_case_academic("Test", debug=True)
            mock_debug.assert_called()  # Debug print was called
    
    def test_changed_flag(self):
        """Test the changed flag return value"""
        # No change needed
        result, changed = to_sentence_case_academic("AI")
        assert not changed
        
        # Change needed
        result, changed = to_sentence_case_academic("HELLO WORLD")
        assert changed
        assert result == "Hello world"
    
    def test_punctuation_only_input(self):
        """Test punctuation-only input"""
        result, _ = to_sentence_case_academic("!!!")
        assert result == "X !!!"
        
        result, _ = to_sentence_case_academic("...")
        assert result == "X ..."
    
    def test_emoji_stripping_edge_cases(self):
        """Test emoji stripping with various emojis"""
        # Using unicode escapes for emojis
        rocket_emoji = "\U0001F680"  # 🚀
        star_emoji = "\U0001F31F"    # 🌟
        
        # Single emoji
        result, _ = to_sentence_case_academic(f"{rocket_emoji} rocket")
        assert result == "Rocket"
        
        # Multiple emojis
        result, _ = to_sentence_case_academic(f"{rocket_emoji}{star_emoji} stars")
        assert result == "Stars"
        
        # Emoji in middle (not stripped)
        result, _ = to_sentence_case_academic(f"Hello {rocket_emoji} world")
        assert result == f"Hello {rocket_emoji} world"
    
    def test_number_conversion_edge_cases(self):
        """Test number-to-word conversion edge cases"""
        # Numbers at sentence start
        result, _ = to_sentence_case_academic("20 questions")
        assert result == "Twenty questions"
        
        # Numbers after punctuation
        result, _ = to_sentence_case_academic("Chapter 1: 5 methods")
        assert result == "Chapter 1: Five methods"
        
        # Numbers not at sentence start
        result, _ = to_sentence_case_academic("Page 10")
        assert result == "Page 10"
        
        # Numbers beyond conversion range
        result, _ = to_sentence_case_academic("21 pilots")
        assert result == "21 pilots"  # No conversion for 21
    
    def test_section_number_preservation(self):
        """Test section number detection"""
        # Various section number formats
        result, _ = to_sentence_case_academic("Section 1.2.3")
        assert result == "Section 1.2.3"
        
        result, _ = to_sentence_case_academic("Figure 3.14")
        assert result == "Figure 3.14"
        
        result, _ = to_sentence_case_academic("Table 2.1.4.5")
        assert result == "Table 2.1.4.5"
    
    def test_math_protection_integration(self):
        """Test math region protection"""
        # Math should be preserved
        result, _ = to_sentence_case_academic("The $\\alpha$-particle")
        assert "$\\alpha$" in result
        
        result, _ = to_sentence_case_academic("Using $$E = mc^2$$ formula")
        assert "$$E = mc^2$$" in result
    
    def test_whitelist_case_insensitive_matching(self):
        """Test case-insensitive whitelist matching"""
        cap_whitelist = ["COVID-19", "SARS-CoV-2"]
        
        # All caps input
        result, _ = to_sentence_case_academic("COVID-19 AND SARS-COV-2", 
                                             capitalization_whitelist=cap_whitelist)
        assert result == "COVID-19 and SARS-CoV-2"
        
        # Mixed case input
        result, _ = to_sentence_case_academic("Covid-19 and sars-cov-2", 
                                             capitalization_whitelist=cap_whitelist)
        assert result == "COVID-19 and SARS-CoV-2"
    
    def test_proper_adjective_case_preservation(self):
        """Test proper adjective handling"""
        # Built-in proper adjectives
        result, _ = to_sentence_case_academic("bayesian analysis")
        assert result == "Bayesian analysis"
        
        result, _ = to_sentence_case_academic("GAUSSIAN DISTRIBUTION")
        assert result == "Gaussian distribution"
        
        result, _ = to_sentence_case_academic("the laplacian operator")
        assert result == "The Laplacian operator"
    
    def test_mixed_case_word_preservation(self):
        """Test mixed-case brand names"""
        # First position
        result, _ = to_sentence_case_academic("iPhone Applications")
        assert result == "iPhone applications"
        
        # Middle position
        result, _ = to_sentence_case_academic("Using PyTorch Library")
        assert result == "Using PyTorch library"
        
        # Not in list (should be lowercased)
        result, _ = to_sentence_case_academic("MyCompany Software")
        assert result == "Mycompany software"
    
    def test_possessive_handling(self):
        """Test possessive forms"""
        # Possessive pronouns
        result, _ = to_sentence_case_academic("It's Working")
        assert result == "It's working"
        
        # Possessive acronyms
        result, _ = to_sentence_case_academic("AI's Future")
        assert result == "AI's future"
        
        # Regular possessives
        result, _ = to_sentence_case_academic("Smith's Theory")
        assert result == "Smith's theory"
    
    def test_colon_sentence_detection(self):
        """Test sentence detection after colons"""
        result, _ = to_sentence_case_academic("Chapter 1: introduction")
        assert result == "Chapter 1: Introduction"
        
        result, _ = to_sentence_case_academic("Note: this is important")
        assert result == "Note: This is important"
    
    def test_technical_prefix_preservation(self):
        """Test technical prefixes stay lowercase"""
        # At start of title
        result, _ = to_sentence_case_academic("g-expectation theory")
        assert result == "g-expectation theory"
        
        # Greek letter prefix
        alpha = "\u03B1"  # α
        result, _ = to_sentence_case_academic(f"{alpha}-decay process")
        assert result == f"{alpha}-decay process"
        
        # After sentence break
        result, _ = to_sentence_case_academic("Introduction. g-expectation")
        assert result == "Introduction. g-expectation"
    
    def test_complex_real_world_examples(self):
        """Test complex real-world title examples"""
        # Academic paper title
        result, _ = to_sentence_case_academic(
            "ON THE MCKEAN-VLASOV LIMIT FOR INTERACTING DIFFUSIONS",
            name_dash_whitelist=["McKean-Vlasov"]
        )
        assert result == "On the McKean-Vlasov limit for interacting diffusions"
        
        # Technical report
        result, _ = to_sentence_case_academic(
            "COVID-19 Impact on AI/ML: A PyTorch Case Study",
            capitalization_whitelist=["COVID-19", "PyTorch"]
        )
        assert result == "COVID-19 impact on AI/ML: A PyTorch case study"
        
        # Math paper
        result, _ = to_sentence_case_academic(
            "L^p SPACES AND THE LAPLACIAN OPERATOR"
        )
        assert result == "L^p spaces and the Laplacian operator"


class TestQuotedTitleCapitalisation:
    """Test that words starting a quoted title are capitalised."""

    def test_corrigendum_quoted_title(self):
        """Corrigendum for "A probabilistic work" — A must stay capitalised."""
        result, _ = to_sentence_case_academic('Corrigendum for "A Probabilistic Approach"')
        assert result == 'Corrigendum for "A probabilistic approach"'

    def test_on_quoted_title(self):
        """On "The art of mathematics" — The must stay capitalised."""
        result, _ = to_sentence_case_academic('On "The Art of Mathematics"')
        assert result == 'On "The art of mathematics"'

    def test_closing_quote_does_not_trigger(self):
        """the so-called "big" problem — 'big' must NOT be capitalised."""
        result, _ = to_sentence_case_academic('The So-Called "Big" Problem')
        assert result == 'The so-called "big" problem'

    def test_two_word_scare_quotes_stay_lowercase(self):
        """the "very big" problem — two-word scare quotes stay lowercase."""
        result, _ = to_sentence_case_academic('The "Very Big" Problem')
        assert result == 'The "very big" problem'

    def test_unicode_opening_quote(self):
        """Unicode opening quote \u201c should capitalise the next word."""
        result, _ = to_sentence_case_academic('Corrigendum for \u201cA Probabilistic Approach\u201d')
        assert result == 'Corrigendum for \u201cA probabilistic approach\u201d'

    def test_review_of_quoted_title(self):
        """Review of "Some Important Paper" — Some must stay capitalised."""
        result, _ = to_sentence_case_academic('Review of "Some Important Paper"')
        assert result == 'Review of "Some important paper"'

    def test_erratum_for_quoted(self):
        """Erratum for "An introduction to stochastic calculus" """
        result, _ = to_sentence_case_academic('Erratum for "An Introduction to Stochastic Calculus"')
        assert result == 'Erratum for "An introduction to stochastic calculus"'


class TestPossessiveWhitelistMatching:
    """Test that possessive forms of whitelisted names are preserved."""

    def test_euler_possessive(self):
        """Euler's theorem — Euler must stay capitalised via whitelist."""
        result, _ = to_sentence_case_academic(
            "Euler's Theorem on Polyhedra",
            capitalization_whitelist=["Euler"]
        )
        assert result == "Euler's theorem on polyhedra"

    def test_gauss_possessive(self):
        """Gauss's law — Gauss must stay capitalised via whitelist."""
        result, _ = to_sentence_case_academic(
            "Gauss's Law in Electrostatics",
            capitalization_whitelist=["Gauss"]
        )
        assert result == "Gauss's law in electrostatics"

    def test_multiple_possessives(self):
        """Multiple possessive whitelist names in one title."""
        result, _ = to_sentence_case_academic(
            "Gauss's and Euler's Theorems Revisited",
            capitalization_whitelist=["Gauss", "Euler"]
        )
        assert result == "Gauss's and Euler's theorems revisited"

    def test_curly_apostrophe_possessive(self):
        """Possessive with curly apostrophe \u2019."""
        result, _ = to_sentence_case_academic(
            "Euler\u2019s Theorem on Polyhedra",
            capitalization_whitelist=["Euler"]
        )
        assert result == "Euler\u2019s theorem on polyhedra"

    def test_non_whitelist_possessive_at_start(self):
        """Non-whitelisted name at sentence start keeps capital."""
        result, _ = to_sentence_case_academic("Smith's Paper on Mathematics")
        assert result == "Smith's paper on mathematics"


class TestMathTechnicalPrefixes:
    """Test MATH_TECHNICAL_PREFIXES constant"""
    
    def test_prefixes_content(self):
        """Test that technical prefixes are properly defined"""
        assert "g" in MATH_TECHNICAL_PREFIXES
        assert "l^2" in MATH_TECHNICAL_PREFIXES
        assert "\u03B1-synuclein" in MATH_TECHNICAL_PREFIXES  # α-synuclein
        assert "\u03C9-automata" in MATH_TECHNICAL_PREFIXES   # ω-automata
        
        # Greek letters
        assert "\u03B1" in MATH_TECHNICAL_PREFIXES  # α
        assert "\u03B2" in MATH_TECHNICAL_PREFIXES  # β
        assert "\u03C9" in MATH_TECHNICAL_PREFIXES  # ω


class TestNumbersConstant:
    """Test NUMBERS conversion dictionary"""
    
    def test_numbers_content(self):
        """Test number dictionary completeness"""
        assert NUMBERS['0'] == 'zero'
        assert NUMBERS['1'] == 'one'
        assert NUMBERS['10'] == 'ten'
        assert NUMBERS['20'] == 'twenty'
        
        # Check range
        assert len(NUMBERS) == 21  # 0-20


class TestDebugMode:
    """Test debug functionality"""
    
    @patch('core.io.print')
    def test_debug_print(self, mock_print):
        """Test debug print function"""
        import core.sentence_case as sc
        
        # Debug off
        sc.DEBUG_SENTENCE_CASE = False
        sc.debug_print("Test message")
        mock_print.assert_not_called()
        
        # Debug on
        sc.DEBUG_SENTENCE_CASE = True
        sc.debug_print("Test message")
        mock_print.assert_called_with("[DEBUG] Test message")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])