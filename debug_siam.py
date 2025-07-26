#!/usr/bin/env python3
"""
Debug SIAM Issues
================

Find out exactly what's going wrong with SIAM.
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def debug_siam():
    print("🔍 DEBUGGING SIAM INSTITUTIONAL LOGIN")
    print("=" * 60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Step 1: Navigate to SIAM paper
            test_doi = "10.1137/S0097539795293172"
            siam_url = f"https://epubs.siam.org/doi/{test_doi}"
            
            print(f"Step 1: Navigating to {siam_url}")
            await page.goto(siam_url, timeout=60000)
            await page.wait_for_timeout(5000)
            
            # Take screenshot
            await page.screenshot(path="debug_siam_1_initial.png")
            print("  Screenshot: debug_siam_1_initial.png")
            
            # Step 2: Look for institutional access button
            print("\nStep 2: Looking for institutional access...")
            
            # Check what's actually on the page
            title = await page.title()
            print(f"  Page title: {title}")
            
            # List all visible links
            links = await page.query_selector_all('a')
            link_texts = []
            for link in links[:20]:
                text = await link.text_content()
                if text and text.strip():
                    link_texts.append(text.strip())
            print(f"  First 20 links: {link_texts}")
            
            # Try to find institutional access
            inst_selectors = [
                'a:has-text("Access via your Institution")',
                'a:has-text("Institution")',
                'a:has-text("institutional")',
                'a:has-text("Sign in")',
                'button:has-text("Sign in")',
                '[href*="institutional"]',
                '[href*="shibboleth"]'
            ]
            
            inst_button = None
            for selector in inst_selectors:
                try:
                    inst_button = await page.wait_for_selector(selector, timeout=3000)
                    if inst_button:
                        text = await inst_button.text_content()
                        print(f"  ✓ Found institutional button: '{text}' with {selector}")
                        break
                except:
                    continue
            
            if not inst_button:
                print("  ❌ No institutional access button found!")
                await page.screenshot(path="debug_siam_2_no_button.png")
                await browser.close()
                return
            
            # Step 3: Click institutional access
            print("\nStep 3: Clicking institutional access...")
            await inst_button.click()
            await page.wait_for_timeout(5000)
            
            current_url = page.url
            print(f"  New URL after click: {current_url}")
            
            await page.screenshot(path="debug_siam_3_after_click.png")
            print("  Screenshot: debug_siam_3_after_click.png")
            
            # Step 4: Look for institution search
            print("\nStep 4: Looking for institution search...")
            
            # Check page content
            page_content = await page.content()
            if 'shibboleth' in page_content.lower():
                print("  ✓ Page contains 'shibboleth'")
            if 'institution' in page_content.lower():
                print("  ✓ Page contains 'institution'")
            
            # Try multiple search selectors
            search_selectors = [
                'input#shibboleth_search',
                'input[id*="search"]',
                'input[placeholder*="institution"]',
                'input[type="text"]',
                'input[name*="search"]'
            ]
            
            search_input = None
            for selector in search_selectors:
                try:
                    search_input = await page.wait_for_selector(selector, timeout=5000)
                    if search_input:
                        placeholder = await search_input.get_attribute('placeholder')
                        print(f"  ✓ Found search input: {selector} (placeholder: {placeholder})")
                        break
                except:
                    continue
            
            if not search_input:
                print("  ❌ No search input found!")
                
                # List all inputs on the page
                inputs = await page.query_selector_all('input')
                print(f"  All inputs on page ({len(inputs)}):")
                for i, inp in enumerate(inputs[:10]):
                    inp_type = await inp.get_attribute('type')
                    inp_id = await inp.get_attribute('id')
                    inp_name = await inp.get_attribute('name')
                    inp_placeholder = await inp.get_attribute('placeholder')
                    print(f"    {i}: type={inp_type}, id={inp_id}, name={inp_name}, placeholder={inp_placeholder}")
                
                await browser.close()
                return
            
            # Step 5: Try to search for ETH
            print("\nStep 5: Searching for ETH Zurich...")
            await search_input.click()
            await search_input.fill("")
            await page.wait_for_timeout(1000)
            await search_input.type("ETH Zurich", delay=200)
            await page.wait_for_timeout(3000)
            
            await page.screenshot(path="debug_siam_4_search_typed.png")
            print("  Screenshot: debug_siam_4_search_typed.png")
            
            # Look for dropdown results
            print("\nStep 6: Looking for search results...")
            
            # Check for dropdown container
            dropdown_selectors = [
                '.ms-res-ctn',
                '.dropdown-menu',
                '.search-results',
                '[class*="result"]',
                '[class*="dropdown"]'
            ]
            
            dropdown = None
            for selector in dropdown_selectors:
                try:
                    dropdown = await page.wait_for_selector(selector, timeout=3000)
                    if dropdown:
                        print(f"  ✓ Found dropdown: {selector}")
                        break
                except:
                    continue
            
            if dropdown:
                # Look for ETH options
                eth_selectors = [
                    '.ms-res-item a:has-text("ETH Zurich")',
                    'a.sso-institution:has-text("ETH Zurich")',
                    'text="ETH Zurich"',
                    '[data-entityid*="ethz.ch"]'
                ]
                
                for selector in eth_selectors:
                    try:
                        eth_option = await page.wait_for_selector(selector, timeout=2000)
                        if eth_option:
                            print(f"  ✓ Found ETH option: {selector}")
                            await eth_option.click()
                            print("  ✓ Clicked ETH option")
                            await page.wait_for_timeout(5000)
                            break
                    except:
                        continue
            else:
                print("  ❌ No dropdown found!")
            
            final_url = page.url
            print(f"\nFinal URL: {final_url}")
            
            await page.screenshot(path="debug_siam_5_final.png")
            print("Screenshot: debug_siam_5_final.png")
            
        except Exception as e:
            print(f"❌ Error during debug: {e}")
            await page.screenshot(path="debug_siam_error.png")
        
        finally:
            print("\nClosing browser...")
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_siam())