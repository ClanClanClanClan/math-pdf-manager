#!/usr/bin/env python3
"""
Manual Click Verification Test
Set up browser exactly like our system and let user manually test clicking.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright


async def test_manual_click_verification():
    """Set up browser and let user manually test everything."""
    
    test_doi = "10.1109/JPROC.2018.2820126"
    
    print(f"\n🖱️  MANUAL CLICK VERIFICATION TEST")
    print(f"DOI: {test_doi}")
    print("=" * 70)
    print()
    print("This test will:")
    print("1. Set up the browser exactly like our automated system")
    print("2. Navigate to the IEEE paper") 
    print("3. Let YOU manually perform authentication")
    print("4. Let YOU manually test PDF clicking")
    print("5. We'll observe what happens vs your regular browser")
    print()
    input("Press Enter to continue...")
    
    async with async_playwright() as p:
        # Use exact same config as our main system
        browser = await p.firefox.launch(
            headless=False,
            firefox_user_prefs={
                "dom.webdriver.enabled": False,
                "useAutomationExtension": False,
                "general.platform.override": "MacIntel",
                "general.useragent.override": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7; rv:109.0) Gecko/20100101 Firefox/119.0"
            }
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7; rv:109.0) Gecko/20100101 Firefox/119.0'
        )
        
        page = await context.new_page()
        
        try:
            # Navigate to paper
            url = f"https://doi.org/{test_doi}"
            print(f"🌐 Navigating to: {url}")
            
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(3000)
            
            print(f"📍 Current URL: {page.url}")
            
            print(f"\n📋 PHASE 1: ENVIRONMENT CHECK")
            print("-" * 40)
            
            # Check environment
            env_check = await page.evaluate("""
                () => {
                    return {
                        userAgent: navigator.userAgent,
                        webdriver: navigator.webdriver,
                        plugins: navigator.plugins.length,
                        languages: navigator.languages,
                        cookieEnabled: navigator.cookieEnabled,
                        javaEnabled: navigator.javaEnabled(),
                        windowOuterSize: `${window.outerWidth}x${window.outerHeight}`,
                        screenSize: `${screen.width}x${screen.height}`,
                        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
                    };
                }
            """)
            
            print("Environment details:")
            for key, value in env_check.items():
                print(f"  {key}: {value}")
                
            print(f"\n📋 PHASE 2: MANUAL AUTHENTICATION TEST")
            print("-" * 40)
            print()
            print("🔴 PLEASE MANUALLY PERFORM AUTHENTICATION:")
            print("1. Click 'Institutional Sign In' in the top navigation")
            print("2. Click 'Access Through Your Institution' button")  
            print("3. Search for and select 'ETH Zurich'")
            print("4. Complete ETH login with your credentials")
            print("5. Wait to be redirected back to IEEE")
            print()
            print("When you're done with authentication, press Enter...")
            
            # Wait for user to complete authentication
            input()
            
            print(f"📍 Current URL after auth: {page.url}")
            
            # Check authentication status
            sign_out = await page.query_selector('*:has-text("Sign Out")')
            if sign_out:
                print("✅ Authentication detected - found Sign Out link")
            else:
                print("⚠️  No Sign Out link found - authentication may have failed")
            
            print(f"\n📋 PHASE 3: MANUAL PDF CLICK TEST")
            print("-" * 40)
            
            # Look for PDF button
            pdf_button = await page.query_selector('a[href*="/stamp/stamp.jsp"]')
            if pdf_button:
                href = await pdf_button.get_attribute('href')
                print(f"✅ PDF button found: {href}")
                
                print()
                print("🔴 PLEASE MANUALLY TEST PDF ACCESS:")
                print("1. Click the PDF button on the page")
                print("2. Observe what happens")
                print("3. Tell me the result:")
                print("   - Does it open the PDF viewer?")
                print("   - Does it redirect somewhere else?") 
                print("   - Does nothing happen?")
                print("   - Any error messages?")
                print()
                
                # Monitor page changes
                original_url = page.url
                print(f"📍 Starting URL: {original_url}")
                
                # Wait for user to test
                print("Click the PDF button now, then press Enter when done...")
                input()
                
                current_url = page.url
                print(f"📍 URL after PDF click: {current_url}")
                
                if current_url != original_url:
                    print(f"✅ Navigation occurred!")
                    if '/stamp/stamp.jsp' in current_url:
                        print(f"🎉 SUCCESS: Navigated to PDF viewer!")
                    else:
                        print(f"⚠️  Navigation to unexpected page")
                else:
                    print(f"❌ No navigation occurred")
                    
                # Check page content
                page_title = await page.title()
                print(f"📄 Current page title: {page_title}")
                
            else:
                print("❌ No PDF button found")
                
                # Look for alternative PDF elements
                pdf_elements = await page.query_selector_all('*:has-text("PDF"), *:has-text("Download")')
                if pdf_elements:
                    print(f"Found {len(pdf_elements)} elements containing PDF/Download text")
                else:
                    print("No PDF-related elements found at all")
            
            print(f"\n📋 PHASE 4: COMPARISON WITH REGULAR BROWSER")
            print("-" * 40)
            print()
            print("🔴 PLEASE COMPARE:")
            print("1. Open your regular Firefox/Chrome browser")
            print("2. Navigate to the same paper:")
            print(f"   {url}")
            print("3. Perform the same authentication steps")
            print("4. Try clicking the PDF button")
            print("5. Compare the behavior")
            print()
            print("Questions:")
            print("- Does the PDF button work in your regular browser?")
            print("- Is there any visual difference between the pages?")
            print("- Are there different elements or buttons shown?")
            print("- Any console errors in either browser?")
            print()
            
            print(f"Browser will stay open for detailed comparison...")
            print(f"Press Ctrl+C when you're done investigating.")
            
            # Keep open indefinitely for comparison
            try:
                while True:
                    await page.wait_for_timeout(10000)
            except KeyboardInterrupt:
                print("\n👋 Test completed by user")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_manual_click_verification())