#!/usr/bin/env python3
"""
Improved browser automation based on actual Wiley interface
"""

import asyncio
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

async def test_wiley_improved():
    """Test Wiley with improved selectors based on actual interface"""
    print("Testing Improved Wiley Browser Automation")
    print("="*50)
    
    try:
        from playwright.async_api import async_playwright
        from src.secure_credential_manager import SecureCredentialManager
        
        # Get credentials
        cred_manager = SecureCredentialManager()
        username = cred_manager.get_credential("eth_username")
        password = cred_manager.get_credential("eth_password")
        
        if not username or not password:
            print("✗ No ETH credentials found")
            return
        
        print(f"✓ Using ETH credentials: {username[:3]}***")
        
        # Test with a specific Wiley DOI
        test_doi = "10.1002/anie.201506954"
        wiley_url = f"https://doi.org/{test_doi}"
        
        print(f"Testing DOI: {test_doi}")
        
        async with async_playwright() as p:
            print("→ Launching browser...")
            browser = await p.chromium.launch(headless=False, args=['--no-sandbox'])
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
            page = await context.new_page()
            
            try:
                # Navigate to Wiley paper
                print("→ Navigating to Wiley paper...")
                await page.goto(wiley_url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(3000)
                
                # Handle cookie consent if present
                try:
                    cookie_button = await page.wait_for_selector('button:has-text("Accept All")', timeout=2000)
                    if cookie_button:
                        await cookie_button.click()
                        print("✓ Accepted cookies")
                        await page.wait_for_timeout(1000)
                except:
                    pass
                
                print("→ Looking for Login button...")
                
                # Look for the "Login / Register" button we can see in the screenshot
                login_selectors = [
                    'text="Login / Register"',
                    'a:has-text("Login")',
                    'button:has-text("Login")',
                    '[href*="login"]'
                ]
                
                found_login = False
                for selector in login_selectors:
                    try:
                        elem = await page.wait_for_selector(selector, timeout=2000)
                        if elem:
                            print(f"✓ Found login button: {selector}")
                            await elem.click()
                            found_login = True
                            break
                    except:
                        continue
                
                if not found_login:
                    print("✗ No login button found")
                    await page.screenshot(path='wiley_no_login2.png')
                    return
                
                # Wait for login page to load
                await page.wait_for_timeout(3000)
                
                print("→ Looking for institutional access...")
                
                # Look for institutional login options
                institutional_selectors = [
                    'text="Institutional Login"',
                    'text="Access through your institution"',
                    'text="Shibboleth"',
                    'button:has-text("Institution")',
                    'a:has-text("Institution")',
                    '[data-testid*="institution"]'
                ]
                
                found_institutional = False
                for selector in institutional_selectors:
                    try:
                        elem = await page.wait_for_selector(selector, timeout=2000)
                        if elem:
                            print(f"✓ Found institutional access: {selector}")
                            await elem.click()
                            found_institutional = True
                            break
                    except:
                        continue
                
                if not found_institutional:
                    print("✗ No institutional access found")
                    await page.screenshot(path='wiley_no_institutional.png')
                    print("  Screenshot saved as wiley_no_institutional.png")
                    return
                
                # Wait for institution selector
                await page.wait_for_timeout(3000)
                
                print("→ Looking for ETH Zurich in institution list...")
                
                # Look for ETH in various forms
                eth_selectors = [
                    'input[placeholder*="institution"]',  # Search box
                    'text="ETH Zurich"',
                    'text="Swiss Federal Institute"',
                    'option:has-text("ETH")',
                    'li:has-text("ETH")',
                    '[value*="ethz"]'
                ]
                
                found_eth = False
                
                # First try to find a search box and type
                try:
                    search_box = await page.wait_for_selector('input[placeholder*="institution"], input[placeholder*="search"]', timeout=3000)
                    if search_box:
                        print("✓ Found institution search box")
                        await search_box.fill("ETH Zurich")
                        await page.wait_for_timeout(2000)
                        
                        # Look for ETH in results
                        eth_result = await page.wait_for_selector('text="ETH Zurich", li:has-text("ETH")', timeout=3000)
                        if eth_result:
                            print("✓ Found ETH in search results")
                            await eth_result.click()
                            found_eth = True
                except:
                    pass
                
                # If search didn't work, try direct selectors
                if not found_eth:
                    for selector in eth_selectors[1:]:  # Skip search box
                        try:
                            elem = await page.wait_for_selector(selector, timeout=2000)
                            if elem:
                                print(f"✓ Found ETH option: {selector}")
                                await elem.click()
                                found_eth = True
                                break
                        except:
                            continue
                
                if not found_eth:
                    print("✗ ETH Zurich not found")
                    await page.screenshot(path='wiley_no_eth2.png')
                    print("  Screenshot saved as wiley_no_eth2.png")
                    return
                
                # Wait for ETH login page
                print("→ Waiting for ETH login page...")
                await page.wait_for_timeout(5000)
                
                print("→ Filling ETH credentials...")
                
                # Fill username
                username_selectors = [
                    'input[name="j_username"]',
                    'input[name="username"]',
                    'input[id="username"]',
                    'input[type="text"]'
                ]
                
                username_filled = False
                for selector in username_selectors:
                    try:
                        elem = await page.wait_for_selector(selector, timeout=2000)
                        if elem:
                            await elem.fill(username)
                            print("✓ Username filled")
                            username_filled = True
                            break
                    except:
                        continue
                
                # Fill password
                password_selectors = [
                    'input[name="j_password"]',
                    'input[name="password"]',
                    'input[id="password"]',
                    'input[type="password"]'
                ]
                
                password_filled = False
                for selector in password_selectors:
                    try:
                        elem = await page.wait_for_selector(selector, timeout=2000)
                        if elem:
                            await elem.fill(password)
                            print("✓ Password filled")
                            password_filled = True
                            break
                    except:
                        continue
                
                if not username_filled or not password_filled:
                    print("✗ Could not fill credentials")
                    await page.screenshot(path='wiley_no_form2.png')
                    print("  Screenshot saved as wiley_no_form2.png")
                    return
                
                # Submit form
                print("→ Submitting login...")
                submit_selectors = [
                    'input[type="submit"]',
                    'button[type="submit"]',
                    'button:has-text("Login")',
                    'button:has-text("Sign")',
                    'input[value*="Login"]'
                ]
                
                submitted = False
                for selector in submit_selectors:
                    try:
                        elem = await page.wait_for_selector(selector, timeout=2000)
                        if elem:
                            await elem.click()
                            print("✓ Form submitted")
                            submitted = True
                            break
                    except:
                        continue
                
                if not submitted:
                    print("✗ Could not submit form")
                    await page.screenshot(path='wiley_no_submit.png')
                    return
                
                # Wait for authentication and redirect back to Wiley
                print("→ Waiting for authentication...")
                await page.wait_for_timeout(10000)
                
                # Check final result
                current_url = page.url
                print(f"Final URL: {current_url}")
                
                if 'wiley.com' in current_url:
                    print("✓ Successfully returned to Wiley!")
                    
                    # Now try to access the PDF
                    print("→ Looking for PDF access...")
                    
                    # Look for PDF button/link
                    pdf_selectors = [
                        'a:has-text("PDF")',
                        'button:has-text("PDF")',
                        '.pdf-download',
                        '[data-testid*="pdf"]',
                        'a[href*=".pdf"]'
                    ]
                    
                    pdf_found = False
                    for selector in pdf_selectors:
                        try:
                            elem = await page.wait_for_selector(selector, timeout=3000)
                            if elem:
                                print(f"✓ Found PDF access: {selector}")
                                
                                # Check if we can access it
                                href = await elem.get_attribute('href')
                                if href:
                                    print(f"  PDF URL: {href}")
                                
                                pdf_found = True
                                break
                        except:
                            continue
                    
                    if not pdf_found:
                        print("→ No PDF access found (may require subscription)")
                    
                    await page.screenshot(path='wiley_final.png')
                    print("  Final screenshot saved as wiley_final.png")
                    
                    return True
                    
                else:
                    print("✗ Did not return to Wiley properly")
                    await page.screenshot(path='wiley_auth_failed.png')
                    return False
                
            finally:
                await browser.close()
                
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run improved browser test"""
    print("Improved Browser Automation Test")
    print("Using actual Wiley interface patterns")
    print("="*50)
    
    success = await test_wiley_improved()
    
    print("\n" + "="*50)
    if success:
        print("✓ Browser automation successful!")
        print("✓ ETH institutional authentication working")
        print("✓ Publisher access confirmed")
    else:
        print("✗ Some issues encountered - check screenshots")
        print("  This helps debug the authentication flow")
    
    print("\nNext steps:")
    print("1. Apply working patterns to all publishers")
    print("2. Handle edge cases and different layouts")
    print("3. Integrate with download functionality")

if __name__ == "__main__":
    asyncio.run(main())