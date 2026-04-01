#!/usr/bin/env python3
"""
Test Real Paper URLs for Institutional Access
Testing actual paper pages instead of home pages to find institutional access
"""

import asyncio
import json

from playwright.async_api import async_playwright

# Real paper URLs for testing institutional access
REAL_PAPER_URLS = {
    "ieee": [
        "https://ieeexplore.ieee.org/document/9999743",  # Recent paper
        "https://ieeexplore.ieee.org/document/10000001", 
        "https://ieeexplore.ieee.org/abstract/document/9999743"
    ],
    
    "elsevier": [
        "https://www.sciencedirect.com/science/article/pii/S0167739X23004113",
        "https://www.sciencedirect.com/science/article/pii/S0167739X23004112"  
    ],
    
    "wiley": [
        "https://onlinelibrary.wiley.com/doi/10.1002/anie.202318946",
        "https://onlinelibrary.wiley.com/doi/10.1002/adma.202310001"
    ],
    
    "acm": [
        "https://dl.acm.org/doi/10.1145/3613904.3642596",
        "https://dl.acm.org/doi/10.1145/3613904.3642595"
    ],
    
    "nature": [
        "https://www.nature.com/articles/s41586-024-07871-w",
        "https://www.nature.com/articles/s41586-024-07870-x"
    ],
    
    "taylor_francis": [
        "https://www.tandfonline.com/doi/full/10.1080/10942912.2024.2308421",
        "https://www.tandfonline.com/doi/full/10.1080/10942912.2024.2308422"
    ],
    
    "aps": [
        "https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.132.071801",
        "https://journals.aps.org/prd/abstract/10.1103/PhysRevD.109.012345"
    ],
    
    "iop": [
        "https://iopscience.iop.org/article/10.1088/1361-6633/ad0c60",
        "https://iopscience.iop.org/article/10.1088/1361-6633/ad0c61"
    ]
}

# Institutional access patterns to look for
INSTITUTIONAL_PATTERNS = [
    # Text patterns
    'text:Institutional',
    'text:Sign in via',
    'text:Access through', 
    'text:Shibboleth',
    'text:University access',
    'text:Institutional login',
    'text:Organization access',
    
    # Link patterns
    '[href*="institutional"]',
    '[href*="shibboleth"]', 
    '[href*="wayf"]',
    '[href*="login"]',
    '[href*="signin"]',
    '[href*="auth"]',
    
    # Button/link text patterns
    'a:has-text("Access through")',
    'button:has-text("Institutional")',
    'a:has-text("Sign in")',
    'a:has-text("Login")',
    
    # Class patterns 
    '.institutional-access',
    '.shibboleth-login',
    '.university-access'
]


async def test_paper_institutional_access():
    """Test real paper URLs for institutional access"""
    
    print("🔍 TESTING REAL PAPER URLS FOR INSTITUTIONAL ACCESS")
    print("=" * 70)
    
    results = {}
    
    async with async_playwright() as p:
        # Use realistic browser settings to avoid bot detection
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        
        # Add stealth
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            delete window.chrome;
        """)
        
        for publisher, urls in REAL_PAPER_URLS.items():
            print(f"\n📚 Testing {publisher.upper()}...")
            
            publisher_results = []
            
            for i, url in enumerate(urls, 1):
                print(f"   [{i}] {url}")
                
                try:
                    # Navigate to paper
                    response = await page.goto(url, wait_until='domcontentloaded', timeout=15000)
                    await page.wait_for_timeout(3000)  # Let page fully load
                    
                    if response.status == 200:
                        # Look for institutional access patterns
                        institutional_elements = []
                        
                        for pattern in INSTITUTIONAL_PATTERNS:
                            try:
                                elements = await page.locator(pattern).all()
                                for elem in elements:
                                    try:
                                        text = await elem.text_content()
                                        href = await elem.get_attribute('href')
                                        is_visible = await elem.is_visible()
                                        
                                        if (text and text.strip()) or href:
                                            institutional_elements.append({
                                                'pattern': pattern,
                                                'text': text.strip() if text else '',
                                                'href': href,
                                                'visible': is_visible
                                            })
                                    except:
                                        pass
                            except:
                                pass
                        
                        # Check for paywall/access messages
                        paywall_patterns = [
                            'text:Subscribe',
                            'text:Purchase', 
                            'text:Buy article',
                            'text:Access denied',
                            'text:Log in to access',
                            'text:Subscription required'
                        ]
                        
                        paywall_found = False
                        for pattern in paywall_patterns:
                            try:
                                elements = await page.locator(pattern).all()
                                if elements and len(elements) > 0:
                                    paywall_found = True
                                    break
                            except:
                                pass
                        
                        # Check if PDF is directly accessible  
                        pdf_patterns = [
                            'a[href*=".pdf"]',
                            'a:has-text("Download PDF")',
                            'button:has-text("PDF")',
                            '.pdf-download'
                        ]
                        
                        pdf_links = []
                        for pattern in pdf_patterns:
                            try:
                                elements = await page.locator(pattern).all()
                                for elem in elements:
                                    try:
                                        href = await elem.get_attribute('href')
                                        text = await elem.text_content()
                                        is_visible = await elem.is_visible()
                                        
                                        if href and '.pdf' in href:
                                            pdf_links.append({
                                                'href': href,
                                                'text': text.strip() if text else '',
                                                'visible': is_visible
                                            })
                                    except:
                                        pass
                            except:
                                pass
                        
                        result = {
                            'url': url,
                            'accessible': True,
                            'status_code': response.status,
                            'institutional_elements': institutional_elements,
                            'has_institutional': len(institutional_elements) > 0,
                            'paywall_found': paywall_found,
                            'pdf_links': pdf_links,
                            'has_direct_pdf': len(pdf_links) > 0
                        }
                        
                        # Determine access type
                        if len(pdf_links) > 0 and not paywall_found:
                            access_type = "✅ OPEN ACCESS"
                        elif len(institutional_elements) > 0:
                            access_type = "🏛️ INSTITUTIONAL"
                        elif paywall_found:
                            access_type = "💰 PAYWALL"
                        else:
                            access_type = "❓ UNCLEAR"
                        
                        print(f"      {access_type} | Institutional: {len(institutional_elements)} | PDF: {len(pdf_links)}")
                        
                        if institutional_elements:
                            for elem in institutional_elements[:2]:  # Show first 2
                                print(f"         • {elem['text'][:40]}... -> {elem['href'][:40] if elem['href'] else 'no href'}...")
                        
                    else:
                        result = {
                            'url': url,
                            'accessible': False,
                            'status_code': response.status,
                            'error': f"HTTP {response.status}"
                        }
                        print(f"      ❌ HTTP {response.status}")
                    
                    publisher_results.append(result)
                    
                except Exception as e:
                    result = {
                        'url': url,
                        'accessible': False,
                        'error': str(e)[:100]
                    }
                    print(f"      ❌ Error: {str(e)[:40]}...")
                    publisher_results.append(result)
                
                # Delay between requests
                await page.wait_for_timeout(2000)
            
            results[publisher] = publisher_results
        
        await browser.close()
    
    # Generate summary
    print(f"\n{'=' * 70}")
    print("📊 INSTITUTIONAL ACCESS SUMMARY")
    print("=" * 70)
    
    institutional_publishers = []
    open_access_publishers = []
    paywall_publishers = []
    
    for publisher, publisher_results in results.items():
        accessible_papers = [r for r in publisher_results if r.get('accessible', False)]
        institutional_papers = [r for r in accessible_papers if r.get('has_institutional', False)]
        open_papers = [r for r in accessible_papers if r.get('has_direct_pdf', False)]
        paywall_papers = [r for r in accessible_papers if r.get('paywall_found', False)]
        
        print(f"\n🏛️ {publisher.upper()}:")
        print(f"   Accessible: {len(accessible_papers)}/{len(publisher_results)}")
        
        if institutional_papers:
            institutional_publishers.append(publisher)
            print(f"   ✅ INSTITUTIONAL ACCESS: {len(institutional_papers)} papers")
            
            # Show best institutional access example
            best_institutional = max(institutional_papers, key=lambda x: len(x.get('institutional_elements', [])))
            print(f"   🎯 Best example: {best_institutional['url']}")
            for elem in best_institutional.get('institutional_elements', [])[:2]:
                if elem.get('text'):
                    print(f"      • \"{elem['text'][:50]}...\"")
        
        if open_papers:
            open_access_publishers.append(publisher)
            print(f"   📖 OPEN ACCESS: {len(open_papers)} papers")
        
        if paywall_papers:
            paywall_publishers.append(publisher)  
            print(f"   💰 PAYWALL: {len(paywall_papers)} papers")
        
        if not accessible_papers:
            print(f"   ❌ NO ACCESS: All papers inaccessible")
    
    # Save results
    with open('institutional_access_test.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n🎯 IMPLEMENTATION PRIORITY:")
    print(f"   🏛️ INSTITUTIONAL ACCESS ({len(institutional_publishers)}): {', '.join(institutional_publishers)}")
    print(f"   📖 OPEN ACCESS ({len(open_access_publishers)}): {', '.join(open_access_publishers)}")
    print(f"   💰 PAYWALL ONLY ({len(paywall_publishers)}): {', '.join(paywall_publishers)}")
    
    return institutional_publishers


async def main():
    institutional_publishers = await test_paper_institutional_access()
    
    print(f"\n🚀 RECOMMENDED NEXT STEPS:")
    print(f"   1. Focus on {len(institutional_publishers)} publishers with institutional access")
    print(f"   2. Build unified downloader framework")
    print(f"   3. Test ETH Shibboleth authentication for each")


if __name__ == "__main__":
    asyncio.run(main())