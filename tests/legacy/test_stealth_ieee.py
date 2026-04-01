#!/usr/bin/env python3
"""
IEEE Stealth Mode Test
Remove ALL automation detection signatures to match manual browsing exactly.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright


async def test_stealth_ieee():
    """Test IEEE access with complete stealth mode to match manual browsing."""
    
    test_doi = "10.1109/JPROC.2018.2820126"
    
    print(f"\n🥷 IEEE STEALTH MODE TEST")
    print(f"DOI: {test_doi}")
    print("Removing ALL automation signatures...")
    print("=" * 60)
    
    async with async_playwright() as p:
        # Launch with minimal automation signatures
        browser = await p.firefox.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding'
            ],
            firefox_user_prefs={
                # Remove webdriver signatures  
                "dom.webdriver.enabled": False,
                "useAutomationExtension": False,
                
                # Normal browser signatures
                "general.platform.override": "MacIntel",
                "general.useragent.override": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7; rv:120.0) Gecko/20100101 Firefox/120.0",
                
                # Security preferences to match normal browsing
                "security.tls.insecure_fallback_hosts": "",
                "network.http.referer.XOriginPolicy": 0,
                "network.http.sendOriginHeader": 1,
                
                # Plugin and media preferences
                "media.peerconnection.enabled": True,
                "media.navigator.enabled": True,
                
                # Disable automation-specific features
                "marionette.enabled": False,
                "remote.enabled": False,
                
                # Normal content preferences
                "browser.cache.disk.enable": True,
                "browser.cache.memory.enable": True,
                "network.cookie.cookieBehavior": 0
            }
        )
        
        # Create context with normal browser signatures
        context = await browser.new_context(
            viewport={'width': 1440, 'height': 900},  # More common resolution
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/New_York',
            permissions=['geolocation', 'notifications'],
            color_scheme='light'
        )
        
        page = await context.new_page()
        
        # Ultra stealth: Remove ALL automation signatures
        await page.add_init_script("""
            // Remove webdriver property completely
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // Add realistic plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {
                        0: {type: "application/pdf", suffixes: "pdf", description: "Portable Document Format"},
                        description: "Portable Document Format",
                        filename: "internal-pdf-viewer",
                        length: 1,
                        name: "PDF Viewer"
                    },
                    {
                        0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
                        description: "Portable Document Format", 
                        filename: "internal-pdf-viewer",
                        length: 1,
                        name: "Chrome PDF Plugin"
                    }
                ],
            });
            
            // Add realistic languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
            
            // Mock Chrome object for Chrome user agent
            window.chrome = {
                runtime: {
                    onConnect: undefined,
                    onMessage: undefined
                },
                loadTimes: function() {
                    return {
                        commitLoadTime: Date.now() / 1000 - Math.random(),
                        connectionInfo: 'http/1.1',
                        finishDocumentLoadTime: Date.now() / 1000 - Math.random(),
                        finishLoadTime: Date.now() / 1000 - Math.random(),
                        firstPaintAfterLoadTime: Date.now() / 1000 - Math.random(),
                        firstPaintTime: Date.now() / 1000 - Math.random(),
                        navigationType: 'Other',
                        requestTime: Date.now() / 1000 - Math.random(),
                        startLoadTime: Date.now() / 1000 - Math.random(),
                        wasAlternateProtocolAvailable: false,
                        wasFetchedViaSpdy: false,
                        wasNpnNegotiated: false
                    };
                },
                csi: function() {
                    return {
                        startE: Date.now(),
                        onloadT: Date.now(),
                        pageT: Date.now() - performance.timing.navigationStart,
                        tran: 15
                    };
                }
            };
            
            // Remove automation-specific properties
            delete window.navigator.webdriver;
            delete window._phantom;
            delete window.callPhantom;
            delete window._selenium;
            delete window.selenium;
            delete window.webdriver;
            delete window.__nightmare;
            delete window.__puppeteer_evaluation_script__;
            delete window.__fxdriver_evaluate;
            delete window.__driver_unwrapped;
            delete window.__webdriver_unwrapped;
            delete window.__driver_evaluate;
            delete window.__webdriver_evaluate;
            delete window.__selenium_unwrapped;
            delete window.__fxdriver_unwrapped;
            
            // Override permission queries to return realistic results
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // Add realistic screen properties
            Object.defineProperty(screen, 'availHeight', {get: () => 875});
            Object.defineProperty(screen, 'availWidth', {get: () => 1440});
            Object.defineProperty(screen, 'colorDepth', {get: () => 24});
            Object.defineProperty(screen, 'pixelDepth', {get: () => 24});
            
            // Mock realistic performance timing
            const timing = performance.timing;
            Object.defineProperty(performance, 'timing', {
                get: () => ({
                    ...timing,
                    navigationStart: Date.now() - Math.random() * 1000,
                    loadEventEnd: Date.now() - Math.random() * 100
                })
            });
        """)
        
        try:
            from src.secure_credential_manager import get_credential_manager
            cm = get_credential_manager()
            username, password = cm.get_eth_credentials()
            
            print("🥷 STEALTH MODE ACTIVATED")
            
            # Navigate to paper
            url = f"https://doi.org/{test_doi}"
            print(f"🌐 Navigating to: {url}")
            
            # Navigate like a human - slower and with pauses
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(3000)  # Human-like pause
            
            print(f"📍 Current URL: {page.url}")
            
            # Check stealth mode effectiveness
            stealth_check = await page.evaluate("""
                () => {
                    const checks = {
                        'navigator.webdriver': navigator.webdriver,
                        'window.chrome exists': !!window.chrome,
                        'plugins length': navigator.plugins.length,
                        'languages': navigator.languages.length
                    };
                    return checks;
                }
            """)
            
            print(f"🔍 Stealth mode check:")
            for key, value in stealth_check.items():
                status = "✅" if (key == 'navigator.webdriver' and value is None) or (key != 'navigator.webdriver' and value) else "❌"
                print(f"   {status} {key}: {value}")
            
            # Human-like scrolling and mouse movement
            print(f"🖱️  Simulating human behavior...")
            await page.mouse.move(500, 300, steps=3)
            await page.wait_for_timeout(1000)
            await page.evaluate("window.scrollBy(0, 200)")
            await page.wait_for_timeout(2000)
            
            print(f"\n🔐 STARTING AUTHENTICATION WITH STEALTH...")
            
            # Step 1: Find and click institutional sign in (with human-like behavior)
            login_button = await page.wait_for_selector('a.inst-sign-in', timeout=10000)
            
            # Move mouse to button gradually
            box = await login_button.bounding_box()
            await page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2, steps=5)
            await page.wait_for_timeout(500)
            
            await login_button.click()
            print("✅ Clicked institutional sign in")
            await page.wait_for_timeout(3000)  # Longer human-like pause
            
            # Step 2: Click SeamlessAccess button (with human behavior)
            seamless_btn = await page.wait_for_selector('button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn', timeout=10000)
            
            box = await seamless_btn.bounding_box()
            await page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2, steps=3)
            await page.wait_for_timeout(800)
            
            await seamless_btn.click()
            print("✅ Clicked SeamlessAccess button")
            await page.wait_for_timeout(3000)
            
            # Step 3: Type ETH Zurich (character by character like human)
            search_input = await page.wait_for_selector('input.inst-typeahead-input', timeout=10000)
            await search_input.click()
            await page.wait_for_timeout(500)
            
            # Type slowly like human
            await search_input.type("ETH Zurich", delay=150)
            print("✅ Entered ETH Zurich (human-like typing)")
            await page.wait_for_timeout(3000)  # Wait for dropdown
            
            # Step 4: Try multiple selectors for ETH option
            eth_selectors = [
                'a#ETH\\\\ Zurich\\\\ -\\\\ ETH\\\\ Zurich',
                'a[id="ETH Zurich - ETH Zurich"]',
                'div.selection-item a:has-text("ETH Zurich")',
                'a[href*="aai-logon.ethz.ch"]'
            ]
            
            eth_option = None
            for selector in eth_selectors:
                try:
                    eth_option = await page.wait_for_selector(selector, timeout=5000)
                    if eth_option:
                        print(f"✅ Found ETH option with: {selector}")
                        break
                except:
                    continue
            
            if not eth_option:
                print("❌ Could not find ETH option in dropdown")
                print("🔍 Let's inspect what's in the dropdown...")
                
                # Check what options are actually available
                dropdown_items = await page.query_selector_all('div.selection-item, .institution-option, a[id*="ETH"]')
                print(f"📋 Found {len(dropdown_items)} dropdown items")
                
                for i, item in enumerate(dropdown_items[:5]):  # Show first 5
                    text = await item.text_content()
                    href = await item.get_attribute('href') if await item.evaluate("el => el.tagName") == 'A' else 'N/A'
                    print(f"   {i+1}. Text: '{text[:50]}...' | Href: {href}")
                
                # Try clicking the first ETH-related option
                for item in dropdown_items:
                    text = await item.text_content()
                    if 'ETH' in text and 'Zurich' in text:
                        print(f"🎯 Trying to click: {text}")
                        await item.click()
                        eth_option = item
                        break
            
            if eth_option:
                await page.wait_for_timeout(1000)
                await eth_option.click()
                print("✅ Selected ETH Zurich")
                await page.wait_for_timeout(8000)  # Wait for navigation
                
                # Continue with ETH login...
                if 'ethz.ch' in page.url.lower():
                    print("✅ Reached ETH login page")
                    
                    # Human-like ETH login
                    username_field = await page.wait_for_selector('input[name="j_username"]', timeout=10000)
                    await username_field.click()
                    await page.wait_for_timeout(500)
                    await username_field.type(username, delay=100)
                    
                    password_field = await page.wait_for_selector('input[name="j_password"]', timeout=10000)
                    await password_field.click()
                    await page.wait_for_timeout(500)
                    await password_field.type(password, delay=120)
                    
                    submit_btn = await page.wait_for_selector('button[type="submit"]', timeout=10000)
                    await page.wait_for_timeout(1000)  # Pause before submit
                    await submit_btn.click()
                    print("✅ Submitted ETH credentials")
                    
                    # Wait for redirect
                    await page.wait_for_timeout(15000)
                    
                    if 'ieeexplore.ieee.org' in page.url:
                        print("🎉 STEALTH AUTHENTICATION SUCCESSFUL!")
                        print(f"📍 Back at: {page.url}")
                        
                        # Test PDF access with stealth
                        pdf_button = await page.wait_for_selector('a[href*="/stamp/stamp.jsp"]', timeout=10000)
                        if pdf_button:
                            href = await pdf_button.get_attribute('href')
                            print(f"📄 PDF button found: {href}")
                            
                            # Human-like PDF click
                            box = await pdf_button.bounding_box()
                            await page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2, steps=4)
                            await page.wait_for_timeout(1000)
                            
                            print("🖱️  Clicking PDF button with stealth...")
                            await pdf_button.click()
                            await page.wait_for_timeout(8000)
                            
                            final_url = page.url
                            print(f"📍 After PDF click: {final_url}")
                            
                            if '/stamp/stamp.jsp' in final_url:
                                print("🎉 STEALTH PDF ACCESS SUCCESSFUL!")
                                return True
                            else:
                                print("❌ PDF access still blocked with stealth mode")
                                return False
            
            print("❌ Authentication flow failed")
            return False
            
        except Exception as e:
            print(f"❌ Stealth mode error: {e}")
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            print(f"\n⏸️  Browser staying open for manual comparison...")
            await page.wait_for_timeout(60000)  # 1 minute
            await browser.close()

if __name__ == "__main__":
    success = asyncio.run(test_stealth_ieee())
    if success:
        print("\n🎉 STEALTH MODE SUCCESSFUL!")
    else:
        print("\n❌ Stealth mode still has issues")