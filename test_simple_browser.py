#!/usr/bin/env python3
"""
Simple browser automation test following the working IEEE pattern
"""

import asyncio
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

async def test_wiley_like_ieee():
    """Test Wiley following the exact IEEE pattern"""
    print("Testing Wiley Browser Automation (IEEE Pattern)")
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
        
        # Test with a specific Wiley DOI (like IEEE approach)
        test_doi = "10.1002/anie.201506954"  # A real Wiley paper
        wiley_url = f"https://doi.org/{test_doi}"
        
        print(f"Testing DOI: {test_doi}")
        print(f"URL: {wiley_url}")
        
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
                
                print("→ Looking for institutional access...")
                
                # Look for institutional access buttons
                institutional_selectors = [
                    'text="Institutional Login"',
                    'text="Access through your institution"',
                    'text="Sign in via your institution"',
                    'a[href*="institutional"]',
                    'button:has-text("Institution")'
                ]
                
                found_login = False
                for selector in institutional_selectors:
                    try:
                        elem = await page.wait_for_selector(selector, timeout=2000)
                        if elem:
                            print(f"✓ Found institutional login: {selector}")
                            await elem.click()
                            found_login = True
                            break
                    except:
                        continue
                
                if not found_login:
                    print("✗ No institutional login found")
                    # Take screenshot for debugging
                    await page.screenshot(path='wiley_no_login.png')
                    print("  Screenshot saved as wiley_no_login.png")
                    return
                
                # Wait for institution selector
                await page.wait_for_timeout(3000)
                
                print("→ Looking for ETH Zurich...")
                
                # Look for ETH in institution list
                eth_selectors = [
                    'text="ETH Zurich"',
                    'text="Swiss Federal Institute"',
                    'option:has-text("ETH")',
                    'li:has-text("ETH")'
                ]
                
                found_eth = False
                for selector in eth_selectors:
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
                    print("✗ ETH Zurich not found in institution list")
                    await page.screenshot(path='wiley_no_eth.png')
                    print("  Screenshot saved as wiley_no_eth.png")
                    return
                
                # Wait for ETH login page
                await page.wait_for_timeout(5000)
                
                print("→ Filling ETH credentials...")
                
                # Fill credentials
                username_filled = False
                username_selectors = [
                    'input[name="j_username"]',
                    'input[name="username"]',
                    'input[id="username"]'
                ]
                
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
                
                password_filled = False
                password_selectors = [
                    'input[name="j_password"]',
                    'input[name="password"]',
                    'input[id="password"]'
                ]
                
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
                    await page.screenshot(path='wiley_no_form.png')
                    print("  Screenshot saved as wiley_no_form.png")
                    return
                
                # Submit form
                print("→ Submitting login...")
                submit_selectors = [
                    'input[type="submit"]',
                    'button[type="submit"]',
                    'button:has-text("Login")',
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
                    return
                
                # Wait for authentication
                print("→ Waiting for authentication...")
                await page.wait_for_timeout(10000)
                
                # Check if back at Wiley with access
                current_url = page.url
                print(f"Final URL: {current_url}")
                
                if 'wiley.com' in current_url and 'login' not in current_url.lower():
                    print("✓ Successfully authenticated with Wiley!")
                    
                    # Look for PDF download
                    pdf_selectors = [
                        'a:has-text("PDF")',
                        'a[href*=".pdf"]',
                        'button:has-text("Download PDF")'
                    ]
                    
                    for selector in pdf_selectors:
                        try:
                            elem = await page.wait_for_selector(selector, timeout=3000)
                            if elem:
                                print(f"✓ Found PDF download option: {selector}")
                                break
                        except:
                            continue
                    else:
                        print("→ No PDF download found (may require subscription)")
                        
                    await page.screenshot(path='wiley_success.png')
                    print("  Success screenshot saved as wiley_success.png")
                    
                else:
                    print("✗ Authentication may have failed")
                    await page.screenshot(path='wiley_failed.png')
                    print("  Screenshot saved as wiley_failed.png")
                
            finally:
                await browser.close()
                
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Run simple browser test"""
    print("Simple Browser Automation Test")
    print("Following the working IEEE pattern")
    print("="*50)
    
    # Check requirements
    try:
        from playwright.async_api import async_playwright
        print("✓ Playwright available")
    except ImportError:
        print("✗ Install Playwright: pip install playwright && playwright install")
        return
    
    await test_wiley_like_ieee()
    
    print("\n" + "="*50)
    print("Test completed. Check screenshots for debugging.")

if __name__ == "__main__":
    asyncio.run(main())