#!/usr/bin/env python3
"""
SIAM Modal Investigation
========================

Investigate what should happen in the modal after clicking institutional access.
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def investigate_siam_modal():
    print("🔍 INVESTIGATING SIAM MODAL BEHAVIOR")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Navigate to SIAM paper
            test_doi = "10.1137/S0097539795293172"
            siam_url = f"https://epubs.siam.org/doi/{test_doi}"
            print(f"1. Navigating to: {siam_url}")
            await page.goto(siam_url, timeout=90000)
            await page.wait_for_timeout(5000)
            
            # Click GET ACCESS
            print("2. Clicking GET ACCESS...")
            access_button = await page.wait_for_selector('a:has-text("GET ACCESS")', timeout=15000)
            await access_button.click()
            await page.wait_for_timeout(5000)
            print("   Modal should be open now")
            
            # Take screenshot of modal
            await page.screenshot(path="siam_modal_1_initial.png")
            print("   Screenshot: siam_modal_1_initial.png")
            
            # Try clicking the institutional access link and watch for changes
            print("3. Clicking 'Access via your Institution' and monitoring changes...")
            
            # Set up monitoring for network requests
            network_requests = []
            page.on('request', lambda request: network_requests.append(f"{request.method} {request.url}"))
            
            # Set up monitoring for console logs
            console_logs = []
            page.on('console', lambda msg: console_logs.append(f"{msg.type}: {msg.text}"))
            
            # Get the institutional link
            inst_link = await page.wait_for_selector('a:has-text("Access via your Institution")', timeout=15000)
            
            # Get the href to see where it should go
            href = await inst_link.get_attribute('href')
            print(f"   Link href: {href}")
            
            # Try regular click first
            print("   Trying regular click...")
            await inst_link.click()
            await page.wait_for_timeout(3000)
            
            # Check if anything changed
            current_url = page.url
            print(f"   URL after click: {current_url}")
            
            # Take screenshot after click
            await page.screenshot(path="siam_modal_2_after_click.png")
            print("   Screenshot: siam_modal_2_after_click.png")
            
            # Check for any new elements that might have appeared
            print("4. Looking for institutional login elements...")
            
            # Common institutional login selectors
            institutional_selectors = [
                'input#shibboleth_search',
                'input[placeholder*="institution"]',
                'select[name*="institution"]',
                '.institutional-login',
                '.shibboleth-login',
                '#institutional-access-form',
                'form[action*="shibboleth"]',
                'form[action*="institutional"]',
                'iframe[src*="shibboleth"]',
                'iframe[src*="institutional"]'
            ]
            
            found_elements = []
            for selector in institutional_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=2000)
                    if element:
                        print(f"   ✓ Found: {selector}")
                        found_elements.append(selector)
                except:
                    continue
            
            if not found_elements:
                print("   ❌ No institutional login elements found")
                
                # Maybe we need to wait longer or the modal content loads dynamically
                print("5. Waiting for dynamic content...")
                await page.wait_for_timeout(10000)
                
                # Take another screenshot
                await page.screenshot(path="siam_modal_3_after_wait.png")
                print("   Screenshot: siam_modal_3_after_wait.png")
                
                # Check if there are any iframes that might contain the institutional login
                iframes = await page.query_selector_all('iframe')
                print(f"   Found {len(iframes)} iframes")
                
                for i, iframe in enumerate(iframes):
                    src = await iframe.get_attribute('src')
                    print(f"     Iframe {i+1}: src='{src}'")
                    
                    # If there's a shibboleth iframe, that might be what we need
                    if src and ('shibboleth' in src.lower() or 'institutional' in src.lower()):
                        print(f"     ✓ Found institutional iframe!")
                        
                        # Try to interact with the iframe
                        try:
                            frame = await iframe.content_frame()
                            if frame:
                                await frame.wait_for_timeout(3000)
                                # Look for the search input in the iframe
                                search_input = await frame.wait_for_selector('input#shibboleth_search', timeout=5000)
                                if search_input:
                                    print(f"     ✓ Found shibboleth search in iframe!")
                                    return True
                        except:
                            print(f"     ❌ Could not access iframe content")
            
            # Print network requests to see if anything interesting happened
            if network_requests:
                print("6. Network requests during modal interaction:")
                for req in network_requests[-10:]:  # Last 10 requests
                    print(f"   {req}")
            
            # Print console logs
            if console_logs:
                print("7. Console logs:")
                for log in console_logs[-5:]:  # Last 5 logs
                    print(f"   {log}")
            
            print("\n📊 Modal investigation complete")
            
        except Exception as e:
            print(f"❌ Investigation error: {e}")
            await page.screenshot(path="siam_modal_error.png")
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(investigate_siam_modal())