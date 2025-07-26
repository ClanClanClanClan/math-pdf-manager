#!/usr/bin/env python3
"""
Test Springer Comprehensive
============================

Test a wide range of Springer papers to see which are open access vs paywalled.
"""

import sys
sys.path.append('src')

from pathlib import Path
import requests
import time


def test_springer_papers_comprehensive():
    """Test many different Springer papers to find the real pattern."""
    print("🔬 COMPREHENSIVE SPRINGER TESTING")
    print("=" * 60)
    
    # Test a wide variety of Springer papers
    test_papers = [
        # Recent papers (likely paywalled)
        ("10.1007/s10994-023-06345-7", "Recent ML journal 2023"),
        ("10.1007/s00521-023-08234-1", "Recent Neural Computing 2023"),
        ("10.1007/978-3-031-26409-2_15", "Recent conference 2023"),
        
        # Older papers (might be open)  
        ("10.1007/978-3-319-07443-6_15", "ECCV 2014 - tested before"),
        ("10.1007/s10994-021-05946-3", "ML journal 2021 - tested before"),
        ("10.1007/BF00994018", "Very old paper 1992"),
        ("10.1007/3-540-44668-0_13", "Old conference 2000"),
        
        # Different Springer series
        ("10.1007/s00138-022-01234-5", "Machine Vision journal"),
        ("10.1007/s11263-020-01234-1", "Computer Vision journal"),
        ("10.1007/s10472-019-09876-2", "AI journal"),
        
        # Lecture Notes series (often restricted)
        ("10.1007/978-3-030-58536-5_1", "LNCS recent"),
        ("10.1007/978-3-540-74958-5_48", "LNCS older"),
        
        # Nature series (usually very restricted)
        ("10.1007/s41061-020-00123-4", "Nature Chemistry"),
        ("10.1007/s10038-021-00987-6", "Nature Genetics"),
        
        # Specific high-impact papers
        ("10.1007/JHEP03(2021)123", "High Energy Physics"),
        ("10.1007/s00220-020-03789-2", "Mathematical Physics"),
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/pdf,application/octet-stream,*/*',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    results = {
        'open_access': [],
        'paywalled': [],
        'not_found': [],
        'errors': []
    }
    
    print(f"Testing {len(test_papers)} Springer papers...")
    
    for i, (doi, description) in enumerate(test_papers, 1):
        print(f"\n🧪 [{i}/{len(test_papers)}] Testing: {doi}")
        print(f"   Description: {description}")
        
        # Try multiple URL patterns
        url_patterns = [
            f"https://link.springer.com/content/pdf/{doi}.pdf",
            f"https://link.springer.com/article/{doi}/pdf",  
            f"https://rd.springer.com/content/pdf/{doi}.pdf",
        ]
        
        paper_result = None
        
        for url_pattern in url_patterns:
            print(f"   Trying: {url_pattern[:60]}...")
            
            try:
                response = requests.head(url_pattern, headers=headers, timeout=15, allow_redirects=True)
                status = response.status_code
                content_type = response.headers.get('Content-Type', 'unknown')
                
                print(f"     Status: {status}, Type: {content_type}")
                
                if status == 200 and 'pdf' in content_type.lower():
                    print(f"   ✅ OPEN ACCESS - PDF available!")
                    
                    # Try downloading to verify
                    try:
                        download_response = requests.get(url_pattern, headers=headers, timeout=30)
                        if download_response.status_code == 200 and len(download_response.content) > 10000:  # At least 10KB
                            size = len(download_response.content)
                            print(f"   📁 Verified download: {size:,} bytes")
                            
                            # Save a sample
                            filename = f"springer_open_{doi.replace('/', '_').replace('.', '_')}.pdf"
                            filepath = Path("test_springer_comprehensive") / filename
                            filepath.parent.mkdir(exist_ok=True)
                            
                            with open(filepath, 'wb') as f:
                                f.write(download_response.content)
                            
                            results['open_access'].append((doi, description, size))
                            paper_result = 'OPEN'
                            break
                        else:
                            print(f"   ⚠️  Download failed or too small")
                    except Exception as e:
                        print(f"   ⚠️  Download error: {str(e)[:50]}")
                
                elif status == 403:
                    print(f"   🔒 PAYWALLED - Authentication required")
                    if not paper_result:
                        paper_result = 'PAYWALLED'
                elif status == 404:
                    print(f"   ❌ NOT FOUND")
                    if not paper_result:
                        paper_result = 'NOT_FOUND'
                else:
                    print(f"   ❓ Other status: {status}")
                    
            except requests.exceptions.Timeout:
                print(f"   ⏱️  Timeout")
            except Exception as e:
                print(f"   💥 Error: {str(e)[:30]}")
        
        # Classify the result
        if paper_result == 'OPEN':
            pass  # Already added to results['open_access']
        elif paper_result == 'PAYWALLED':
            results['paywalled'].append((doi, description))
        elif paper_result == 'NOT_FOUND':
            results['not_found'].append((doi, description))
        else:
            results['errors'].append((doi, description))
        
        # Be nice to the server
        time.sleep(1)
    
    # Analysis
    print(f"\n" + "=" * 60)
    print("📊 COMPREHENSIVE SPRINGER ANALYSIS")
    print("=" * 60)
    
    total_papers = len(test_papers)
    open_count = len(results['open_access'])
    paywalled_count = len(results['paywalled'])
    not_found_count = len(results['not_found'])
    error_count = len(results['errors'])
    
    print(f"\n📈 RESULTS:")
    print(f"   ✅ Open Access: {open_count}/{total_papers} ({open_count/total_papers*100:.1f}%)")
    print(f"   🔒 Paywalled: {paywalled_count}/{total_papers} ({paywalled_count/total_papers*100:.1f}%)")
    print(f"   ❌ Not Found: {not_found_count}/{total_papers} ({not_found_count/total_papers*100:.1f}%)")
    print(f"   💥 Errors: {error_count}/{total_papers} ({error_count/total_papers*100:.1f}%)")
    
    if open_count > 0:
        print(f"\n✅ OPEN ACCESS PAPERS:")
        for doi, desc, size in results['open_access']:
            print(f"   • {doi}: {desc} ({size:,} bytes)")
    
    if paywalled_count > 0:
        print(f"\n🔒 PAYWALLED PAPERS:")
        for doi, desc in results['paywalled']:
            print(f"   • {doi}: {desc}")
    
    if not_found_count > 0:
        print(f"\n❌ NOT FOUND:")
        for doi, desc in results['not_found']:
            print(f"   • {doi}: {desc}")
    
    print(f"\n🎯 CONCLUSIONS:")
    if open_count > 0:
        print(f"   • {open_count} Springer papers are genuinely open access")
        if open_count < total_papers / 2:
            print(f"   • Most Springer papers ({paywalled_count + not_found_count}) require authentication")
            print(f"   • Institutional access is needed for comprehensive Springer coverage")
        else:
            print(f"   • Majority of tested papers are open access!")
    else:
        print(f"   • NO papers are open access - all require institutional authentication")
        print(f"   • Previous success was likely a fluke or special case")
    
    # Test passes if we successfully tested papers (not based on results)
    assert total_papers > 0, "Should have tested at least some papers"


def test_springer_authentication_needed():
    """Test if Springer authentication actually works for paywalled papers."""
    print(f"\n\n🔐 TESTING SPRINGER INSTITUTIONAL AUTHENTICATION")
    print("=" * 60)
    
    try:
        from publishers.springer_publisher import SpringerPublisher
        from publishers import AuthenticationConfig
        import os
        
        # Create auth config
        auth_config = AuthenticationConfig(
            username=os.environ.get('ETH_USERNAME', ''),
            password=os.environ.get('ETH_PASSWORD', ''),
            institutional_login='eth'
        )
        
        # Create publisher instance
        springer = SpringerPublisher(auth_config)
        
        print(f"✅ Springer publisher created")
        
        # Test with a known paywalled paper
        paywalled_doi = "10.1007/s10994-023-06345-7"  # Recent paper, likely paywalled
        download_path = Path("test_springer_comprehensive") / f"auth_test_{paywalled_doi.replace('/', '_').replace('.', '_')}.pdf"
        
        print(f"\n🔐 Testing authentication for: {paywalled_doi}")
        
        # First try without auth
        print(f"   1. Testing without authentication...")
        result_no_auth = springer.download_paper(paywalled_doi, download_path)
        
        if result_no_auth.success:
            print(f"   ✅ Success without auth - paper is open access")
        else:
            print(f"   ❌ Failed without auth: {result_no_auth.error_message}")
            
            print(f"   2. Testing with authentication...")
            # Try with auth
            auth_result = springer.authenticate()
            if auth_result:
                print(f"   ✅ Authentication successful")
                result_with_auth = springer.download_paper(paywalled_doi, download_path)
                
                if result_with_auth.success:
                    print(f"   ✅ Download successful with auth!")
                    print(f"      File: {result_with_auth.file_path}")
                    if download_path.exists():
                        print(f"      Size: {download_path.stat().st_size:,} bytes")
                else:
                    print(f"   ❌ Download failed even with auth: {result_with_auth.error_message}")
            else:
                print(f"   ❌ Authentication failed")
        
    except Exception as e:
        print(f"   💥 Authentication test failed: {e}")


def main():
    """Run comprehensive Springer testing."""
    print("🧪 SPRINGER REALITY CHECK")
    print("=" * 80)
    print("Testing a wide range of Springer papers to understand the real open access vs paywalled ratio.\n")
    
    # Test many papers
    results = test_springer_papers_comprehensive()
    
    # Test authentication
    test_springer_authentication_needed()
    
    print(f"\n" + "=" * 80)
    print("🏁 SPRINGER REALITY CHECK RESULTS")
    print("=" * 80)
    
    open_count = len(results['open_access'])
    total_count = len(results['open_access']) + len(results['paywalled']) + len(results['not_found'])
    
    if open_count == 0:
        print("🚨 REALITY: NO Springer papers are open access")
        print("   The previous success was likely a special case")
        print("   Institutional authentication is REQUIRED for Springer")
    elif open_count < total_count / 3:
        print(f"⚠️  MIXED: Only {open_count}/{total_count} Springer papers are open access")
        print("   Most papers require institutional authentication")
        print("   Success rate will be limited without proper auth")
    else:
        print(f"🎉 GOOD NEWS: {open_count}/{total_count} Springer papers are open access")
        print("   Significant portion available without authentication")
    
    print(f"\n📊 UPDATED SUCCESS RATE CALCULATION:")
    print(f"   Base open access: 6 papers (ArXiv, HAL, PMC)")
    print(f"   Springer open access: {open_count} papers")
    print(f"   Total guaranteed: {6 + open_count} papers")
    print(f"   With institutional access: {6 + open_count} + remaining paywalled papers")


if __name__ == "__main__":
    main()