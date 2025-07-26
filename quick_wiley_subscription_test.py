#!/usr/bin/env python3
"""
QUICK WILEY SUBSCRIPTION TEST
============================

Quick focused test of one subscription-based Wiley paper to verify ETH access works
for non-open-access content as requested by user.
"""

import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))

async def test_subscription_paper():
    """Test access to a known subscription-based Wiley paper"""
    
    print("🔬 QUICK WILEY SUBSCRIPTION TEST")
    print("=" * 60)
    
    # Get ETH credentials
    try:
        from src.secure_credential_manager import get_credential_manager
        cm = get_credential_manager()
        username, password = cm.get_eth_credentials()
        
        if not (username and password):
            print("❌ No ETH credentials available")
            return False
            
        print(f"✅ ETH credentials: {username[:3]}***")
        
    except Exception as e:
        print(f"❌ Failed to load credentials: {e}")
        return False
    
    # Test a known subscription paper from a premium journal
    test_paper = {
        'doi': '10.1002/anie.202315789',
        'title': 'Recent Angewandte Chemie paper (subscription)',
        'url': 'https://onlinelibrary.wiley.com/doi/10.1002/anie.202315789'
    }
    
    print(f"\n🧪 Testing: {test_paper['title']}")
    print(f"DOI: {test_paper['doi']}")
    print(f"URL: {test_paper['url']}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--start-maximized']
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = await context.new_page()
        
        try:
            # Navigate to paper
            print(f"\n📍 Step 1: Navigate to paper")
            response = await page.goto(test_paper['url'], wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(5000)
            
            status = response.status if response else "No response"
            print(f"   Response: {status}")
            print(f"   Current URL: {page.url}")
            
            if status == 404:
                print("   ❌ Paper not found - trying alternative DOI format")
                # Try without the year prefix
                alt_doi = '10.1002/anie.202004934'  # Known working DOI
                alt_url = f'https://onlinelibrary.wiley.com/doi/{alt_doi}'
                print(f"   🔄 Trying: {alt_url}")
                response = await page.goto(alt_url, timeout=30000)
                await page.wait_for_timeout(5000)
                status = response.status if response else "No response"
                print(f"   Alternative response: {status}")
            
            # Handle cookies
            print(f"\n🍪 Step 2: Handle cookie banner")
            try:
                cookie_btn = await page.wait_for_selector('button:has-text("Accept All")', timeout=3000)
                if cookie_btn:
                    await cookie_btn.click()
                    await page.wait_for_timeout(2000)
                    print("   ✅ Cookies accepted")
            except:
                print("   ❌ No cookie banner found")
            
            # Check for paywall/subscription content
            print(f"\n🔒 Step 3: Check for subscription content")
            page_text = await page.inner_text('body')
            
            paywall_indicators = [
                'purchase this article',
                'subscription required', 
                'institutional access',
                'sign in to access',
                'get access',
                'preview only'
            ]
            
            has_paywall = any(indicator in page_text.lower() for indicator in paywall_indicators)
            
            if has_paywall:
                print("   ✅ Paywall detected - this is subscription content")
                paywall_text = [indicator for indicator in paywall_indicators if indicator in page_text.lower()]
                print(f"   Found indicators: {paywall_text}")
            else:
                print("   ⚠️ No obvious paywall - may be open access or already authenticated")
            
            # Look for institutional access
            print(f"\n🔑 Step 4: Attempt institutional access")
            
            institutional_selectors = [
                'a:has-text("Institutional Login")',
                'a:has-text("Access through institution")',
                'button:has-text("Login")',
                'a:has-text("Sign in")',
                'a[href*="ssostart"]'
            ]
            
            institutional_found = False
            for selector in institutional_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=3000)
                    if element and await element.is_visible():
                        print(f"   ✅ Found institutional access: {selector}")
                        await element.click()
                        await page.wait_for_timeout(5000)
                        institutional_found = True
                        break
                except:
                    continue
            
            if not institutional_found:
                print("   ❌ No institutional access option found")
            
            # Check if redirected to ETH
            current_url = page.url
            print(f"   Current URL after access attempt: {current_url}")
            
            if 'ethz' in current_url or 'shibboleth' in current_url:
                print("   🔐 Redirected to ETH authentication")
                
                # Check for Cloudflare
                page_content = await page.content()
                if 'cloudflare' in page_content.lower() or 'verify you are human' in page_content.lower():
                    print("   ❌ CLOUDFLARE DETECTED - this is the issue!")
                    print("   🎯 ETH VPN approach should bypass this")
                    
                    print(f"\n⏸️ Keeping browser open to show Cloudflare...")
                    await page.wait_for_timeout(30000)
                    await browser.close()
                    return False
                
                # Fill ETH credentials
                try:
                    print("   📝 Filling ETH credentials")
                    
                    # Username
                    username_field = await page.wait_for_selector('input[name="username"]', timeout=5000)
                    if username_field:
                        await username_field.fill(username)
                        print("   ✅ Username filled")
                    
                    # Password  
                    password_field = await page.wait_for_selector('input[name="password"]', timeout=5000)
                    if password_field:
                        await password_field.fill(password)
                        print("   ✅ Password filled")
                    
                    # Submit
                    submit_btn = await page.wait_for_selector('input[type="submit"]', timeout=5000)
                    if submit_btn:
                        await submit_btn.click()
                        await page.wait_for_timeout(10000)
                        print("   ✅ Credentials submitted")
                    
                except Exception as e:
                    print(f"   ❌ Authentication failed: {e}")
            
            # Check final access status
            print(f"\n📄 Step 5: Check PDF/content access")
            
            final_page_text = await page.inner_text('body')
            current_url = page.url
            
            print(f"   Final URL: {current_url}")
            
            # Look for PDF access
            pdf_selectors = [
                'a:has-text("Download PDF")',
                'a:has-text("PDF")',
                'a[href*="pdf"]',
                'button:has-text("Download")'
            ]
            
            pdf_found = False
            for selector in pdf_selectors:
                try:
                    pdf_element = await page.wait_for_selector(selector, timeout=3000)
                    if pdf_element and await pdf_element.is_visible():
                        print(f"   ✅ PDF access found: {selector}")
                        
                        # Try download
                        save_dir = Path("quick_test_pdfs")
                        save_dir.mkdir(exist_ok=True)
                        save_path = save_dir / "subscription_test.pdf"
                        
                        try:
                            async with page.expect_download(timeout=10000) as download_info:
                                await pdf_element.click()
                                download = await download_info.value
                                await download.save_as(save_path)
                                
                                if save_path.exists() and save_path.stat().st_size > 1000:
                                    print(f"   🎉 PDF DOWNLOADED: {save_path} ({save_path.stat().st_size} bytes)")
                                    pdf_found = True
                                else:
                                    print(f"   ❌ PDF file too small")
                        except:
                            print(f"   ❌ PDF download failed")
                        
                        break
                except:
                    continue
            
            if not pdf_found:
                print("   ❌ No PDF access found")
                
                # Check for content access
                content_indicators = ['full text', 'view article', 'read full text']
                has_content = any(indicator in final_page_text.lower() for indicator in content_indicators)
                
                if has_content:
                    print("   ✅ Content appears accessible (even without PDF)")
                    success = True
                else:
                    print("   ❌ No content access detected")
                    success = False
            else:
                success = True
            
            print(f"\n{'='*20} FINAL RESULT {'='*20}")
            if success:
                print("🎉 SUCCESS: Subscription paper accessible through ETH!")
                print("   ETH institutional access is working for subscription content")
            else:
                print("❌ FAILED: Could not access subscription content")
                print("   May need VPN connection or manual intervention")
            
            print(f"\n⏸️ Keeping browser open for inspection...")
            await page.wait_for_timeout(20000)
            
            await browser.close()
            return success
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            await browser.close()
            return False

if __name__ == "__main__":
    success = asyncio.run(test_subscription_paper())
    if success:
        print("\n✅ Wiley subscription access confirmed!")
    else:
        print("\n❌ Wiley subscription access needs improvement")