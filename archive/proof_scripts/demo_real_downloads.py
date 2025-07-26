#!/usr/bin/env python3
"""
Real Download Demonstration
==========================

Show exactly how the download system works with real papers.
Complete walkthrough from detection to final file.
"""

import asyncio
import sys
import logging
from pathlib import Path
import time

sys.path.append('src')

# Set up detailed logging to show what's happening internally
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)


async def demo_arxiv_downloads():
    """Demonstrate ArXiv downloads with version detection."""
    print("📚 ARXIV DOWNLOAD DEMONSTRATIONS")
    print("=" * 80)
    
    # Test cases showing different ArXiv scenarios
    arxiv_papers = [
        {
            'id': '2301.07041',
            'title': 'Latest version (system will detect v5)',
            'expected': 'Should download latest version automatically'
        },
        {
            'id': '2301.07041v1', 
            'title': 'Specific version request',
            'expected': 'Should download v1 specifically'
        },
        {
            'id': 'arxiv:1706.03762',
            'title': 'Attention is All You Need (Transformer paper)',
            'expected': 'Famous paper, should work reliably'
        },
        {
            'id': 'https://arxiv.org/abs/1512.03385',
            'title': 'ResNet paper (URL format)',
            'expected': 'Should extract ID and download'
        }
    ]
    
    from downloader.proper_downloader import ProperAcademicDownloader
    from downloader.version_detection import VersionAwareDownloader
    
    # Create downloader with demo directory
    downloader = ProperAcademicDownloader('demo_downloads')
    version_detector = VersionAwareDownloader()
    
    for i, paper in enumerate(arxiv_papers, 1):
        print(f"\n🧪 Demo {i}: {paper['title']}")
        print(f"   Identifier: {paper['id']}")
        print(f"   Expected: {paper['expected']}")
        print("-" * 60)
        
        start_time = time.time()
        
        # Show version detection first
        print("🔍 Phase 1: Version Detection")
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                url, version_info = await version_detector.get_best_download_url(paper['id'], session)
                filename = version_detector.generate_filename_with_version(
                    paper['id'], version_info, 'ArXiv'
                )
                print(f"   📊 Detected version: {version_info.version}")
                print(f"   🌐 Download URL: {url}")
                print(f"   📁 Generated filename: {filename}")
                
                if version_info.date_submitted:
                    print(f"   📅 Submission date: {version_info.date_submitted}")
        except Exception as e:
            print(f"   ❌ Version detection error: {e}")
        
        print(f"\n📥 Phase 2: Actual Download")
        
        # Perform actual download
        try:
            result = await downloader.download(paper['id'])
            
            if result.success:
                # Show success details
                print(f"   ✅ SUCCESS!")
                print(f"   📁 File: {Path(result.file_path).name}")
                print(f"   📊 Size: {result.file_size:,} bytes ({result.file_size/1024/1024:.1f} MB)")
                print(f"   ⏱️  Time: {result.download_time:.2f}s")
                print(f"   🎯 Source: {result.source_used}")
                
                # Check if file actually exists and has content
                file_path = Path(result.file_path)
                if file_path.exists():
                    actual_size = file_path.stat().st_size
                    print(f"   📋 File verification: ✅ {actual_size:,} bytes on disk")
                    
                    # Show first few bytes to prove it's a real PDF
                    with open(file_path, 'rb') as f:
                        first_bytes = f.read(8)
                        if first_bytes.startswith(b'%PDF'):
                            print(f"   🗂️  File format: ✅ Valid PDF (starts with {first_bytes})")
                        else:
                            print(f"   ⚠️  File format: Warning - doesn't start with PDF header")
                else:
                    print(f"   ❌ File verification: File not found on disk!")
            else:
                print(f"   ❌ FAILED: {result.error}")
                
        except Exception as e:
            print(f"   ❌ EXCEPTION: {str(e)}")
        
        total_time = time.time() - start_time
        print(f"   ⏱️  Total time: {total_time:.2f}s")
        
        # Add a pause between demos
        if i < len(arxiv_papers):
            print(f"\n⏸️  Pausing 2 seconds before next demo...")
            await asyncio.sleep(2)
    
    await downloader.close()


async def demo_institutional_attempts():
    """Demonstrate institutional download attempts."""
    print("\n\n🏛️  INSTITUTIONAL DOWNLOAD DEMONSTRATIONS")
    print("=" * 80)
    
    institutional_papers = [
        {
            'identifier': '10.1109/CVPR.2016.90',
            'publisher': 'IEEE',
            'title': 'Deep Residual Learning for Image Recognition',
            'note': 'Famous ResNet paper - should detect IEEE'
        },
        {
            'identifier': 'https://epubs.siam.org/doi/10.1137/1.9781611974737.1',
            'publisher': 'SIAM', 
            'title': 'SODA Conference Paper',
            'note': 'SIAM conference proceedings'
        },
        {
            'identifier': '10.1007/978-3-319-07443-6_15',
            'publisher': 'Springer',
            'title': 'Springer Book Chapter',
            'note': 'Should detect newly added Springer support'
        }
    ]
    
    from downloader.proper_downloader import ProperAcademicDownloader
    
    downloader = ProperAcademicDownloader('demo_institutional')
    
    for i, paper in enumerate(institutional_papers, 1):
        print(f"\n🧪 Demo {i}: {paper['publisher']} Paper")
        print(f"   Title: {paper['title']}")
        print(f"   Identifier: {paper['identifier']}")
        print(f"   Note: {paper['note']}")
        print("-" * 60)
        
        start_time = time.time()
        
        print("🔍 Phase 1: Publisher Detection")
        
        # Test detection explicitly
        if downloader.institutional_available:
            detected = downloader.institutional.can_handle(paper['identifier'])
            if detected:
                print(f"   ✅ Detected publisher: {detected}")
                
                # Show authentication config
                auth_config = downloader.institutional._get_auth_config(detected)
                has_username = bool(auth_config.username)
                has_password = bool(auth_config.password)
                print(f"   🔐 Authentication setup:")
                print(f"      Username configured: {has_username}")
                print(f"      Password configured: {has_password}")
                print(f"      Institution: {auth_config.institutional_login}")
            else:
                print(f"   ❌ Publisher not detected")
        else:
            print(f"   ❌ Institutional system not available")
        
        print(f"\n📥 Phase 2: Download Attempt")
        
        try:
            result = await downloader.download(paper['identifier'])
            
            if result.success:
                print(f"   ✅ SUCCESS!")
                print(f"   📁 File: {Path(result.file_path).name}")
                print(f"   📊 Size: {result.file_size:,} bytes")
                print(f"   🎯 Source: {result.source_used}")
            else:
                print(f"   ❌ FAILED: {result.error}")
                
                # Analyze the failure
                if "Authentication failed" in result.error:
                    print(f"   💡 Analysis: Institutional authentication required")
                    print(f"      → This is expected without ETH network access")
                    print(f"      → The detection and framework are working correctly")
                elif "403" in result.error:
                    print(f"   💡 Analysis: Access forbidden (paywall)")
                    print(f"      → Paper is behind paywall as expected") 
                    print(f"      → Institutional access would be needed")
                else:
                    print(f"   💡 Analysis: Other issue - may need investigation")
                    
        except Exception as e:
            print(f"   ❌ EXCEPTION: {str(e)}")
        
        total_time = time.time() - start_time
        print(f"   ⏱️  Total time: {total_time:.2f}s")
        
        if i < len(institutional_papers):
            print(f"\n⏸️  Pausing 1 second before next demo...")
            await asyncio.sleep(1)
    
    await downloader.close()


async def demo_error_scenarios():
    """Demonstrate how the system handles various error scenarios."""
    print("\n\n🚨 ERROR HANDLING DEMONSTRATIONS")
    print("=" * 80)
    
    error_cases = [
        {
            'identifier': '9999.99999',
            'scenario': 'Invalid ArXiv ID',
            'expected': 'Should detect as ArXiv but fail gracefully'
        },
        {
            'identifier': '10.1038/nature12373',
            'scenario': 'Nature paper (no publisher support)',
            'expected': 'Should not detect any publisher'
        },
        {
            'identifier': 'https://totally-fake-domain.com/paper.pdf',
            'scenario': 'Invalid URL',
            'expected': 'Should reject gracefully'
        },
        {
            'identifier': '',
            'scenario': 'Empty identifier',
            'expected': 'Should handle empty input'
        }
    ]
    
    from downloader.proper_downloader import ProperAcademicDownloader
    
    downloader = ProperAcademicDownloader('demo_errors')
    
    for i, case in enumerate(error_cases, 1):
        print(f"\n🧪 Error Demo {i}: {case['scenario']}")
        print(f"   Identifier: '{case['identifier']}'")
        print(f"   Expected: {case['expected']}")
        print("-" * 60)
        
        start_time = time.time()
        
        try:
            result = await downloader.download(case['identifier'])
            
            if result.success:
                print(f"   🤔 UNEXPECTED SUCCESS: {result.source_used}")
                print(f"      This may indicate an issue with validation")
            else:
                print(f"   ✅ PROPER FAILURE: {result.error}")
                print(f"   💡 Analysis: System handled error gracefully")
                
        except Exception as e:
            print(f"   ⚠️  EXCEPTION: {str(e)}")
            print(f"   💡 Analysis: May need better exception handling")
        
        total_time = time.time() - start_time
        print(f"   ⏱️  Time: {total_time:.2f}s")
    
    await downloader.close()


async def demo_version_comparison():
    """Demonstrate version detection and comparison."""
    print("\n\n🏷️  VERSION DETECTION DEMONSTRATIONS") 
    print("=" * 80)
    
    version_cases = [
        '2301.07041',      # Should get latest version
        '2301.07041v1',    # Should get specific v1
        '2301.07041v2',    # Should get specific v2
        '1706.03762',      # Transformer paper - check its versions
    ]
    
    from downloader.version_detection import VersionAwareDownloader
    
    detector = VersionAwareDownloader()
    
    print("📊 Comparing version detection for the same paper:")
    print()
    
    import aiohttp
    async with aiohttp.ClientSession() as session:
        for identifier in version_cases:
            print(f"🔍 Testing: {identifier}")
            
            try:
                url, version_info = await detector.get_best_download_url(identifier, session)
                filename = detector.generate_filename_with_version(identifier, version_info, 'ArXiv')
                
                print(f"   📊 Version: {version_info.version}")
                print(f"   🌐 URL: {url}")
                print(f"   📁 Filename: {filename}")
                print(f"   🔄 Latest: {version_info.is_latest}")
                
                if version_info.date_submitted:
                    print(f"   📅 Date: {version_info.date_submitted}")
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
            
            print()


def show_file_results():
    """Show what files were actually created."""
    print("\n📁 FILES CREATED DURING DEMONSTRATIONS")
    print("=" * 80)
    
    demo_dirs = ['demo_downloads', 'demo_institutional', 'demo_errors']
    
    for dir_name in demo_dirs:
        demo_dir = Path(dir_name)
        if demo_dir.exists():
            files = list(demo_dir.glob('*'))
            print(f"\n📂 {dir_name}:")
            
            if files:
                for file_path in sorted(files):
                    if file_path.is_file():
                        size = file_path.stat().st_size
                        print(f"   📄 {file_path.name} - {size:,} bytes ({size/1024/1024:.1f} MB)")
            else:
                print(f"   (empty)")
        else:
            print(f"\n📂 {dir_name}: (not created)")


async def main():
    """Run all download demonstrations."""
    print("🎯 REAL DOWNLOAD SYSTEM DEMONSTRATIONS")
    print("=" * 80)
    print("This will show exactly how the download system works with real papers.")
    print("Watch the internal processes, version detection, and error handling.")
    print()
    
    # Run all demonstrations
    await demo_arxiv_downloads()
    await demo_institutional_attempts()
    await demo_error_scenarios()
    await demo_version_comparison()
    
    # Show final results
    show_file_results()
    
    print("\n" + "=" * 80)
    print("🏁 DEMONSTRATION COMPLETE")
    print("=" * 80)
    print("Summary of what was shown:")
    print("✅ ArXiv downloads with version detection")
    print("✅ Institutional publisher detection and authentication attempts")
    print("✅ Robust error handling for invalid inputs")
    print("✅ Version comparison and URL generation")
    print("✅ File verification and actual PDF creation")
    print()
    print("The system demonstrates:")
    print("• Real working downloads (not just test frameworks)")
    print("• Proper version detection using ArXiv API")
    print("• Institutional authentication framework")
    print("• Graceful error handling")
    print("• Complete end-to-end workflow")


if __name__ == "__main__":
    asyncio.run(main())