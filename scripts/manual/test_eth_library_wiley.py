#!/usr/bin/env python3
"""
ETH LIBRARY WILEY ACCESS
========================

Test accessing Wiley through ETH library portal (library.ethz.ch)
This should provide pre-authenticated access without hitting Cloudflare
"""

import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))

async def test_eth_library_wiley():
    """Test Wiley access through ETH library"""
    
    print("📚 ETH LIBRARY WILEY ACCESS TEST")
    print("=" * 80)
    
    # Get ETH credentials
    try:
        from src.secure_credential_manager import get_credential_manager
        cm = get_credential_manager()
        username, password = cm.get_eth_credentials()
        
        if not (username and password):
            print("❌ No ETH credentials available")
            return False
            
        print(f"✅ ETH credentials loaded: {username[:3]}***")
        
    except Exception as e:
        print(f"❌ Failed to load credentials: {e}")
        return False
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--start-maximized']
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = await context.new_page()
        
        # Step 1: Access ETH Library
        print("\n📍 Step 1: Access ETH Library Portal")
        library_url = "https://library.ethz.ch/"
        await page.goto(library_url, wait_until='domcontentloaded')
        await page.wait_for_timeout(3000)
        
        # Step 2: Look for journal/database access
        print("🔍 Step 2: Look for journal database access")
        
        # Common selectors for library database access
        database_selectors = [
            'a:has-text("Databases")',
            'a:has-text("Journals")',
            'a:has-text("E-Journals")',
            'a:has-text("Electronic Resources")',
            'a:has-text("Find Journals")',
            'text="Wiley"',
            'a[href*="journal"]',
            'a[href*="database"]'
        ]
        
        found_access = False
        for selector in database_selectors:
            try:
                element = await page.wait_for_selector(selector, timeout=3000)
                if element:
                    text = await element.inner_text()
                    href = await element.get_attribute('href')
                    print(f"   📎 Found: '{text.strip()}' -> {href}")
                    
                    if 'journal' in text.lower() or 'database' in text.lower():
                        print(f"   🎯 Trying: {text.strip()}")
                        await element.click()
                        await page.wait_for_timeout(3000)
                        found_access = True
                        break
            except:
                continue
        
        if not found_access:
            print("   ❌ No obvious database access found")
            print("   🔍 Let's try searching for Wiley directly")
            
            # Try search functionality
            search_selectors = [
                'input[type="search"]',
                'input[name*="search"]',
                'input[placeholder*="search"]'
            ]
            
            for selector in search_selectors:
                try:
                    search_box = await page.wait_for_selector(selector, timeout=3000)
                    if search_box:
                        print("   📝 Found search box, searching for 'Wiley'")
                        await search_box.fill("Wiley Online Library")
                        await search_box.press("Enter")
                        await page.wait_for_timeout(3000)
                        break
                except:
                    continue
        
        # Step 3: Look for Wiley access
        print("\n🔍 Step 3: Look for Wiley access links")
        
        # Look for Wiley-related links
        wiley_selectors = [
            'a:has-text("Wiley")',
            'a[href*="wiley"]',
            'text="Wiley Online Library"',
            'a:has-text("John Wiley")'
        ]
        
        wiley_link = None
        for selector in wiley_selectors:
            try:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    text = await element.inner_text()
                    href = await element.get_attribute('href')
                    
                    if 'wiley' in text.lower():
                        print(f"   📎 Found Wiley link: '{text.strip()}' -> {href}")
                        wiley_link = element
                        break
                        
                if wiley_link:
                    break
            except:
                continue
        
        if wiley_link:
            print("   🎯 Clicking Wiley access link")
            await wiley_link.click()
            await page.wait_for_timeout(5000)
            
            # Check if we need ETH authentication
            current_url = page.url
            print(f"   📍 Current URL: {current_url}")
            
            if 'ethz' in current_url or 'shibboleth' in current_url:
                print("   🔑 ETH authentication required")
                
                # Handle ETH login
                await handle_eth_authentication(page, username, password)
                
        else:
            print("   ❌ No Wiley access found through library portal")
            print("   💡 Let's try direct ETH journal search")
            
            # Try alternative: ETH E-Journal portal
            eth_journal_url = "https://www.library.ethz.ch/en/Resources/Databases-and-E-Journals"
            print(f"   🔄 Trying: {eth_journal_url}")
            await page.goto(eth_journal_url)
            await page.wait_for_timeout(3000)
        
        # Step 4: Test paper access
        if 'wiley' in page.url.lower():
            print("\n🧪 Step 4: Test paper access")
            
            # Try accessing our test paper
            test_doi = "10.1002/anie.202004934"
            wiley_paper_url = f"https://onlinelibrary.wiley.com/doi/{test_doi}"
            
            print(f"   🎯 Testing access to: {wiley_paper_url}")
            await page.goto(wiley_paper_url)
            await page.wait_for_timeout(5000)
            
            # Check if we have access
            page_content = await page.content()
            
            if any(indicator in page_content.lower() for indicator in [
                'download pdf', 'view pdf', 'full text'
            ]):
                print("   ✅ Paper appears accessible!")
                
                # Try to download PDF
                pdf_dir = Path("eth_library_test")
                pdf_dir.mkdir(exist_ok=True)
                
                pdf_selectors = [
                    'a:has-text("Download PDF")',
                    'a:has-text("PDF")',
                    'a[href*="pdf"]'
                ]
                
                for selector in pdf_selectors:
                    try:
                        pdf_link = await page.wait_for_selector(selector, timeout=3000)
                        if pdf_link and await pdf_link.is_visible():
                            print(f"   🎯 Found PDF link: {selector}")
                            
                            # Try download
                            save_path = pdf_dir / "eth_library_test.pdf"
                            
                            async with page.expect_download() as download_info:
                                await pdf_link.click()
                                download = await download_info.value
                                await download.save_as(save_path)
                                
                                if save_path.exists():
                                    print(f"   ✅ PDF downloaded: {save_path}")
                                    return True
                            break
                    except:
                        continue
                        
            else:
                print("   ❌ Paper not accessible")
        
        print("\n⏸️ Keeping browser open for manual inspection...")
        await page.wait_for_timeout(30000)
        
        await browser.close()
        return False

async def handle_eth_authentication(page, username, password):
    """Handle ETH authentication when prompted"""
    
    print("   🔐 Handling ETH authentication")
    
    # Wait for auth page to load
    await page.wait_for_timeout(3000)
    
    # Look for username field
    username_selectors = [
        'input[name="username"]',
        'input[name="user"]',
        'input[type="text"]',
        'input[id*="username"]'
    ]
    
    for selector in username_selectors:
        try:
            username_field = await page.wait_for_selector(selector, timeout=3000)
            if username_field:
                print("   📝 Found username field")
                await username_field.fill(username)
                break
        except:
            continue
    
    # Look for password field
    password_selectors = [
        'input[name="password"]',
        'input[type="password"]'
    ]
    
    for selector in password_selectors:
        try:
            password_field = await page.wait_for_selector(selector, timeout=3000)
            if password_field:
                print("   📝 Found password field")
                await password_field.fill(password)
                break
        except:
            continue
    
    # Submit
    submit_selectors = [
        'input[type="submit"]',
        'button[type="submit"]',
        'button:has-text("Login")',
        'button:has-text("Sign in")'
    ]
    
    for selector in submit_selectors:
        try:
            submit_btn = await page.wait_for_selector(selector, timeout=3000)
            if submit_btn:
                print("   🚀 Submitting credentials")
                await submit_btn.click()
                await page.wait_for_timeout(5000)
                return True
        except:
            continue
    
    return False

if __name__ == "__main__":
    success = asyncio.run(test_eth_library_wiley())
    print(f"\n{'🎉' if success else '💥'} ETH Library test {'succeeded' if success else 'failed'}")