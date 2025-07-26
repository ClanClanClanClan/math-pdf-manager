#!/usr/bin/env python3
"""
Debug SIAM Page Structure
=========================

Check what's on the SIAM page to understand the authentication flow.
"""

import asyncio
from playwright.async_api import async_playwright

async def debug_siam_page():
    """Debug SIAM page to understand authentication options."""
    
    test_doi = "10.1137/S0097539795293172"
    siam_url = f"https://epubs.siam.org/doi/{test_doi}"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Visual mode for debugging
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = await context.new_page()
        
        try:
            print(f"🔍 Navigating to: {siam_url}")
            await page.goto(siam_url, wait_until='domcontentloaded')
            await page.wait_for_timeout(5000)
            
            print(f"📍 Current URL: {page.url}")
            
            # Check page title
            title = await page.title()
            print(f"📄 Page title: {title}")
            
            # Look for any login/access links
            print("\n🔗 Looking for authentication links...")
            all_links = await page.query_selector_all('a')
            auth_links = []
            
            for link in all_links:
                text = await link.text_content()
                href = await link.get_attribute('href')
                if text and any(keyword in text.lower() for keyword in ['sign', 'login', 'access', 'institution', 'athens']):
                    auth_links.append((text.strip(), href))
            
            if auth_links:
                print("Found authentication links:")
                for text, href in auth_links:
                    print(f"  - '{text}' -> {href}")
            else:
                print("❌ No authentication links found")
            
            # Look for any buttons
            print("\n🔘 Looking for authentication buttons...")
            all_buttons = await page.query_selector_all('button')
            auth_buttons = []
            
            for button in all_buttons:
                text = await button.text_content()
                if text and any(keyword in text.lower() for keyword in ['sign', 'login', 'access', 'institution', 'athens']):
                    auth_buttons.append(text.strip())
            
            if auth_buttons:
                print("Found authentication buttons:")
                for text in auth_buttons:
                    print(f"  - '{text}'")
            else:
                print("❌ No authentication buttons found")
            
            # Check if there are any PDF access restrictions
            print("\n📋 Checking page content for access restrictions...")
            page_content = await page.content()
            
            if 'pdf' in page_content.lower():
                print("✅ Page mentions PDF content")
                
            if any(keyword in page_content.lower() for keyword in ['restricted', 'subscription', 'institutional', 'access denied']):
                print("⚠️ Page indicates access restrictions")
            
            # Look for existing PDF links (might already have access)
            pdf_links = await page.query_selector_all('a[href*="pdf"]')
            if pdf_links:
                print(f"📄 Found {len(pdf_links)} PDF-related links")
                for link in pdf_links[:3]:  # Show first 3
                    text = await link.text_content()
                    href = await link.get_attribute('href')
                    print(f"  - '{text}' -> {href}")
            
            print(f"\n⏱️ Waiting 30 seconds for manual inspection...")
            await page.wait_for_timeout(30000)
            
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_siam_page())