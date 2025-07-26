#!/usr/bin/env python3
"""
Test SIAM Publisher with Multiple Papers
========================================

Test various SIAM papers to determine download success rate.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from publishers.siam_publisher import SIAMPublisher
from publishers import AuthenticationConfig
from secure_credential_manager import get_credential_manager

# Test papers from different SIAM journals and time periods
TEST_PAPERS = [
    {
        "doi": "10.1137/S0097539795293172", 
        "title": "SIAM J. Computing - Classic paper",
        "type": "journal"
    },
    {
        "doi": "10.1137/20M1320493",
        "title": "SIAM J. Applied Math - Recent paper", 
        "type": "journal"
    },
    {
        "doi": "10.1137/1.9781611974737.1",
        "title": "SODA proceedings - Conference",
        "type": "conference"
    },
    {
        "doi": "10.1137/16M1103518", 
        "title": "SIAM J. Matrix Analysis",
        "type": "journal"
    },
    {
        "doi": "10.1137/S0036142901389049",
        "title": "SIAM J. Numerical Analysis - Older paper",
        "type": "journal"
    },
    {
        "doi": "10.1137/21M1406854",
        "title": "SIAM J. Optimization - Recent",
        "type": "journal"
    },
    {
        "doi": "10.1137/S0895479801387551",
        "title": "SIAM J. Matrix Analysis - Classic",
        "type": "journal"
    },
    {
        "doi": "10.1137/19M1244421",
        "title": "SIAM J. Scientific Computing",
        "type": "journal"
    }
]

def test_siam_multiple_papers():
    """Test SIAM with multiple papers to check success rate."""
    
    print("🧪 TESTING SIAM WITH MULTIPLE PAPERS")
    print("=" * 60)
    print(f"Testing {len(TEST_PAPERS)} different SIAM papers...")
    print()
    
    # Get credentials
    cm = get_credential_manager()
    username, password = cm.get_eth_credentials()
    
    if not username or not password:
        print("❌ No ETH credentials found!")
        return
    
    # Create authentication config
    auth_config = AuthenticationConfig(
        username=username,
        password=password,
        institutional_login='eth'
    )
    
    # Create SIAM publisher (will authenticate once)
    siam = SIAMPublisher(auth_config)
    
    print("🔐 Authenticating with SIAM...")
    auth_success = siam.authenticate()
    
    if not auth_success:
        print("❌ Authentication failed!")
        return
    
    print("✅ Authentication successful!")
    print()
    
    # Test each paper
    results = []
    output_dir = Path("siam_multiple_test")
    output_dir.mkdir(exist_ok=True)
    
    for i, paper in enumerate(TEST_PAPERS, 1):
        print(f"📄 [{i}/{len(TEST_PAPERS)}] {paper['title']}")
        print(f"   DOI: {paper['doi']}")
        print(f"   Type: {paper['type']}")
        
        # Create output path
        safe_title = paper['title'].replace(' ', '_').replace('/', '_').replace('.', '_')[:50]
        output_path = output_dir / f"{safe_title}.pdf"
        
        try:
            # Check if SIAM can handle this DOI
            if not siam.can_handle(paper['doi']):
                print("   ❌ DOI not recognized as SIAM")
                results.append({
                    'paper': paper,
                    'success': False,
                    'error': 'DOI not recognized',
                    'size': 0
                })
                continue
            
            # Attempt download
            print("   📥 Downloading...")
            result = siam.download_paper(paper['doi'], output_path)
            
            if result.success:
                file_size = output_path.stat().st_size if output_path.exists() else 0
                print(f"   ✅ SUCCESS - {file_size:,} bytes")
                
                # Verify it's a valid PDF
                if output_path.exists():
                    with open(output_path, 'rb') as f:
                        header = f.read(4)
                        if header == b'%PDF':
                            print("   ✅ Valid PDF confirmed")
                            results.append({
                                'paper': paper,
                                'success': True,
                                'error': None,
                                'size': file_size
                            })
                        else:
                            print("   ❌ Invalid PDF file")
                            results.append({
                                'paper': paper,
                                'success': False,
                                'error': 'Invalid PDF',
                                'size': file_size
                            })
                else:
                    print("   ❌ File not found after download")
                    results.append({
                        'paper': paper,
                        'success': False,
                        'error': 'File not found',
                        'size': 0
                    })
            else:
                print(f"   ❌ FAILED - {result.error_message}")
                results.append({
                    'paper': paper,
                    'success': False,
                    'error': result.error_message,
                    'size': 0
                })
                
        except Exception as e:
            print(f"   💥 ERROR - {str(e)[:100]}")
            results.append({
                'paper': paper,
                'success': False,
                'error': str(e),
                'size': 0
            })
        
        print()
    
    # Summary
    print("=" * 60)
    print("📊 SUMMARY RESULTS")
    print("=" * 60)
    
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    success_rate = len(successful) / len(results) * 100 if results else 0
    total_size = sum(r['size'] for r in successful)
    
    print(f"Total papers tested: {len(results)}")
    print(f"✅ Successful downloads: {len(successful)}")
    print(f"❌ Failed downloads: {len(failed)}")
    print(f"📈 Success rate: {success_rate:.1f}%")
    print(f"📁 Total downloaded: {total_size:,} bytes")
    
    if successful:
        print(f"\n✅ SUCCESSFUL DOWNLOADS:")
        for result in successful:
            paper = result['paper']
            print(f"   • {paper['title']}: {result['size']:,} bytes")
    
    if failed:
        print(f"\n❌ FAILED DOWNLOADS:")
        for result in failed:
            paper = result['paper'] 
            print(f"   • {paper['title']}: {result['error']}")
    
    print()
    
    # Analysis
    if success_rate >= 80:
        print("🎉 EXCELLENT: SIAM publisher has high success rate!")
        print("   Ready for production use with multiple papers.")
    elif success_rate >= 60:
        print("✅ GOOD: SIAM publisher works for most papers.")
        print("   Some papers may require additional handling.")
    elif success_rate >= 40:
        print("⚠️  MODERATE: SIAM publisher works for some papers.")
        print("   Needs improvement for broader coverage.")
    else:
        print("❌ POOR: SIAM publisher has low success rate.")
        print("   Requires significant fixes before production use.")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    if len(successful) > 0:
        avg_size = total_size // len(successful) if successful else 0
        print(f"   • Average PDF size: {avg_size:,} bytes")
        print(f"   • Authentication system is working")
        
    if len(failed) > 0:
        # Analyze common failure patterns
        error_types = {}
        for result in failed:
            error = result['error'] or 'Unknown'
            error_types[error] = error_types.get(error, 0) + 1
        
        print(f"   • Common failure patterns:")
        for error, count in error_types.items():
            print(f"     - {error}: {count} papers")
    
    return success_rate >= 70  # Consider 70%+ as success

if __name__ == "__main__":
    success = test_siam_multiple_papers()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 SIAM MULTI-PAPER TEST: SUCCESS")
    else:
        print("❌ SIAM MULTI-PAPER TEST: NEEDS IMPROVEMENT")
    print("=" * 60)
    
    sys.exit(0 if success else 1)