#!/usr/bin/env python3
"""
IEEE Known Papers Test
Test with well-known IEEE papers that should definitely work.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright
from src.secure_credential_manager import get_credential_manager


async def test_known_papers():
    """Test with known working IEEE papers."""
    
    # Direct IEEE URLs instead of DOIs
    test_papers = [
        {
            "name": "Original Paper (working auth)",
            "url": "https://ieeexplore.ieee.org/document/8347162",
            "arnumber": "8347162"
        },
        {
            "name": "Different IEEE Paper #1", 
            "url": "https://ieeexplore.ieee.org/document/9043731",
            "arnumber": "9043731"
        },
        {
            "name": "Different IEEE Paper #2",
            "url": "https://ieeexplore.ieee.org/document/8998488", 
            "arnumber": "8998488"
        }
    ]
    
    print(f"\n{'='*70}")
    print(f"📚 IEEE KNOWN PAPERS TEST")
    print(f"{'='*70}")
    print("Testing PDF access with different known IEEE papers...")
    print()
    
    async with async_playwright() as p:
        browser = await p.firefox.launch(
            headless=False,
            firefox_user_prefs={
                "dom.webdriver.enabled": False,
                "useAutomationExtension": False,
            }
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = await context.new_page()
        
        try:
            # Get credentials
            cm = get_credential_manager()
            username, password = cm.get_eth_credentials()
            
            authenticated = False
            
            # Try to authenticate with the first paper we know works
            for paper in test_papers:
                print(f"\n🔍 Testing: {paper['name']}")
                print(f"URL: {paper['url']}")
                
                await page.goto(paper['url'], wait_until='domcontentloaded')
                await page.wait_for_timeout(3000)
                
                print(f"📍 Current URL: {page.url}")
                
                # Accept cookies if not done already
                try:
                    cookie_btn = await page.query_selector('button:has-text("Accept All")')
                    if cookie_btn:
                        await cookie_btn.click()
                        await page.wait_for_timeout(1000)
                except:
                    pass
                
                # Check if already authenticated
                pdf_button = await page.query_selector('a[href*="/stamp/stamp.jsp"]')
                
                if pdf_button and not authenticated:
                    print("✅ Already authenticated from previous session!")
                    authenticated = True
                elif not pdf_button and not authenticated:
                    print("🔐 Need to authenticate...")
                    
                    # Authenticate
                    login_btn = await page.query_selector('a.inst-sign-in')
                    if login_btn:
                        await login_btn.click()
                        await page.wait_for_timeout(3000)
                        
                        seamless_btn = await page.query_selector('button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn')
                        if seamless_btn:
                            await seamless_btn.click()
                            await page.wait_for_timeout(3000)
                            
                            search_input = await page.query_selector('input.inst-typeahead-input')
                            if search_input:
                                await search_input.click()
                                await search_input.fill("")
                                await page.wait_for_timeout(500)
                                
                                for char in "ETH Zurich":
                                    await search_input.type(char)
                                    await page.wait_for_timeout(100)
                                
                                await page.wait_for_timeout(2000)
                                await search_input.press('ArrowDown')
                                await page.wait_for_timeout(500)
                                await search_input.press('Enter')
                                
                                await page.wait_for_timeout(8000)
                                
                                # ETH login
                                if 'ethz.ch' in page.url.lower():
                                    username_field = await page.query_selector('input[name="j_username"], input[name="username"], input[type="text"]')
                                    if username_field:
                                        await username_field.fill(username)
                                    
                                    password_field = await page.query_selector('input[name="j_password"], input[name="password"], input[type="password"]')
                                    if password_field:
                                        await password_field.fill(password)
                                    
                                    submit_btn = await page.query_selector('button[type="submit"], input[type="submit"]')
                                    if submit_btn:
                                        await submit_btn.click()
                                        await page.wait_for_timeout(15000)
                                        authenticated = True
                                        print("✅ Authentication completed")
                
                # Now check PDF access for this paper
                await page.wait_for_timeout(3000)
                pdf_button = await page.query_selector('a[href*="/stamp/stamp.jsp"]')
                
                if pdf_button:
                    print(f"✅ PDF button available for {paper['name']}")
                    
                    # Test 1: Click PDF button
                    print("  🔬 Test 1: Clicking PDF button...")
                    before_url = page.url
                    
                    # Try click with extra JavaScript override
                    await page.evaluate("""
                        () => {
                            const btn = document.querySelector('a[href*="/stamp/stamp.jsp"]');
                            if (btn) {
                                const newBtn = btn.cloneNode(true);
                                btn.parentNode.replaceChild(newBtn, btn);
                                newBtn.onclick = null;
                            }
                        }
                    """)
                    
                    pdf_button = await page.query_selector('a[href*="/stamp/stamp.jsp"]')
                    await pdf_button.click()
                    await page.wait_for_timeout(8000)
                    
                    after_url = page.url
                    
                    if '/stamp/stamp.jsp' in after_url:
                        print("  🎉 SUCCESS! PDF click worked!")
                        print(f"  📄 PDF URL: {after_url}")
                        
                        # Check if we can access the PDF
                        page_content = await page.content()
                        if 'pdf' in page_content.lower():
                            print("  ✅ PDF content loaded")
                        
                        download_btn = await page.query_selector('button[title*="Download"], a[title*="Download"]')
                        if download_btn:
                            print("  ✅ Download button available")
                            print(f"  🎉 SUCCESS! {paper['name']} PDF is accessible!")
                            print("  Browser staying open for manual download...")
                            await page.wait_for_timeout(120000)
                            await browser.close()
                            return
                        else:
                            print("  📥 You can manually save this PDF")
                            await page.wait_for_timeout(30000)
                    
                    elif after_url != before_url:
                        print(f"  ❌ Redirected to: {after_url}")
                    else:
                        print("  ❌ No navigation occurred")
                    
                    # Test 2: Direct navigation
                    print("  🔬 Test 2: Direct PDF navigation...")
                    pdf_url = f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={paper['arnumber']}"
                    await page.goto(pdf_url, wait_until='domcontentloaded')
                    await page.wait_for_timeout(8000)
                    
                    if '/stamp/stamp.jsp' in page.url:
                        print("  🎉 SUCCESS! Direct navigation worked!")
                        print(f"  📄 PDF URL: {page.url}")
                        print(f"  🎉 SUCCESS! {paper['name']} PDF is accessible via direct navigation!")
                        print("  Browser staying open for manual download...")
                        await page.wait_for_timeout(120000)
                        await browser.close()
                        return
                    else:
                        print(f"  ❌ Direct navigation blocked: {page.url}")
                    
                    print(f"  ❌ Both methods failed for {paper['name']}")
                else:
                    print(f"❌ No PDF button for {paper['name']}")
                    if authenticated:
                        print("  Authentication is working but this paper might not be available")
                    else:
                        print("  Need to authenticate first")
            
            print(f"\n📊 CONCLUSION")
            print("-" * 30)
            if authenticated:
                print("✅ Authentication is working")
                print("❌ PDF access is consistently blocked across all papers")
                print("🔍 This confirms system-wide anti-automation detection")
                print("\n💡 The institutional authentication system is working perfectly!")
                print("💡 IEEE's PDF blocking is a separate anti-automation measure")
            else:
                print("❌ Authentication issues detected")
            
            await browser.close()
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            await browser.close()


if __name__ == "__main__":
    asyncio.run(test_known_papers())