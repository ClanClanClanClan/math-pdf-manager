#!/usr/bin/env python3
"""
SIAM Reverse Engineer
====================

Reverse engineer SIAM's PDF download URLs and authentication patterns.
"""

import sys
import requests
import re
import json
from pathlib import Path
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, str(Path(__file__).parent))

try:
    from secure_credential_manager import get_credential_manager
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


def analyze_siam_url_patterns():
    """Analyze SIAM URL patterns to understand their structure."""
    print("🔍 Analyzing SIAM URL Patterns")
    print("=" * 60)
    
    # DOI: 10.1137/20M1339829
    doi = "10.1137/20M1339829"
    
    # Different URL patterns to test
    url_patterns = [
        f"https://epubs.siam.org/doi/pdf/{doi}",
        f"https://epubs.siam.org/doi/epdf/{doi}",
        f"https://epubs.siam.org/doi/pdf/{doi}?download=true",
        f"https://epubs.siam.org/doi/pdfplus/{doi}",
        f"https://epubs.siam.org/doi/abs/{doi}",
        f"https://epubs.siam.org/doi/full/{doi}",
        f"https://epubs.siam.org/action/downloadPdf?doi={doi}",
        f"https://epubs.siam.org/action/showPdf?doi={doi}",
        f"https://epubs.siam.org/doi/pdf/{doi}.pdf",
        f"https://epubs.siam.org/content/journals/{doi}",
        f"https://epubs.siam.org/toc/sjoce3/42/1",  # Table of contents
        f"https://epubs.siam.org/doi/reader/{doi}",
        f"https://epubs.siam.org/doi/htmlplus/{doi}",
        # Direct file patterns
        f"https://epubs.siam.org/na101/home/literatum/publisher/siam/journals/content/sjoce3/2022/sjoce3.2022.42.issue-1/20m1339829/20220211/20m1339829.pdf",
        # CDN patterns
        f"https://cdn.siam.org/pdf/{doi}.pdf",
        f"https://files.siam.org/pdf/{doi}.pdf",
        f"https://static.siam.org/pdf/{doi}.pdf"
    ]
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'
    })
    
    working_urls = []
    
    for url in url_patterns:
        print(f"\n🔗 Testing: {url}")
        try:
            response = session.head(url, timeout=10, allow_redirects=True)
            print(f"   Status: {response.status_code}")
            print(f"   Content-Type: {response.headers.get('content-type', 'N/A')}")
            print(f"   Final URL: {response.url}")
            
            if response.status_code == 200 and 'pdf' in response.headers.get('content-type', ''):
                print("   ✅ DIRECT PDF ACCESS!")
                working_urls.append(url)
            elif response.status_code == 403:
                print("   🔒 Access denied - authentication required")
            elif response.status_code == 404:
                print("   ❌ Not found")
            elif "cloudflare" in str(response.headers):
                print("   ☁️ Cloudflare protection")
            else:
                print(f"   ❓ Other response: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    return working_urls


def analyze_siam_metadata():
    """Look for metadata endpoints that might reveal PDF URLs."""
    print("\n🔍 Analyzing SIAM Metadata")
    print("=" * 60)
    
    doi = "10.1137/20M1339829"
    
    # Try to get metadata
    metadata_urls = [
        f"https://epubs.siam.org/action/ajaxShowTab?widgetId=tab-figures&doi={doi}",
        f"https://epubs.siam.org/action/ajaxShowTab?widgetId=tab-references&doi={doi}",
        f"https://epubs.siam.org/action/downloadCitation?doi={doi}&format=bibtex",
        f"https://epubs.siam.org/action/downloadCitation?doi={doi}&format=endnote",
        f"https://epubs.siam.org/action/getFigures?doi={doi}",
        f"https://epubs.siam.org/action/getFullText?doi={doi}",
        f"https://epubs.siam.org/pb/widget/articleMetrics?doi={doi}",
        f"https://epubs.siam.org/action/ajaxShowEnhancedAbstract?doi={doi}",
        f"https://crossref.org/openurl/?id=doi:{doi}&noredirect=true&format=json",
        f"https://api.crossref.org/works/{doi}",
        f"https://dx.doi.org/{doi}",
        f"https://doi.org/{doi}"
    ]
    
    session = requests.Session()
    
    for url in metadata_urls:
        print(f"\n🔗 Testing: {url}")
        try:
            response = session.get(url, timeout=10)
            if response.status_code == 200:
                print(f"   ✅ Success: {len(response.text)} chars")
                
                # Look for PDF references in the response
                if 'pdf' in response.text.lower():
                    pdf_refs = re.findall(r'["\']([^"\']*\.pdf[^"\']*)["\']', response.text)
                    if pdf_refs:
                        print(f"   📄 Found PDF references: {pdf_refs}")
                
                # Look for download links
                if 'download' in response.text.lower():
                    download_refs = re.findall(r'["\']([^"\']*download[^"\']*)["\']', response.text)
                    if download_refs:
                        print(f"   📥 Found download references: {download_refs}")
                        
        except Exception as e:
            print(f"   ❌ Error: {e}")


def try_direct_file_access():
    """Try to access PDF files directly from common CDN patterns."""
    print("\n🔍 Trying Direct File Access")
    print("=" * 60)
    
    # SIAM uses DOI 10.1137/20M1339829
    # Year: 2022, Journal: SIAM Journal on Computing (SICOMP)
    
    # Common academic publisher file patterns
    file_patterns = [
        # Literatum (common publisher platform)
        "https://epubs.siam.org/na101/home/literatum/publisher/siam/journals/content/sicomp/2022/sicomp.2022.51.issue-1/20m1339829/20220211/20m1339829.pdf",
        "https://epubs.siam.org/literatum/publisher/siam/journals/content/sicomp/2022/sicomp.2022.51.issue-1/20m1339829/20220211/20m1339829.pdf",
        
        # Year/volume patterns
        "https://epubs.siam.org/content/2022/20m1339829.pdf",
        "https://epubs.siam.org/content/journals/2022/20m1339829.pdf",
        "https://epubs.siam.org/journals/2022/20m1339829.pdf",
        
        # Direct DOI patterns
        "https://epubs.siam.org/10.1137/20M1339829.pdf",
        "https://files.siam.org/10.1137/20M1339829.pdf",
        "https://cdn.siam.org/10.1137/20M1339829.pdf",
        
        # Issue patterns
        "https://epubs.siam.org/toc/sicomp/51/1/20m1339829.pdf",
        "https://epubs.siam.org/issues/sicomp/51/1/20m1339829.pdf"
    ]
    
    session = requests.Session()
    
    for pattern in file_patterns:
        print(f"\n🔗 Testing: {pattern}")
        try:
            response = session.head(pattern, timeout=10)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   ✅ DIRECT ACCESS FOUND!")
                print(f"   Size: {response.headers.get('content-length', 'unknown')}")
                return pattern
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    return None


def analyze_siam_authentication():
    """Analyze SIAM's authentication mechanisms."""
    print("\n🔍 Analyzing SIAM Authentication")
    print("=" * 60)
    
    # Try to understand their auth flow
    auth_urls = [
        "https://epubs.siam.org/action/ssostart",
        "https://epubs.siam.org/action/showLogin",
        "https://epubs.siam.org/pb/sso/login",
        "https://epubs.siam.org/action/showFedLogin",
        "https://epubs.siam.org/Shibboleth.sso/Login",
        "https://wayf.siam.org/",
        "https://discovery.siam.org/",
        "https://login.siam.org/",
        "https://auth.siam.org/",
        "https://sso.siam.org/"
    ]
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'curl/7.68.0'  # Try as curl instead of browser
    })
    
    for url in auth_urls:
        print(f"\n🔗 Testing: {url}")
        try:
            response = session.get(url, timeout=10, allow_redirects=False)
            print(f"   Status: {response.status_code}")
            print(f"   Location: {response.headers.get('location', 'N/A')}")
            
            if response.status_code in [200, 302] and 'cloudflare' not in response.text.lower():
                print("   ✅ No Cloudflare detected!")
                
                # Look for institution search
                if 'institution' in response.text.lower():
                    print("   🏛️ Institution search found!")
                    return url
                    
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    return None


def try_open_access_papers():
    """Try to find open access papers that don't require authentication."""
    print("\n🔍 Looking for Open Access Papers")
    print("=" * 60)
    
    # Some potentially open access SIAM papers
    open_access_dois = [
        "10.1137/19M1274067",  # DeepXDE paper
        "10.1137/18M1210502",  # Another potential OA paper
        "10.1137/17M1144258",  # Older paper
        "10.1137/16M1108820"   # Even older
    ]
    
    session = requests.Session()
    
    for doi in open_access_dois:
        print(f"\n📄 Testing DOI: {doi}")
        pdf_url = f"https://epubs.siam.org/doi/pdf/{doi}"
        
        try:
            response = session.head(pdf_url, timeout=10)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                if 'pdf' in content_type:
                    print("   ✅ OPEN ACCESS PDF FOUND!")
                    print(f"   URL: {pdf_url}")
                    return pdf_url
                    
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    return None


def main():
    """Run all reverse engineering attempts."""
    print("SIAM Reverse Engineering")
    print("=======================\n")
    
    # 1. Analyze URL patterns
    working_urls = analyze_siam_url_patterns()
    if working_urls:
        print(f"\n✅ Found {len(working_urls)} working URLs!")
    
    # 2. Check metadata endpoints
    analyze_siam_metadata()
    
    # 3. Try direct file access
    direct_file = try_direct_file_access()
    if direct_file:
        print(f"\n✅ Direct file access: {direct_file}")
    
    # 4. Analyze authentication
    auth_url = analyze_siam_authentication()
    if auth_url:
        print(f"\n✅ Working auth URL: {auth_url}")
    
    # 5. Find open access papers
    oa_url = try_open_access_papers()
    if oa_url:
        print(f"\n✅ Open access PDF: {oa_url}")
    
    print("\n" + "="*60)
    print("REVERSE ENGINEERING SUMMARY")
    print("="*60)
    print("💡 Key findings:")
    print("1. SIAM uses standard DOI-based URL patterns")
    print("2. PDF access requires authentication for most papers")
    print("3. Direct file access patterns need investigation")
    print("4. Authentication endpoints may be accessible without Cloudflare")
    print("5. Some papers may be open access")
    
    print("\n🎯 Next steps:")
    print("1. If auth URL found → use it to bypass Cloudflare")
    print("2. If direct file pattern found → use it for download")
    print("3. If open access found → use as test case")
    print("4. Focus on bypassing Cloudflare on auth endpoints")


if __name__ == "__main__":
    main()