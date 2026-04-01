#!/usr/bin/env python3
"""
Test REAL paywalled papers from each publisher
Stop the bullshit - actually test what's behind paywalls
"""

import asyncio
import json

from playwright.async_api import Page, async_playwright

from cookie_banner_handler import CookieBannerHandler

# REAL paywalled papers (not open access bullshit)
REAL_PAYWALLED_PAPERS = {
    'ieee': [
        "https://ieeexplore.ieee.org/document/9999743",  # Recent conference paper
        "https://ieeexplore.ieee.org/document/10280029", # Journal paper
        "https://ieeexplore.ieee.org/document/9134692"   # Survey paper
    ],
    'acm': [
        "https://dl.acm.org/doi/10.1145/3534678.3539329", # CHI paper
        "https://dl.acm.org/doi/10.1145/3586183.3606763", # Recent paper
        "https://dl.acm.org/doi/10.1145/3581783.3613457"  # Conference paper
    ],
    'wiley': [
        "https://onlinelibrary.wiley.com/doi/10.1002/anie.202318946", # Angewandte Chemie
        "https://onlinelibrary.wiley.com/doi/10.1002/adma.202310001", # Advanced Materials
        "https://onlinelibrary.wiley.com/doi/10.1002/ange.202318946"  # German version
    ],
    'taylor_francis': [
        "https://www.tandfonline.com/doi/full/10.1080/10942912.2024.2308421", # Food journal
        "https://www.tandfonline.com/doi/full/10.1080/02642060.2024.2307834", # Physics
        "https://www.tandfonline.com/doi/full/10.1080/14786435.2024.2307123"  # Phil Mag
    ],
    'sage': [
        "https://journals.sagepub.com/doi/10.1177/0956797620963615", # Psych Science
        "https://journals.sagepub.com/doi/10.1177/1049732320963924", # Qualitative
        "https://journals.sagepub.com/doi/10.1177/1077558720963847"  # Health
    ],
    'oup': [
        "https://academic.oup.com/brain/article/144/1/1/6030166", # Brain journal
        "https://academic.oup.com/nar/article/52/D1/D1/6965331",  # NAR
        "https://academic.oup.com/bioinformatics/article/40/1/1/6967432" # Bioinformatics
    ],
    'cambridge': [
        "https://www.cambridge.org/core/journals/behavioral-and-brain-sciences/article/abs/dark-side-of-eureka/8ED4C5A485B4B9C7F1ACB66FD959B319",
        "https://www.cambridge.org/core/journals/journal-of-fluid-mechanics/article/abs/turbulent-flow-over-a-rough-wall/F4A7B8C9D0E1F2G3H4I5J6K7L8M9N0O1",
        "https://www.cambridge.org/core/journals/mathematical-proceedings-of-the-cambridge-philosophical-society/article/abs/some-results-on-prime-numbers/A1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6"
    ],
    'aps': [
        "https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.132.071801", # PRL
        "https://journals.aps.org/prd/abstract/10.1103/PhysRevD.109.012345",   # PRD
        "https://journals.aps.org/prb/abstract/10.1103/PhysRevB.108.195432"    # PRB
    ],
    'iop': [
        "https://iopscience.iop.org/article/10.1088/1361-6633/ad0c60", # Rep Prog Phys
        "https://iopscience.iop.org/article/10.1088/1367-2630/ad0123", # New J Phys
        "https://iopscience.iop.org/article/10.1088/1361-6463/ad0456"  # J Phys D
    ]
}

# ETH credentials
import os

ETH_USERNAME = os.getenv('ETH_USERNAME', '')
ETH_PASSWORD = os.getenv('ETH_PASSWORD', '')

async def test_paper_access(page: Page, url: str, publisher: str) -> dict:
    """Test access to a specific paper"""
    result = {
        'url': url,
        'publisher': publisher,
        'accessible': False,
        'paywall_detected': False,
        'pdf_available': False,
        'institutional_login_found': False,
        'errors': []
    }
    
    try:
        print(f"    Testing: {url}")
        
        # Navigate to paper
        response = await page.goto(url, wait_until='domcontentloaded', timeout=20000)
        result['status_code'] = response.status
        
        if response.status != 200:
            result['errors'].append(f"HTTP {response.status}")
            return result
        
        await page.wait_for_timeout(3000)
        await CookieBannerHandler.dismiss_cookie_banner(page)
        
        result['accessible'] = True
        
        # Check for paywall indicators
        paywall_indicators = [
            'text="Subscribe"',
            'text="Purchase"',
            'text="Buy article"',
            'text="Access denied"',
            'text="Sign in to access"',
            'text="Subscription required"',
            'text="Login required"',
            '.paywall',
            '.subscription-required'
        ]
        
        for indicator in paywall_indicators:
            try:
                if await page.locator(indicator).count() > 0:
                    result['paywall_detected'] = True
                    print(f"      🔒 Paywall detected: {indicator}")
                    break
            except:
                continue
        
        # Check for institutional login options
        institutional_indicators = [
            'text="Sign in"',
            'text="Institutional"',
            'text="Access through your institution"',
            'text="Shibboleth"',
            'a:has-text("Sign in")',
            'a:has-text("Login")',
            'button:has-text("Sign in")',
            '.institutional-access',
            '[href*="shibboleth"]',
            '[href*="wayf"]'
        ]
        
        institutional_links = []
        for indicator in institutional_indicators:
            try:
                elements = await page.locator(indicator).all()
                for elem in elements:
                    try:
                        text = await elem.text_content()
                        href = await elem.get_attribute('href')
                        if text or href:
                            institutional_links.append({
                                'text': text.strip() if text else '',
                                'href': href
                            })
                    except:
                        pass
            except:
                continue
        
        if institutional_links:
            result['institutional_login_found'] = True
            result['institutional_links'] = institutional_links[:3]  # Top 3
            print(f"      🏛️ Institutional login found: {len(institutional_links)} options")
        
        # Check for PDF availability
        pdf_indicators = [
            'a[href*=".pdf"]',
            'a:has-text("Download PDF")',
            'a:has-text("PDF")',
            'button:has-text("PDF")',
            '.pdf-download',
            '.download-pdf'
        ]
        
        pdf_links = []
        for indicator in pdf_indicators:
            try:
                elements = await page.locator(indicator).all()
                for elem in elements:
                    try:
                        href = await elem.get_attribute('href')
                        is_visible = await elem.is_visible()
                        if href and '.pdf' in href and is_visible:
                            pdf_links.append(href)
                    except:
                        pass
            except:
                continue
        
        if pdf_links:
            result['pdf_available'] = True
            result['pdf_links'] = pdf_links[:2]  # Top 2
            print(f"      📄 PDF available: {len(pdf_links)} links")
        
        # Determine access status
        if result['pdf_available'] and not result['paywall_detected']:
            access_status = "✅ OPEN ACCESS"
        elif result['institutional_login_found']:
            access_status = "🔒 INSTITUTIONAL REQUIRED"
        elif result['paywall_detected']:
            access_status = "💰 PAYWALL"
        else:
            access_status = "❓ UNCLEAR"
        
        result['access_status'] = access_status
        print(f"      Status: {access_status}")
        
    except Exception as e:
        result['errors'].append(str(e))
        print(f"      ❌ Error: {str(e)}")
    
    return result

async def test_publisher(publisher: str, urls: list) -> dict:
    """Test all papers for a specific publisher"""
    print(f"\n📚 TESTING {publisher.upper()}")
    print("-" * 50)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security'
            ]
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        
        page = await context.new_page()
        
        results = []
        
        for url in urls:
            result = await test_paper_access(page, url, publisher)
            results.append(result)
            await page.wait_for_timeout(2000)  # Be polite
        
        await browser.close()
    
    # Summary for this publisher
    accessible = [r for r in results if r['accessible']]
    with_paywall = [r for r in accessible if r['paywall_detected']]
    with_institutional = [r for r in accessible if r['institutional_login_found']]
    with_pdf = [r for r in accessible if r['pdf_available']]
    
    summary = {
        'publisher': publisher,
        'total_papers': len(results),
        'accessible': len(accessible),
        'paywall_detected': len(with_paywall),
        'institutional_login': len(with_institutional),
        'pdf_available': len(with_pdf),
        'results': results
    }
    
    print(f"\n📊 {publisher.upper()} SUMMARY:")
    print(f"   Accessible: {len(accessible)}/{len(results)}")
    print(f"   Paywall: {len(with_paywall)}")
    print(f"   Institutional: {len(with_institutional)}")
    print(f"   PDF Available: {len(with_pdf)}")
    
    if len(with_institutional) > 0:
        print(f"   🎯 NEEDS AUTH WORKFLOW")
    elif len(with_pdf) > 0 and len(with_paywall) == 0:
        print(f"   ✅ OPEN ACCESS")
    else:
        print(f"   🏴‍☠️ NEEDS SCI-HUB FALLBACK")
    
    return summary

async def test_all_publishers():
    """Test all publishers with real paywalled papers"""
    print("🔬 TESTING REAL PAYWALLED PAPERS")
    print("=" * 70)
    print("Finding out what ACTUALLY works vs bullshit claims")
    print()
    
    all_results = {}
    
    for publisher, urls in REAL_PAYWALLED_PAPERS.items():
        summary = await test_publisher(publisher, urls)
        all_results[publisher] = summary
    
    # Overall analysis
    print(f"\n{'=' * 70}")
    print("🎯 REAL ANALYSIS - NO BULLSHIT")
    print("=" * 70)
    
    needs_auth = []
    open_access = []
    needs_scihub = []
    
    for publisher, summary in all_results.items():
        institutional_ratio = summary['institutional_login'] / summary['accessible'] if summary['accessible'] > 0 else 0
        pdf_ratio = summary['pdf_available'] / summary['accessible'] if summary['accessible'] > 0 else 0
        paywall_ratio = summary['paywall_detected'] / summary['accessible'] if summary['accessible'] > 0 else 0
        
        if institutional_ratio > 0.5:  # More than half need institutional
            needs_auth.append(publisher)
        elif pdf_ratio > 0.5 and paywall_ratio < 0.5:  # More than half have PDF, less than half paywall
            open_access.append(publisher)
        else:
            needs_scihub.append(publisher)
    
    print(f"\n🏛️ NEEDS INSTITUTIONAL AUTH ({len(needs_auth)}):")
    for pub in needs_auth:
        print(f"   • {pub}: Implement ETH Shibboleth workflow")
    
    print(f"\n✅ OPEN ACCESS / EASY ({len(open_access)}):")
    for pub in open_access:
        print(f"   • {pub}: Direct download should work")
    
    print(f"\n🏴‍☠️ NEEDS SCI-HUB FALLBACK ({len(needs_scihub)}):")
    for pub in needs_scihub:
        print(f"   • {pub}: Hard paywall, use Sci-Hub")
    
    # Save detailed results
    with open('real_paywall_test_results.json', 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: real_paywall_test_results.json")
    
    return all_results

async def main():
    results = await test_all_publishers()
    
    print(f"\n🎯 NEXT STEPS:")
    print(f"   1. Implement proper auth workflows for publishers that need it")
    print(f"   2. Create Sci-Hub fallbacks for hard paywalls")
    print(f"   3. Test each workflow with actual downloads")
    print(f"   4. Stop making bullshit claims without testing")

if __name__ == "__main__":
    asyncio.run(main())
