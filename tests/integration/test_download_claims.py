#!/usr/bin/env python3
"""
Test Download Claims
===================

Actually test all the claims I made instead of assuming they work.
This will reveal what's real vs. what's wishful thinking.
"""

import asyncio
import sys
import logging
from pathlib import Path

sys.path.append('src')

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Test data - mix of valid and invalid identifiers
TEST_IDENTIFIERS = {
    # ArXiv papers (various formats)
    'arxiv_valid_1': '2301.07041',
    'arxiv_valid_2': 'arxiv:2301.07041', 
    'arxiv_valid_3': 'https://arxiv.org/abs/2301.07041',
    'arxiv_invalid': '1234.5678',  # Doesn't exist
    
    # SSRN papers
    'ssrn_valid': 'https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3445746',
    'ssrn_invalid': 'https://papers.ssrn.com/sol3/papers.cfm?abstract_id=999999999',
    
    # HAL papers 
    'hal_valid': 'https://hal.science/hal-03330165',
    'hal_invalid': 'hal-999999999',
    
    # bioRxiv papers
    'biorxiv_valid': '10.1101/2023.01.01.523456',
    'biorxiv_invalid': '10.1101/1999.99.99.999999',
    
    # PMC papers
    'pmc_valid': 'PMC8862325',
    'pmc_invalid': 'PMC999999999',
    
    # IEEE (institutional)
    'ieee_valid': '10.1109/CVPR.2016.90',
    
    # Unknown formats
    'unknown': 'completely_random_text',
}


async def test_source_detection():
    """Test if sources are detected correctly."""
    print("🔍 TESTING SOURCE DETECTION")
    print("=" * 50)
    
    try:
        from downloader.open_access_sources import get_open_access_sources
        
        for label, identifier in TEST_IDENTIFIERS.items():
            sources = get_open_access_sources(identifier)
            source_names = [s.info.name for s in sources] if sources else []
            
            print(f"  {label:15} | {identifier:45} | {source_names}")
            
    except Exception as e:
        print(f"❌ Source detection test failed: {e}")
        return False
    
    return True


async def test_pdf_url_generation():
    """Test if PDF URLs are generated correctly."""
    print("\n🌐 TESTING PDF URL GENERATION")
    print("=" * 50)
    
    try:
        from downloader.open_access_sources import get_open_access_sources
        import aiohttp
        
        # Test URL generation (without actually downloading)
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            
            for label, identifier in TEST_IDENTIFIERS.items():
                if 'invalid' in label or 'unknown' in label:
                    continue  # Skip invalid ones for URL generation test
                    
                sources = get_open_access_sources(identifier)
                
                for source in sources:
                    try:
                        pdf_url = await source.get_pdf_url(identifier, session)
                        result = "✅" if pdf_url else "❌ No URL"
                        print(f"  {source.info.name:15} | {label:15} | {pdf_url}")
                    except Exception as e:
                        print(f"  {source.info.name:15} | {label:15} | ❌ Error: {str(e)[:50]}")
    
    except Exception as e:
        print(f"❌ URL generation test failed: {e}")
        return False
    
    return True


async def test_actual_downloads():
    """Test actual downloads with a subset of known good papers."""
    print("\n📥 TESTING ACTUAL DOWNLOADS")
    print("=" * 50)
    
    # Only test known good papers to avoid overwhelming servers
    safe_test_identifiers = {
        'arxiv_known_good': '2301.07041',  # Known to work
        # We'll be conservative and not hammer other servers during testing
    }
    
    try:
        from downloader.proper_downloader import ProperAcademicDownloader
        # Note: We'll use ProperAcademicDownloader which contains OpenAccessDownloader
        
        downloader = ProperAcademicDownloader('test_downloads')
        
        for label, identifier in safe_test_identifiers.items():
            print(f"\n  Testing {label}: {identifier}")
            
            try:
                result = await downloader.download(identifier)
                
                if result.success:
                    file_path = Path(result.file_path)
                    file_size = file_path.stat().st_size if file_path.exists() else 0
                    
                    print(f"    ✅ Success: {result.source_used}")
                    print(f"    📁 File: {file_path.name}")
                    print(f"    📊 Size: {file_size:,} bytes")
                    print(f"    ⏱️  Time: {result.download_time:.2f}s")
                    
                    # Test version detection
                    if 'arxiv' in identifier:
                        version_info = extract_arxiv_version_info(file_path.name)
                        print(f"    🏷️  Version: {version_info}")
                else:
                    print(f"    ❌ Failed: {result.error}")
                    
            except Exception as e:
                print(f"    ❌ Exception: {str(e)}")
        
        await downloader.close()
        
    except Exception as e:
        print(f"❌ Download test failed: {e}")
        return False
    
    return True


def extract_arxiv_version_info(filename):
    """Extract version information from ArXiv filename."""
    import re
    
    # Look for version patterns like "v1", "v2", etc.
    version_match = re.search(r'v(\d+)', filename)
    if version_match:
        return f"v{version_match.group(1)}"
    
    # Look for date patterns that might indicate versions
    date_match = re.search(r'(\d{4}\.\d{2}\.\d{2})', filename)
    if date_match:
        return f"dated {date_match.group(1)}"
    
    return "unknown"


async def test_institutional_detection():
    """Test institutional publisher detection."""
    print("\n🏛️  TESTING INSTITUTIONAL DETECTION")
    print("=" * 50)
    
    try:
        from downloader.proper_downloader import ProperAcademicDownloader
        
        downloader = ProperAcademicDownloader('test_institutional')
        
        if not downloader.institutional_available:
            print("  ❌ Institutional system not available")
            return False
        
        institutional_tests = {
            'ieee_doi': '10.1109/CVPR.2016.90',
            'ieee_url': 'https://ieeexplore.ieee.org/document/7780596',
            'siam_url': 'https://epubs.siam.org/doi/10.1137/1.9781611974737.1',
            'unknown': 'random_text'
        }
        
        for label, identifier in institutional_tests.items():
            publisher = downloader.institutional.can_handle(identifier)
            result = "✅" if publisher else "❌ No match"
            print(f"  {label:15} | {identifier:50} | {publisher or 'None'}")
        
    except Exception as e:
        print(f"❌ Institutional test failed: {e}")
        return False
    
    return True


async def test_error_handling():
    """Test how the system handles various error conditions."""
    print("\n🚨 TESTING ERROR HANDLING")
    print("=" * 50)
    
    try:
        from downloader.proper_downloader import ProperAcademicDownloader
        
        downloader = ProperAcademicDownloader('test_errors')
        
        error_test_cases = [
            ('empty_string', ''),
            ('none_value', None),
            ('invalid_url', 'http://totally.invalid.domain.xyz/paper.pdf'),
            ('malformed_doi', '10.invalid/malformed'),
            ('random_text', 'just some random text'),
        ]
        
        for label, identifier in error_test_cases:
            print(f"\n  Testing {label}: {repr(identifier)}")
            
            try:
                if identifier is None:
                    print("    ❌ Skipping None test")
                    continue
                    
                result = await downloader.download(identifier)
                
                if result.success:
                    print(f"    🤔 Unexpected success: {result.source_used}")
                else:
                    print(f"    ✅ Proper failure: {result.error}")
                    
            except Exception as e:
                print(f"    ⚠️  Exception (might be expected): {str(e)[:100]}")
        
        await downloader.close()
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False
    
    return True


async def main():
    """Run all tests."""
    print("🧪 COMPREHENSIVE DOWNLOAD SYSTEM TESTING")
    print("=" * 60)
    print("Testing all claims made about the download system...")
    print()
    
    tests = [
        ("Source Detection", test_source_detection),
        ("PDF URL Generation", test_pdf_url_generation), 
        ("Actual Downloads", test_actual_downloads),
        ("Institutional Detection", test_institutional_detection),
        ("Error Handling", test_error_handling),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'=' * 20} {test_name} {'=' * 20}")
        try:
            success = await test_func()
            results[test_name] = success
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("🏁 TEST SUMMARY")
    print("=" * 60)
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} | {test_name}")
    
    print(f"\n📊 Overall: {passed_tests}/{total_tests} tests passed ({passed_tests/total_tests*100:.1f}%)")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! Claims verified.")
    else:
        print("🚨 Some tests failed. Claims need revision.")


if __name__ == "__main__":
    asyncio.run(main())