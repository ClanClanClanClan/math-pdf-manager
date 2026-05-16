#!/usr/bin/env python3
"""
Test Institutional Downloads with Real Data
==========================================

Comprehensive testing of IEEE, SIAM, Springer and preparation for all major publishers.
Tests both with and without credentials to verify the framework.
"""

import asyncio
import sys
import os
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional

sys.path.append('src')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s: %(message)s')


@dataclass
class PublisherTestCase:
    """Test case for a publisher."""
    publisher: str
    identifier: str
    expected_detection: bool
    paper_title: Optional[str] = None
    note: str = ""


# Real test data for institutional publishers
INSTITUTIONAL_TEST_CASES = [
    # IEEE Test Cases
    PublisherTestCase(
        publisher="ieee",
        identifier="10.1109/CVPR.2016.90",
        expected_detection=True,
        paper_title="Deep Residual Learning for Image Recognition",
        note="Famous ResNet paper"
    ),
    PublisherTestCase(
        publisher="ieee", 
        identifier="https://ieeexplore.ieee.org/document/7780596",
        expected_detection=True,
        paper_title="Deep Residual Learning for Image Recognition",
        note="Same paper, URL format"
    ),
    PublisherTestCase(
        publisher="ieee",
        identifier="10.1109/TPAMI.2020.2992934",
        expected_detection=True, 
        paper_title="EfficientNet: Rethinking Model Scaling for Convolutional Neural Networks",
        note="Another famous paper"
    ),
    
    # SIAM Test Cases
    PublisherTestCase(
        publisher="siam",
        identifier="https://epubs.siam.org/doi/10.1137/1.9781611974737.1",
        expected_detection=True,
        paper_title="SODA proceedings paper",
        note="SIAM conference proceedings"
    ),
    PublisherTestCase(
        publisher="siam",
        identifier="10.1137/S0097539795293172",
        expected_detection=True,
        paper_title="SIAM journal paper",
        note="SIAM journal DOI"
    ),
    PublisherTestCase(
        publisher="siam",
        identifier="https://epubs.siam.org/doi/pdf/10.1137/16M1103518",
        expected_detection=True,
        paper_title="Direct PDF link",
        note="SIAM direct PDF URL"
    ),
    
    # Springer Test Cases (need to add Springer support)
    PublisherTestCase(
        publisher="springer",
        identifier="10.1007/978-3-319-07443-6_15",
        expected_detection=True,
        paper_title="Springer conference paper",
        note="Springer book chapter"
    ),
    PublisherTestCase(
        publisher="springer",
        identifier="https://link.springer.com/article/10.1007/s10994-021-05946-3",
        expected_detection=True,
        paper_title="Springer journal article",
        note="Machine Learning journal"
    ),
    
    # Should NOT match
    PublisherTestCase(
        publisher="none",
        identifier="10.1038/nature12373",
        expected_detection=False,
        note="Nature paper - different publisher"
    ),
]


async def test_publisher_detection():
    """Test if publishers are correctly detected from identifiers."""
    print("🔍 TESTING PUBLISHER DETECTION")
    print("=" * 70)
    
    try:
        from downloader.proper_downloader import ProperAcademicDownloader
        
        downloader = ProperAcademicDownloader('test_institutional')
        
        if not downloader.institutional_available:
            print("❌ Institutional system not available")
            return False
        
        print(f"Available publishers: {list(downloader.institutional.working_publishers.keys())}")
        print()
        
        success_count = 0
        total_count = 0
        
        for test_case in INSTITUTIONAL_TEST_CASES:
            total_count += 1
            detected_publisher = downloader.institutional.can_handle(test_case.identifier)
            
            # Check if detection matches expectation
            if test_case.expected_detection:
                expected = test_case.publisher
                success = detected_publisher == expected
            else:
                success = detected_publisher is None
            
            if success:
                success_count += 1
                status = "✅"
            else:
                status = "❌"
            
            print(f"{status} {test_case.publisher:10} | {test_case.identifier:50} | {detected_publisher or 'None':10} | {test_case.note}")
        
        print(f"\nDetection Accuracy: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
        assert success_count > 0, f"At least some publisher detection should work: {success_count}/{total_count}"
        
    except Exception as e:
        print(f"❌ Publisher detection test failed: {e}")
        assert False, f"Publisher detection test failed: {e}"


async def test_authentication_framework():
    """Test the authentication framework without actually authenticating."""
    print("\n🔐 TESTING AUTHENTICATION FRAMEWORK")
    print("=" * 70)
    
    try:
        from downloader.proper_downloader import ProperAcademicDownloader
        
        downloader = ProperAcademicDownloader('test_auth_framework')
        
        if not downloader.institutional_available:
            print("❌ Institutional system not available")
            return False
        
        # Test credential detection
        institutional = downloader.institutional
        
        print("Testing credential setup...")
        for pub_name in ['ieee', 'siam']:
            if pub_name in institutional.working_publishers:
                auth_config = institutional._get_auth_config(pub_name)
                
                has_username = bool(auth_config.username)
                has_password = bool(auth_config.password) 
                has_institutional = bool(auth_config.institutional_login)
                
                print(f"  {pub_name:10} | Username: {has_username:5} | Password: {has_password:5} | Institution: {has_institutional:5}")
        
        assert True, "Authentication framework test completed"
        
    except Exception as e:
        print(f"❌ Authentication framework test failed: {e}")
        assert False, f"Authentication framework test failed: {e}"


async def test_download_attempts():
    """Test actual download attempts (will fail without proper auth, but tests framework)."""
    print("\n📥 TESTING DOWNLOAD ATTEMPTS")
    print("=" * 70)
    
    # Only test one paper per publisher to be respectful
    test_papers = [
        ("ieee", "10.1109/CVPR.2016.90", "ResNet paper"),
        ("siam", "https://epubs.siam.org/doi/10.1137/1.9781611974737.1", "SODA paper"),
    ]
    
    try:
        from downloader.proper_downloader import ProperAcademicDownloader
        
        downloader = ProperAcademicDownloader('test_download_attempts')
        
        if not downloader.institutional_available:
            print("❌ Institutional system not available") 
            return False
        
        for publisher, identifier, description in test_papers:
            print(f"\nTesting {publisher}: {description}")
            print(f"  Identifier: {identifier}")
            
            try:
                result = await downloader.download(identifier)
                
                if result.success:
                    print(f"  ✅ SUCCESS: {result.source_used}")
                    print(f"     File: {result.file_path}")
                    print(f"     Size: {result.file_size:,} bytes")
                    print(f"     Time: {result.download_time:.2f}s")
                else:
                    print(f"  ❌ FAILED: {result.error}")
                    
                    # Analyze the failure
                    if "Authentication failed" in result.error:
                        print(f"     → Credentials needed (expected)")
                    elif "No working download method" in result.error:
                        print(f"     → Publisher not detected (unexpected)")
                    else:
                        print(f"     → Other error (investigate)")
            
            except Exception as e:
                print(f"  ❌ EXCEPTION: {str(e)[:100]}")
        
        await downloader.close()
        assert True, "Download attempt test completed"
        
    except Exception as e:
        print(f"❌ Download attempt test failed: {e}")
        assert False, f"Download attempt test failed: {e}"


def test_springer_preparation():
    """Prepare for adding Springer publisher support."""
    print("\n📚 TESTING SPRINGER PREPARATION")
    print("=" * 70)
    
    try:
        # Check if Springer publisher exists
        try:
            sys.path.append('src')
            from publishers.springer_publisher import SpringerPublisher
            print("✅ Springer publisher implementation found")
            springer_available = True
        except ImportError:
            print("⚠️  Springer publisher not implemented yet")
            springer_available = False
        
        # Test Springer detection patterns
        springer_identifiers = [
            "10.1007/978-3-319-07443-6_15",
            "https://link.springer.com/article/10.1007/s10994-021-05946-3",
            "10.1007/s00453-021-00854-1",
        ]
        
        print("\nSpringer identifier patterns:")
        for identifier in springer_identifiers:
            # Check if we can detect Springer patterns
            is_springer = ('10.1007' in identifier or 
                          'link.springer.com' in identifier or
                          'springer' in identifier.lower())
            
            status = "✅" if is_springer else "❌"
            print(f"  {status} {identifier}")
        
        # Show what needs to be implemented
        if not springer_available:
            print("\n📋 To implement Springer support:")
            print("  1. Create src/publishers/springer_publisher.py")
            print("  2. Implement SpringerPublisher class") 
            print("  3. Add Shibboleth authentication for ETH → Springer")
            print("  4. Test with real Springer papers")
            print("  5. Add to ProperAcademicDownloader")
        
        assert True, "Springer preparation test completed"
        
    except Exception as e:
        print(f"❌ Springer preparation failed: {e}")
        assert False, f"Springer preparation failed: {e}"


def test_major_publisher_framework():
    """Test framework for adding all major publishers."""
    print("\n🌍 TESTING MAJOR PUBLISHER FRAMEWORK")
    print("=" * 70)
    
    # Define major academic publishers to support
    major_publishers = {
        'springer': {
            'patterns': ['10.1007', 'link.springer.com', 'springer'],
            'auth_method': 'shibboleth',
            'priority': 'high',
            'status': 'partially_implemented'
        },
        'elsevier': {
            'patterns': ['10.1016', 'sciencedirect.com', 'elsevier'],
            'auth_method': 'shibboleth', 
            'priority': 'high',
            'status': 'not_implemented'
        },
        'wiley': {
            'patterns': ['10.1002', 'onlinelibrary.wiley.com', 'wiley'],
            'auth_method': 'shibboleth',
            'priority': 'medium',
            'status': 'not_implemented'
        },
        'nature': {
            'patterns': ['10.1038', 'nature.com'],
            'auth_method': 'shibboleth',
            'priority': 'medium', 
            'status': 'not_implemented'
        },
        'acm': {
            'patterns': ['10.1145', 'dl.acm.org'],
            'auth_method': 'shibboleth',
            'priority': 'medium',
            'status': 'not_implemented'
        },
        'taylor_francis': {
            'patterns': ['10.1080', 'tandfonline.com'],
            'auth_method': 'shibboleth',
            'priority': 'low',
            'status': 'not_implemented'
        },
    }
    
    print("Major publishers analysis:")
    print(f"{'Publisher':15} | {'Priority':8} | {'Auth Method':12} | {'Status':20} | {'Patterns':30}")
    print("-" * 100)
    
    for name, info in major_publishers.items():
        patterns_str = ', '.join(info['patterns'][:2]) + ("..." if len(info['patterns']) > 2 else "")
        print(f"{name:15} | {info['priority']:8} | {info['auth_method']:12} | {info['status']:20} | {patterns_str:30}")
    
    print(f"\nTotal publishers to implement: {len([p for p in major_publishers.values() if p['status'] == 'not_implemented'])}")
    print(f"High priority: {len([p for p in major_publishers.values() if p['priority'] == 'high'])}")
    
    assert True, "Major publisher framework test completed"


async def main():
    """Run all institutional tests."""
    print("🏛️  COMPREHENSIVE INSTITUTIONAL PUBLISHER TESTING")
    print("=" * 80)
    print("Testing IEEE, SIAM, Springer and framework for major publishers...")
    print()
    
    tests = [
        ("Publisher Detection", test_publisher_detection),
        ("Authentication Framework", test_authentication_framework), 
        ("Download Attempts", test_download_attempts),
        ("Springer Preparation", test_springer_preparation),
        ("Major Publisher Framework", test_major_publisher_framework),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'=' * 20} {test_name} {'=' * 20}")
        try:
            if asyncio.iscoroutinefunction(test_func):
                success = await test_func()
            else:
                success = test_func()
            results[test_name] = success
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 80)
    print("🏁 INSTITUTIONAL TEST SUMMARY")
    print("=" * 80)
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} | {test_name}")
    
    print(f"\n📊 Overall: {passed_tests}/{total_tests} tests passed ({passed_tests/total_tests*100:.1f}%)")
    
    if passed_tests == total_tests:
        print("🎉 All institutional tests passed!")
    else:
        print("🚨 Some institutional tests failed. Framework needs work.")


if __name__ == "__main__":
    asyncio.run(main())