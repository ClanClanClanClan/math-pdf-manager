#!/usr/bin/env python3
"""
Simple test to see if Sci-Hub is working at all
"""

import asyncio
from pathlib import Path

import requests

# Known DOIs that should exist in Sci-Hub
KNOWN_DOIS = [
    "10.1038/nature12373",  # Nature paper
    "10.1126/science.1259855",  # Science paper
    "10.1109/TPAMI.2020.3019330",  # IEEE TPAMI paper
]

SCIHUB_MIRRORS = [
    "https://sci-hub.se",
    "https://sci-hub.st", 
    "https://sci-hub.ru",
    "https://sci-hub.ee"
]

def test_scihub_simple():
    """Test Sci-Hub with simple HTTP requests"""
    
    print("🏴‍☠️ TESTING SCI-HUB MIRRORS")
    print("=" * 50)
    
    for doi in KNOWN_DOIS:
        print(f"\n📄 Testing DOI: {doi}")
        
        for mirror in SCIHUB_MIRRORS:
            try:
                url = f"{mirror}/{doi}"
                print(f"   Trying {mirror}...")
                
                # Simple HTTP request
                response = requests.get(url, timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                })
                
                print(f"      Status: {response.status_code}")
                
                if response.status_code == 200:
                    # Check if it looks like Sci-Hub page
                    if 'sci-hub' in response.text.lower():
                        print(f"      ✅ Sci-Hub page loaded")
                        
                        # Look for PDF indicators
                        if 'pdf' in response.text.lower():
                            print(f"      📄 PDF content detected")
                        
                        # Check for iframe/embed tags  
                        if '<iframe' in response.text or '<embed' in response.text:
                            print(f"      🎯 PDF embed found - SUCCESS!")
                            
                            # Try to extract PDF URL
                            import re
                            pdf_match = re.search(r'(https?://[^\s"\']+\.pdf)', response.text)
                            if pdf_match:
                                pdf_url = pdf_match.group(1)
                                print(f"      📥 PDF URL: {pdf_url[:50]}...")
                            
                        break
                    else:
                        print(f"      ❌ Not a Sci-Hub page")
                else:
                    print(f"      ❌ HTTP {response.status_code}")
                    
            except requests.exceptions.Timeout:
                print(f"      ⏰ Timeout")
            except requests.exceptions.ConnectionError:
                print(f"      🚫 Connection failed")
            except Exception as e:
                print(f"      ❌ Error: {str(e)[:30]}")
        
        print("-" * 50)

def test_known_working_doi():
    """Test with a DOI known to work on Sci-Hub"""
    
    # This Nature paper should definitely be on Sci-Hub
    doi = "10.1038/nature12373"
    
    print(f"\n🎯 FOCUSED TEST: {doi}")
    
    for mirror in SCIHUB_MIRRORS[:2]:  # Just test first 2
        try:
            url = f"{mirror}/{doi}"
            print(f"Testing: {url}")
            
            response = requests.get(url, timeout=15, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            })
            
            if response.status_code == 200:
                print("✅ Page loaded successfully")
                
                # Extract potential PDF URL
                import re
                patterns = [
                    r'<iframe[^>]+src="([^"]*\.pdf[^"]*)"',
                    r'<embed[^>]+src="([^"]*\.pdf[^"]*)"',
                    r'href="([^"]*\.pdf)"',
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, response.text)
                    if matches:
                        print(f"Found PDF URL: {matches[0]}")
                        
                        # Try to download first few bytes to verify
                        try:
                            pdf_response = requests.get(matches[0], 
                                                      timeout=10, 
                                                      headers={'Range': 'bytes=0-1023'})
                            if pdf_response.status_code in [200, 206]:
                                content = pdf_response.content
                                if content.startswith(b'%PDF'):
                                    print("🎉 CONFIRMED: PDF download works!")
                                    return True
                        except:
                            pass
            
        except Exception as e:
            print(f"Error: {e}")
    
    return False

if __name__ == "__main__":
    test_scihub_simple()
    test_known_working_doi()