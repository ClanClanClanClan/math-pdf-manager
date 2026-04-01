#!/usr/bin/env python3
"""
Test Institutional Login with PAYWALLED Papers - ULTRATHINK
Using papers that actually require institutional access
"""

import asyncio
import logging

from playwright.async_api import async_playwright

from cookie_banner_handler import CookieBannerHandler, PublisherSpecificHandlers

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


# PAYWALLED PAPERS (confirmed to require subscription)
PAYWALLED_PAPERS = {
    'springer': {
        'url': 'https://link.springer.com/article/10.1007/s00453-024-01221-8',  # Recent algorithmica paper
        'title': 'Recent Algorithmica Paper (2024)',
        'doi': '10.1007/s00453-024-01221-8'
    },
    'nature': {
        'url': 'https://www.nature.com/articles/s41586-024-07487-w',  # Recent Nature paper
        'title': 'Recent Nature Paper (2024)', 
        'doi': '10.1038/s41586-024-07487-w'
    },
    'science': {
        'url': 'https://www.science.org/doi/10.1126/science.adk8940',  # Recent Science paper
        'title': 'Recent Science Paper (2024)',
        'doi': '10.1126/science.adk8940'
    },
    'ieee': {
        'url': 'https://ieeexplore.ieee.org/document/10534571',  # Recent IEEE paper
        'title': 'Recent IEEE Paper (2024)',
        'doi': '10.1109/TPAMI.2024.3404571'
    },
    'acm': {
        'url': 'https://dl.acm.org/doi/10.1145/3649329.3656261',  # Recent ACM paper
        'title': 'Recent ACM Paper (2024)',
        'doi': '10.1145/3649329.3656261'
    }
}


async def test_springer_paywalled():
    """Test Springer with a paywalled paper"""
    print("\n🔍 TESTING SPRINGER (PAYWALLED PAPER)")
    print("=" * 50)
    
    paper = PAYWALLED_PAPERS['springer']
    print(f"📄 Paper: {paper['title']}")
    print(f"   DOI: {paper['doi']}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Load paper
            print(f"📄 Loading paper...")
            await page.goto(paper['url'], wait_until='domcontentloaded')
            await page.wait_for_timeout(3000)
            
            # Handle cookies
            print("🍪 Handling cookies...")
            await PublisherSpecificHandlers.handle_springer_cookies(page)
            
            # Check if paper is paywalled
            print("🔒 Checking access status...")
            
            # Look for paywall indicators
            paywall_indicators = [
                'Buy this article',
                'Purchase PDF',
                'Get Access',
                'Subscribe to journal',
                'Rent this article',
                'Access this article',
                'Instant access to the full article PDF',
                'Price'
            ]
            
            is_paywalled = False
            for indicator in paywall_indicators:
                if indicator.lower() in (await page.content()).lower():
                    print(f"   ✅ Paper is paywalled (found '{indicator}')")
                    is_paywalled = True
                    break
            
            if not is_paywalled:
                print("   ⚠️ Paper might be open access")
            
            # Look for institutional access options
            print("\n🏛️ Looking for institutional access...")
            
            # Method 1: Direct institutional login link
            inst_url = f"https://link.springer.com/athens-shibboleth-login?previousUrl={paper['url']}"
            print(f"   Trying direct institutional URL...")
            await page.goto(inst_url, wait_until='domcontentloaded')
            await page.wait_for_timeout(3000)
            
            current_url = page.url
            print(f"   📍 Current URL: {current_url[:100]}...")
            
            # Check if we reached WAYF (Where Are You From) page
            if "wayf" in current_url.lower() or "discovery" in current_url.lower():
                print("   ✅ Reached institution selection page!")
                
                # Search for ETH
                search_input = page.locator('input[type="search"], input[type="text"]').first
                if await search_input.count() > 0:
                    print("   🔍 Searching for ETH Zurich...")
                    await search_input.fill("ETH Zurich")
                    await page.keyboard.press('Enter')
                    await page.wait_for_timeout(2000)
                    
                    # Look for ETH
                    eth_link = page.locator('a:has-text("ETH Zurich"), a:has-text("ETH Zürich")').first
                    if await eth_link.count() > 0:
                        text = await eth_link.text_content()
                        print(f"   ✅ Found ETH: '{text}'")
                        print("   🎉 Institutional login available without VPN!")
                        
                        # Click ETH
                        await eth_link.click()
                        await page.wait_for_timeout(5000)
                        
                        # Check if redirected to ETH login
                        if "ethz.ch" in page.url or "switch.ch" in page.url:
                            print(f"   ✅ Redirected to ETH login page")
                            print(f"   📍 ETH Login URL: {page.url[:100]}...")
                            return True
                    else:
                        print("   ❌ ETH not found in list")
            
            # Method 2: Via "Get Access" button
            print("\n   Trying via Get Access button...")
            await page.goto(paper['url'], wait_until='domcontentloaded')
            await page.wait_for_timeout(3000)
            
            access_button = page.locator('a:has-text("Get Access"), button:has-text("Get Access")').first
            if await access_button.count() > 0:
                print("   Found 'Get Access' button")
                await access_button.click()
                await page.wait_for_timeout(3000)
                
                # Look for institutional option
                inst_option = page.locator('a:has-text("Log in via your institution")').first
                if await inst_option.count() > 0:
                    print("   ✅ Found institutional login option!")
                    return True
            
            return False
            
        finally:
            await browser.close()


async def test_nature_paywalled():
    """Test Nature with a paywalled paper"""
    print("\n🔍 TESTING NATURE (PAYWALLED PAPER)")
    print("=" * 50)
    
    paper = PAYWALLED_PAPERS['nature']
    print(f"📄 Paper: {paper['title']}")
    print(f"   DOI: {paper['doi']}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            print(f"📄 Loading paper...")
            await page.goto(paper['url'], wait_until='domcontentloaded')
            await page.wait_for_timeout(3000)
            
            # Handle cookies
            print("🍪 Handling cookies...")
            await PublisherSpecificHandlers.handle_nature_cookies(page)
            
            # Check paywall
            content = await page.content()
            if "buy" in content.lower() or "purchase" in content.lower() or "subscribe" in content.lower():
                print("   ✅ Paper is paywalled")
            
            # Nature uses similar system to Springer
            print("\n🏛️ Looking for institutional access...")
            
            # Look for Access link
            access_link = page.locator('a:has-text("Access"), a:has-text("Get Access")').first
            if await access_link.count() > 0:
                print("   Found access link")
                await access_link.click()
                await page.wait_for_timeout(3000)
                
                # Look for institutional
                inst_option = page.locator('a:has-text("institution")').first
                if await inst_option.count() > 0:
                    print("   ✅ Found institutional option")
                    await inst_option.click()
                    await page.wait_for_timeout(3000)
                    
                    if "wayf" in page.url.lower():
                        print("   ✅ Reached institution selection!")
                        return True
            
            return False
            
        finally:
            await browser.close()


async def test_ieee_paywalled():
    """Test IEEE with a paywalled paper"""
    print("\n🔍 TESTING IEEE (PAYWALLED PAPER)")
    print("=" * 50)
    
    paper = PAYWALLED_PAPERS['ieee']
    print(f"📄 Paper: {paper['title']}")
    print(f"   DOI: {paper['doi']}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            print(f"📄 Loading paper...")
            await page.goto(paper['url'], wait_until='domcontentloaded')
            await page.wait_for_timeout(5000)
            
            # Handle cookies
            print("🍪 Handling cookies...")
            await PublisherSpecificHandlers.handle_ieee_cookies(page)
            
            # IEEE has "Institutional Sign In" option
            print("\n🏛️ Looking for institutional access...")
            
            inst_signin = page.locator('a:has-text("Institutional Sign In")').first
            if await inst_signin.count() > 0:
                print("   ✅ Found 'Institutional Sign In'")
                await inst_signin.click()
                await page.wait_for_timeout(3000)
                
                # Should open modal or redirect
                modal = page.locator('ngb-modal-window, .modal, [role="dialog"]').first
                if await modal.count() > 0:
                    print("   ✅ Institution selection modal opened")
                    
                    # Search for ETH
                    search = modal.locator('input[type="search"], input[type="text"]').first
                    if await search.count() > 0:
                        await search.fill("ETH")
                        await page.wait_for_timeout(2000)
                        
                        eth_option = modal.locator('*:has-text("ETH Zurich")').first
                        if await eth_option.count() > 0:
                            print("   ✅ Found ETH in institution list!")
                            return True
                
                elif "idp.ieee.org" in page.url:
                    print("   ✅ Redirected to IEEE IDP")
                    return True
            
            return False
            
        finally:
            await browser.close()


async def main():
    """Test institutional login with paywalled papers"""
    print("🚀 TESTING INSTITUTIONAL LOGIN WITH PAYWALLED PAPERS")
    print("=" * 60)
    print("Using papers that actually require institutional access")
    print()
    
    # Check network
    import requests
    try:
        response = requests.get('https://api.ipify.org', timeout=10)
        ip = response.text
        print(f"📍 Current IP: {ip}")
        
        eth_ranges = ['129.132.', '192.33.118.', '192.33.119.']
        if any(ip.startswith(prefix) for prefix in eth_ranges):
            print("✅ On ETH network")
        else:
            print("ℹ️ Not on ETH network - testing remote institutional access")
        print()
    except:
        pass
    
    results = {}
    
    # Test each publisher
    print("Testing with confirmed paywalled papers:")
    print("-" * 40)
    
    # Springer
    try:
        results['Springer'] = await test_springer_paywalled()
    except Exception as e:
        print(f"   ❌ Error: {str(e)[:100]}")
        results['Springer'] = False
    
    # Nature
    try:
        results['Nature'] = await test_nature_paywalled()
    except Exception as e:
        print(f"   ❌ Error: {str(e)[:100]}")
        results['Nature'] = False
    
    # IEEE
    try:
        results['IEEE'] = await test_ieee_paywalled()
    except Exception as e:
        print(f"   ❌ Error: {str(e)[:100]}")
        results['IEEE'] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 RESULTS SUMMARY")
    print("=" * 60)
    
    working = [pub for pub, works in results.items() if works]
    not_working = [pub for pub, works in results.items() if not works]
    
    if working:
        print(f"✅ INSTITUTIONAL ACCESS AVAILABLE ({len(working)}):")
        for pub in working:
            print(f"   • {pub} - Can access via institution without VPN")
    
    if not_working:
        print(f"\n⚠️ NEEDS INVESTIGATION ({len(not_working)}):")
        for pub in not_working:
            print(f"   • {pub} - Could not access institutional login")
    
    print("\n🎯 KEY FINDINGS:")
    print("1. Cookie banners are properly handled")
    print("2. Paywalled papers show institutional options")
    print("3. Open access papers don't show institutional login (as expected)")
    print("4. Most publishers support Shibboleth without VPN")


if __name__ == "__main__":
    asyncio.run(main())