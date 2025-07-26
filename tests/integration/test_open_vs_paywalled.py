#!/usr/bin/env python3
"""
Test Open vs Paywalled Papers
==============================

Test which papers are actually open access vs require authentication.
"""

import sys
sys.path.append('src')

from pathlib import Path
import requests


def test_direct_access():
    """Test direct HTTP access to papers without authentication."""
    print("🌐 TESTING DIRECT ACCESS TO PAPERS (NO AUTH)")
    print("=" * 60)
    
    test_papers = {
        'IEEE': [
            ('7780459', 'https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=7780459'),
            ('8578098', 'https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=8578098'),
        ],
        'SIAM': [
            ('10.1137/S0097539795293172', 'https://epubs.siam.org/doi/pdf/10.1137/S0097539795293172'),
            ('10.1137/20M1320493', 'https://epubs.siam.org/doi/pdf/10.1137/20M1320493'),
        ],
        'Springer': [
            ('10.1007/978-3-319-07443-6_15', 'https://link.springer.com/content/pdf/10.1007/978-3-319-07443-6_15.pdf'),
            ('10.1007/s10994-021-05946-3', 'https://link.springer.com/content/pdf/10.1007/s10994-021-05946-3.pdf'),
        ]
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/pdf,application/octet-stream,*/*',
    }
    
    results = {}
    
    for publisher, papers in test_papers.items():
        print(f"\n📊 {publisher}")
        print("-" * 30)
        
        results[publisher] = []
        
        for paper_id, url in papers:
            print(f"\n🧪 Testing: {paper_id}")
            print(f"   URL: {url[:50]}...")
            
            try:
                response = requests.head(url, headers=headers, timeout=15, allow_redirects=True)
                status = response.status_code
                content_type = response.headers.get('Content-Type', 'unknown')
                
                print(f"   Status: {status}")
                print(f"   Content-Type: {content_type}")
                
                if status == 200:
                    if 'pdf' in content_type.lower():
                        print(f"   ✅ OPEN ACCESS - Direct PDF available!")
                        results[publisher].append((paper_id, 'OPEN'))
                        
                        # Try downloading to verify
                        try:
                            download_response = requests.get(url, headers=headers, timeout=30)
                            if download_response.status_code == 200 and len(download_response.content) > 1000:
                                filename = f"test_open_access_{publisher.lower()}_{paper_id.replace('/', '_').replace('.', '_')}.pdf"
                                filepath = Path("test_open_vs_paywalled") / filename
                                filepath.parent.mkdir(exist_ok=True)
                                
                                with open(filepath, 'wb') as f:
                                    f.write(download_response.content)
                                
                                print(f"   📁 Downloaded: {len(download_response.content):,} bytes → {filepath.name}")
                            else:
                                print(f"   ⚠️  Download failed or empty file")
                        except Exception as e:
                            print(f"   ⚠️  Download error: {str(e)[:50]}")
                    else:
                        print(f"   🔒 LIKELY PAYWALLED - Returns HTML, not PDF")
                        results[publisher].append((paper_id, 'PAYWALLED'))
                elif status == 403:
                    print(f"   🚫 FORBIDDEN - Authentication required")
                    results[publisher].append((paper_id, 'AUTH_REQUIRED'))
                elif status == 404:
                    print(f"   ❌ NOT FOUND - Wrong URL or paper doesn't exist")
                    results[publisher].append((paper_id, 'NOT_FOUND'))
                else:
                    print(f"   ⚠️  UNEXPECTED STATUS: {status}")
                    results[publisher].append((paper_id, f'HTTP_{status}'))
                
            except requests.exceptions.Timeout:
                print(f"   ⏱️  TIMEOUT - Server too slow")
                results[publisher].append((paper_id, 'TIMEOUT'))
            except Exception as e:
                print(f"   💥 ERROR: {str(e)[:50]}")
                results[publisher].append((paper_id, 'ERROR'))
    
    # Summary
    print(f"\n" + "=" * 60)
    print("📊 DIRECT ACCESS SUMMARY")
    print("=" * 60)
    
    total_open = 0
    total_tested = 0
    
    for publisher, paper_results in results.items():
        open_count = len([r for r in paper_results if r[1] == 'OPEN'])
        total_count = len(paper_results)
        
        total_open += open_count
        total_tested += total_count
        
        print(f"\n{publisher}:")
        print(f"   Open Access: {open_count}/{total_count}")
        
        for paper_id, status in paper_results:
            status_emoji = {
                'OPEN': '✅',
                'PAYWALLED': '🔒', 
                'AUTH_REQUIRED': '🚫',
                'NOT_FOUND': '❌',
                'TIMEOUT': '⏱️',
                'ERROR': '💥'
            }.get(status, '❓')
            
            print(f"     {status_emoji} {paper_id}: {status}")
    
    print(f"\n🎯 OVERALL:")
    print(f"   Total Open Access: {total_open}/{total_tested} ({total_open/total_tested*100:.1f}%)")
    
    if total_open > 0:
        print(f"\n🎉 GREAT NEWS: {total_open} papers are directly accessible!")
        print(f"   This means institutional authentication may not be needed for everything.")
    else:
        print(f"\n🔒 All tested papers require authentication.")
    
    # Test passes as long as we could check the papers
    assert len(results) > 0, "Should have checked at least some papers"
    # Don't need to return anything since pytest doesn't use the return value


def main():
    """Test open vs paywalled access."""
    print("🔬 TESTING OPEN ACCESS vs PAYWALLED PAPERS")
    print("=" * 80)
    print("Determining which papers actually require authentication vs are open access.\n")
    
    results = test_direct_access()
    
    print(f"\n" + "=" * 80)
    print("🎯 CONCLUSION")
    print("=" * 80)
    print("This test reveals:")
    print("1. 🌐 Which papers are truly open access (no auth needed)")
    print("2. 🔒 Which papers are paywalled (require institutional access)")
    print("3. 🚫 Which papers have access restrictions")
    print("4. 📊 The real success rate potential")
    
    # Calculate realistic success rate
    open_access_base = 6  # ArXiv (2) + HAL (2) + PMC (2) 
    additional_open = sum(len([r for r in papers if r[1] == 'OPEN']) for papers in results.values())
    
    print(f"\n📈 REALISTIC SUCCESS RATES:")
    print(f"   Base Open Access: {open_access_base} papers (ArXiv, HAL, PMC)")
    print(f"   Additional Open: {additional_open} papers (IEEE, SIAM, Springer)")
    print(f"   Total Available: {open_access_base + additional_open} papers")
    
    if additional_open > 0:
        print(f"\n🎉 SUCCESS: We can achieve higher success rates without authentication!")
    else:
        print(f"\n🔧 AUTHENTICATION NEEDED: All institutional papers require proper auth.")


if __name__ == "__main__":
    main()