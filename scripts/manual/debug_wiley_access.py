#!/usr/bin/env python3
"""
DEBUG WILEY ACCESS
==================

Debug script to see exactly what's happening on Wiley pages
and why PDFs aren't downloading despite VPN connection.
"""

import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

# Add the src directory to path
sys.path.insert(0, str(Path(__file__).parent))

API_KEY = "dkg5eEYuOjlv69V1gw1PuxwK0njBM7N457RWItGZHpihEqCc"

async def debug_wiley_page(doi: str):
    """Debug what's actually happening on Wiley pages"""
    
    print(f"🔍 DEBUGGING WILEY ACCESS FOR: {doi}")
    print("=" * 60)
    
    # Load credentials
    try:
        from src.secure_credential_manager import get_credential_manager
        cm = get_credential_manager()
        username, password = cm.get_eth_credentials()
        print(f"✅ Credentials loaded: {username[:3]}***")
    except:
        print("❌ Could not load credentials")
        username, password = None, None
    
    async with async_playwright() as p:
        # Launch browser in visible mode for debugging
        browser = await p.chromium.launch(
            headless=False,  # Show browser
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        
        page = await context.new_page()
        
        # Add API key
        await page.set_extra_http_headers({
            'X-API-Key': API_KEY,
            'Authorization': f'Bearer {API_KEY}'
        })
        
        try:
            url = f"https://onlinelibrary.wiley.com/doi/pdf/{doi}"
            print(f"\n🔄 Navigating to: {url}")
            
            response = await page.goto(url, wait_until='networkidle', timeout=30000)
            
            print(f"📍 Final URL: {page.url}")
            print(f"📊 Response Status: {response.status if response else 'No response'}")
            
            if response:
                content_type = response.headers.get('content-type', '')
                print(f"📋 Content-Type: {content_type}")
            
            # Wait a moment
            await page.wait_for_timeout(3000)
            
            # Get page title
            title = await page.title()
            print(f"📄 Page Title: {title}")
            
            # Check page content
            page_text = await page.inner_text('body')
            print(f"📝 Page Text (first 200 chars): {page_text[:200]}...")
            
            # Look for specific indicators
            indicators = {
                'PDF content': 'pdf' in content_type.lower() if response else False,
                'Login required': any(term in page_text.lower() for term in ['login', 'sign in', 'authenticate']),
                'Institutional access': any(term in page_text.lower() for term in ['institutional', 'shibboleth', 'switch aai']),
                'Access denied': any(term in page_text.lower() for term in ['access denied', 'forbidden', '403', 'unauthorized']),
                'Subscription required': any(term in page_text.lower() for term in ['subscription', 'subscribe', 'purchase']),
                'ETH mentioned': 'eth' in page_text.lower(),
                'Paywall': any(term in page_text.lower() for term in ['paywall', 'pay per view', 'buy article'])
            }
            
            print(f"\n🔍 PAGE ANALYSIS:")
            for indicator, present in indicators.items():
                status = "✅ YES" if present else "❌ NO"
                print(f"  {indicator}: {status}")
            
            # Look for clickable elements
            print(f"\n🔗 CLICKABLE ELEMENTS:")
            
            # PDF download links
            pdf_links = await page.query_selector_all('a[href*="pdf"], [href*="download"]')
            if pdf_links:
                print(f"  📄 Found {len(pdf_links)} potential PDF links")
                for i, link in enumerate(pdf_links[:3]):
                    href = await link.get_attribute('href')
                    text = await link.inner_text()
                    print(f"    {i+1}. {text[:30]} -> {href[:50] if href else 'No href'}")
            else:
                print(f"  📄 No PDF links found")
            
            # Login buttons
            login_buttons = await page.query_selector_all('a:has-text("Login"), button:has-text("Login"), a:has-text("Sign in")')
            if login_buttons:
                print(f"  🔐 Found {len(login_buttons)} login buttons")
                for i, button in enumerate(login_buttons[:3]):
                    text = await button.inner_text()
                    href = await button.get_attribute('href')
                    print(f"    {i+1}. {text} -> {href[:50] if href else 'Button'}")
            else:
                print(f"  🔐 No login buttons found")
            
            # Institutional access links
            institutional_links = await page.query_selector_all('a:has-text("Institutional"), a:has-text("Access through")')
            if institutional_links:
                print(f"  🏛️ Found {len(institutional_links)} institutional access links")
                for i, link in enumerate(institutional_links[:3]):
                    text = await link.inner_text()
                    href = await link.get_attribute('href')
                    print(f"    {i+1}. {text} -> {href[:50] if href else 'No href'}")
            else:
                print(f"  🏛️ No institutional access links found")
            
            # Screenshot for reference
            screenshot_path = Path(f"wiley_debug_{doi.replace('/', '_').replace('.', '_')}.png")
            await page.screenshot(path=screenshot_path)
            print(f"\n📸 Screenshot saved: {screenshot_path}")
            
            # Wait for manual inspection
            print(f"\n⏳ Browser will stay open for 30 seconds for manual inspection...")
            print(f"   Check the browser window to see what's actually displayed")
            await page.wait_for_timeout(30000)
            
            await browser.close()
            
        except Exception as e:
            print(f"❌ Error during debugging: {e}")
            await browser.close()

async def main():
    """Debug multiple DOIs"""
    
    test_dois = [
        "10.1002/anie.202004934",
        "10.1111/1467-9523.00201", 
        "10.1002/adma.202001924"
    ]
    
    print("🎯 WILEY ACCESS DEBUG SESSION")
    print("=" * 80)
    print("This will open browsers to debug what's happening on Wiley pages")
    print("=" * 80)
    
    for i, doi in enumerate(test_dois, 1):
        print(f"\n{'='*20} DEBUG {i}/{len(test_dois)} {'='*20}")
        await debug_wiley_page(doi)
        
        if i < len(test_dois):
            print(f"\n⏳ 5 second pause before next DOI...")
            await asyncio.sleep(5)
    
    print(f"\n🎯 DEBUG SESSION COMPLETE!")
    print(f"Check the screenshots and browser windows to understand the access patterns.")

if __name__ == "__main__":
    asyncio.run(main())