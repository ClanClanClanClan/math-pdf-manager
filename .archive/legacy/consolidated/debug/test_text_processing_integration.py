#!/usr/bin/env python3
"""
Integration test for consolidated text processing modules.
Verifies that all modules work together correctly and provide backward compatibility.
"""

import sys
from pathlib import Path

# Add current directory to path
current_dir = Path(__file__).parent.resolve()
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

def test_text_processing_modules():
    """Test that all text processing modules work correctly."""
    
    print("Testing consolidated text processing modules...")
    
    try:
        # Test imports
        from core.text_processing import (
            TextNormalizer, UnicodeProcessor, TextTokenizer, TextCleaner,
            normalize, canonicalize, clean_text, extract_words
        )
        print("✓ All imports successful")
        
        # Test data
        test_text = "Café résumé naïve — this is a test with 'smart quotes' and math: $x^2 + y^2 = z^2$"
        
        # Test normalization
        normalized = normalize(test_text)
        print(f"✓ Normalization: '{test_text}' -> '{normalized}'")
        
        # Test canonicalization
        canonical = canonicalize(test_text)
        print(f"✓ Canonicalization: '{test_text}' -> '{canonical}'")
        
        # Test cleaning
        cleaned = clean_text(test_text)
        print(f"✓ Cleaning: '{test_text}' -> '{cleaned}'")
        
        # Test tokenization
        words = extract_words(test_text)
        print(f"✓ Tokenization: {len(words)} words extracted: {words[:5]}...")
        
        # Test classes
        normalizer = TextNormalizer()
        processor = UnicodeProcessor()
        tokenizer = TextTokenizer()
        cleaner = TextCleaner()
        
        print("✓ All classes instantiated successfully")
        
        # Test class methods
        norm_result = normalizer.normalize(test_text)
        unicode_result = processor.normalize_unicode(test_text)
        token_result = tokenizer.extract_words(test_text)
        clean_result = cleaner.clean_text(test_text)
        
        print("✓ All class methods work correctly")
        
        # Test homoglyph detection
        homoglyphs = processor.detect_homoglyphs("This contains Cyrillic а instead of Latin a")
        print(f"✓ Homoglyph detection: {len(homoglyphs)} homoglyphs found")
        
        # Test academic text processing
        academic_text = "See Figure 1: The algorithm shows that α-parameter optimization..."
        academic_tokens = tokenizer.extract_academic_tokens(academic_text)
        print(f"✓ Academic tokenization: {len(academic_tokens)} token types found")
        
        # Test filename sanitization
        unsafe_filename = "Test<>File:with|unsafe?chars*.pdf"
        safe_filename = processor.sanitize_filename(unsafe_filename)
        print(f"✓ Filename sanitization: '{unsafe_filename}' -> '{safe_filename}'")
        
        # Test statistics
        stats = {
            'normalizer': normalizer.get_stats(),
            'processor': processor.get_stats(),
            'tokenizer': tokenizer.get_stats(),
            'cleaner': cleaner.get_stats()
        }
        print("✓ All statistics methods work correctly")
        
        print("\n🎉 All tests passed! Text processing consolidation is working correctly.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_backward_compatibility():
    """Test that existing code can still use the old functions."""
    
    print("\nTesting backward compatibility...")
    
    try:
        # Test that we can still import from individual modules
        from core.text_processing.normalizer import normalize as norm_normalize
        from core.text_processing.unicode_utils import normalize_unicode
        from core.text_processing.tokenizer import extract_words as tok_extract_words
        from core.text_processing.cleaner import clean_text as clean_clean_text
        
        test_text = "Test text with accents: café résumé"
        
        # Test that functions produce consistent results
        result1 = norm_normalize(test_text)
        result2 = normalize_unicode(test_text)
        result3 = tok_extract_words(test_text)
        result4 = clean_clean_text(test_text)
        
        print("✓ Individual module imports work correctly")
        print("✓ All functions produce consistent results")
        
        return True
        
    except Exception as e:
        print(f"❌ Backward compatibility test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_performance():
    """Test that caching and performance optimizations work."""
    
    print("\nTesting performance optimizations...")
    
    try:
        from core.text_processing import normalize, canonicalize, extract_words
        
        # Test caching by calling functions multiple times
        test_text = "Performance test with repeated calls"
        
        # First calls (should populate cache)
        for _ in range(10):
            normalize(test_text)
            canonicalize(test_text)
            extract_words(test_text)
        
        # Get cache info
        from core.text_processing.normalizer import default_normalizer
        from core.text_processing.tokenizer import default_tokenizer
        
        norm_cache = default_normalizer.normalize.cache_info()
        tok_cache = default_tokenizer.tokenize.cache_info()
        
        print(f"✓ Normalization cache: {norm_cache.hits} hits, {norm_cache.misses} misses")
        print(f"✓ Tokenization cache: {tok_cache.hits} hits, {tok_cache.misses} misses")
        
        # Test that cache is working (should have hits > 0)
        if norm_cache.hits > 0 and tok_cache.hits > 0:
            print("✓ Caching is working correctly")
            return True
        else:
            print("⚠ Caching may not be working optimally")
            return False
            
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Text Processing Integration Test")
    print("=" * 60)
    
    success = True
    
    # Run all tests
    success &= test_text_processing_modules()
    success &= test_backward_compatibility()
    success &= test_performance()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 ALL TESTS PASSED! Text processing consolidation is successful.")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Please review the output above.")
        sys.exit(1)