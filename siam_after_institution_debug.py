#!/usr/bin/env python3
"""
Debug what happens after clicking "Access via your Institution"
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def debug_after_institution():
    print("🔍 DEBUGGING: What happens after 'Access via your Institution'?")
    
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
            
            # Force click "Access via your Institution"
            print("3. Force clicking 'Access via your Institution'...")
            inst_link = await page.wait_for_selector('a:has-text("Access via your Institution")', timeout=15000)
            await inst_link.click(force=True)
            await page.wait_for_timeout(8000)
            
            # Take screenshot of what we get
            await page.screenshot(path="siam_after_institution_click.png")
            print("   Screenshot: siam_after_institution_click.png")
            
            # Check current URL
            current_url = page.url
            print(f"   Current URL: {current_url}")
            
            # Check page title
            page_title = await page.title()
            print(f"   Page title: '{page_title}'")
            
            # Check page content for any clues
            page_content = await page.content()
            
            # Look for different possible selectors
            print("4. Looking for authentication options...")
            
            selectors_to_check = [
                'input#shibboleth_search',
                'input[id*="search"]',
                'input[placeholder*="institution"]',
                'input[placeholder*="search"]',
                'input[type="text"]',
                'form input',
                '.search-input',
                '#institution-search',
                '[data-testid*="search"]'
            ]
            
            for selector in selectors_to_check:
                try:
                    element = await page.wait_for_selector(selector, timeout=2000)
                    if element:
                        placeholder = await element.get_attribute('placeholder')
                        input_id = await element.get_attribute('id')
                        input_name = await element.get_attribute('name')
                        print(f"   ✓ Found input: {selector}")
                        print(f"     ID: {input_id}, Name: {input_name}, Placeholder: {placeholder}")
                except:
                    continue
            
            # Look for any forms
            print("5. Checking for forms...")
            forms = await page.query_selector_all('form')
            print(f"   Found {len(forms)} forms")
            
            for i, form in enumerate(forms):
                action = await form.get_attribute('action')
                method = await form.get_attribute('method')
                print(f"   Form {i+1}: action='{action}', method='{method}'")
                
                # Check inputs in each form
                inputs = await form.query_selector_all('input')
                for j, inp in enumerate(inputs):
                    inp_type = await inp.get_attribute('type')
                    inp_id = await inp.get_attribute('id')
                    inp_name = await inp.get_attribute('name')
                    inp_placeholder = await inp.get_attribute('placeholder')
                    print(f"     Input {j+1}: type={inp_type}, id={inp_id}, name={inp_name}, placeholder={inp_placeholder}")
            
            # Check for any text containing "shibboleth", "institution", "search"
            if 'shibboleth' in page_content.lower():
                print("   ✓ Page contains 'shibboleth'")
            if 'institution' in page_content.lower():
                print("   ✓ Page contains 'institution'")
            if 'search' in page_content.lower():
                print("   ✓ Page contains 'search'")
            
            # List all visible text on the page
            print("6. Getting all visible text...")
            visible_text = await page.evaluate('''
                Array.from(document.body.querySelectorAll('*'))
                  .filter(el => el.offsetParent !== null && el.innerText && el.innerText.trim())
                  .map(el => el.innerText.trim())
                  .slice(0, 20)
            ''')
            
            print("   Visible text elements:")
            for i, text in enumerate(visible_text[:10]):
                if len(text) < 100:  # Don't print very long text
                    print(f"     {i+1}. '{text}'")
            
            print("\n📊 Debug complete - check screenshot for visual confirmation")
            
        except Exception as e:
            print(f"❌ Debug error: {e}")
            await page.screenshot(path="siam_debug_error.png")
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_after_institution())