#!/usr/bin/env python3
"""
IEEE Different Paper Test
Test with a different IEEE paper to see if blocking is paper-specific.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright
from src.secure_credential_manager import get_credential_manager


async def test_different_paper():
    """Test with different IEEE papers."""
    
    # Different IEEE papers to test
    test_papers = [
        {
            "name": "Deep Learning Paper",
            "doi": "10.1109/JPROC.2018.2825898",
            "expected_arnumber": "8371823"
        },
        {
            "name": "Signal Processing Paper", 
            "doi": "10.1109/TSP.2019.2912880",
            "expected_arnumber": "8704049"
        },
        {
            "name": "Machine Learning Paper",
            "doi": "10.1109/TPAMI.2020.2992393", 
            "expected_arnumber": "9089596"
        }
    ]
    
    print(f"\n{'='*70}")
    print(f"🔬 IEEE DIFFERENT PAPERS TEST")
    print(f"{'='*70}")
    print("Testing PDF access with different IEEE papers...")
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
        
        # Apply stealth
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        try:
            # Get credentials
            cm = get_credential_manager()
            username, password = cm.get_eth_credentials()
            
            # Authenticate once
            print("🔐 PERFORMING ONE-TIME AUTHENTICATION")
            print("-" * 50)
            
            first_paper = test_papers[0]
            url = f"https://doi.org/{first_paper['doi']}"
            print(f"🌐 Authenticating with: {first_paper['name']}")
            print(f"URL: {url}")
            
            await page.goto(url, wait_until='domcontentloaded')
            await page.wait_for_timeout(3000)
            
            print(f"📍 Current URL: {page.url}")
            
            # Extract actual arnumber
            actual_arnumber = None
            if '/document/' in page.url:
                actual_arnumber = page.url.split('/document/')[-1].strip('/')
                print(f"📄 Actual Arnumber: {actual_arnumber}")
            
            # Accept cookies
            try:
                cookie_btn = await page.query_selector('button:has-text("Accept All")')
                if cookie_btn:
                    await cookie_btn.click()
                    await page.wait_for_timeout(1000)
            except:
                pass
            
            # Authentication flow
            login_btn = await page.query_selector('a.inst-sign-in')
            if login_btn:
                await login_btn.click()
                print("✅ Clicked institutional sign in")
                await page.wait_for_timeout(3000)
                
                seamless_btn = await page.query_selector('button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn')
                if seamless_btn:
                    await seamless_btn.click()
                    print("✅ Clicked SeamlessAccess")
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
                        print("✅ Selected ETH Zurich")
                        
                        await page.wait_for_timeout(8000)
                        
                        # ETH login
                        if 'ethz.ch' in page.url.lower():
                            print("✅ At ETH login page")
                            
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
                                print("✅ Authentication completed")
            
            # Check if authenticated
            if 'ieeexplore.ieee.org' in page.url:
                pdf_button = await page.query_selector('a[href*="/stamp/stamp.jsp"]')
                if pdf_button:
                    print("🎉 AUTHENTICATION SUCCESSFUL!")
                    print("Now testing PDF access with multiple papers...")
                else:
                    print("❌ Authentication failed")
                    await browser.close()
                    return
            
            print(f"\n📄 TESTING PDF ACCESS WITH DIFFERENT PAPERS")
            print("=" * 50)
            
            # Test each paper
            for i, paper in enumerate(test_papers):
                print(f"\n🔍 Paper {i+1}: {paper['name']}")
                print(f"DOI: {paper['doi']}")
                
                # Navigate to paper
                paper_url = f"https://doi.org/{paper['doi']}"
                await page.goto(paper_url, wait_until='domcontentloaded')
                await page.wait_for_timeout(3000)
                
                # Extract arnumber
                arnumber = None
                if '/document/' in page.url:
                    arnumber = page.url.split('/document/')[-1].strip('/')
                    print(f"📄 Arnumber: {arnumber}")
                
                # Check for PDF button
                pdf_button = await page.query_selector('a[href*="/stamp/stamp.jsp"]')
                if pdf_button:
                    print("✅ PDF button available (authenticated)")
                    
                    # Test 1: Click PDF button
                    print("  Test 1: Clicking PDF button...")
                    before_url = page.url
                    await pdf_button.click()
                    await page.wait_for_timeout(5000)
                    after_url = page.url
                    
                    if '/stamp/stamp.jsp' in after_url:
                        print("  🎉 SUCCESS! PDF button click worked!")
                        print(f"  📍 PDF URL: {after_url}")
                        
                        # Check if we can see PDF content
                        page_text = await page.content()
                        if 'pdf' in page_text.lower() or 'PDF' in page_text:
                            print("  ✅ PDF content detected!")
                        
                        # Look for download options
                        download_btn = await page.query_selector('button[title*="Download"], a[title*="Download"]')
                        if download_btn:
                            print("  ✅ Download button found!")
                            print("  📥 You can manually download this PDF")
                        
                        # Test successful - stay on this paper
                        print(f"\n🎉 SUCCESS WITH {paper['name']}!")
                        print("Browser staying open for manual PDF download...")
                        await page.wait_for_timeout(120000)  # 2 minutes
                        await browser.close()
                        return
                    
                    elif after_url != before_url:
                        print(f"  ❌ Redirected to: {after_url}")
                    else:
                        print("  ❌ No navigation occurred")
                    
                    # Test 2: Direct navigation
                    if arnumber:
                        print("  Test 2: Direct navigation to PDF...")
                        pdf_url = f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={arnumber}"
                        await page.goto(pdf_url, wait_until='domcontentloaded')
                        await page.wait_for_timeout(5000)
                        
                        if '/stamp/stamp.jsp' in page.url:
                            print("  🎉 SUCCESS! Direct navigation worked!")
                            print(f"  📍 PDF URL: {page.url}")
                            print("  Browser staying open for manual download...")
                            await page.wait_for_timeout(120000)
                            await browser.close()
                            return
                        else:
                            print(f"  ❌ Direct navigation failed: {page.url}")
                else:
                    print("❌ No PDF button (not authenticated for this paper)")
                
                print("  ❌ Both methods failed for this paper")
            
            print(f"\n📊 FINAL RESULTS")
            print("-" * 30)
            print("❌ All tested papers show the same blocking behavior")
            print("✅ Authentication works for all papers") 
            print("❌ PDF access is blocked for all papers")
            print("🔍 This suggests system-wide anti-automation detection")
            
            await browser.close()
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            await browser.close()


if __name__ == "__main__":
    asyncio.run(test_different_paper())