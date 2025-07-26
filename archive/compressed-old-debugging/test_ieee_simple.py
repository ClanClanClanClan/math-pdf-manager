#!/usr/bin/env python3
"""
Simple IEEE Test - Minimal steps to debug
"""

import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        page = await browser.new_page()
        
        print("1️⃣ Going to IEEE...")
        await page.goto("https://doi.org/10.1109/JPROC.2018.2820126")
        await page.wait_for_timeout(5000)
        
        # Accept cookies
        try:
            await page.click('button:has-text("Accept All")')
            await page.wait_for_timeout(1000)
        except:
            pass
        
        print("2️⃣ Click Institutional Sign In...")
        await page.click('a:has-text("Institutional Sign In")')
        await page.wait_for_timeout(2000)
        
        print("3️⃣ Click Access Through Your Institution button...")
        await page.click('button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn')
        await page.wait_for_timeout(3000)
        
        print("4️⃣ Type ETH Zurich in search...")
        # Find first text input in the modal
        modal = await page.query_selector('ngb-modal-window:has-text("Search for your Institution")')
        if modal:
            inputs = await modal.query_selector_all('input[type="text"]')
            if inputs:
                await inputs[0].fill("ETH Zurich")
                await page.wait_for_timeout(1000)
                
                print("5️⃣ Submit search...")
                # Try Enter key
                await page.keyboard.press('Enter')
                await page.wait_for_timeout(3000)
                
                print("6️⃣ Look for results...")
                # Take screenshot
                await page.screenshot(path="ieee_search_results.png")
                print("Screenshot saved to ieee_search_results.png")
                
                # Try to find any element with ETH
                eth_elements = await page.query_selector_all(':text("ETH")')
                print(f"Found {len(eth_elements)} elements with 'ETH'")
                
                # List all visible text
                all_text = await page.query_selector_all('a, button, li, div[role="option"]')
                print("\nVisible clickable elements:")
                for elem in all_text[:20]:
                    text = await elem.text_content()
                    if text and text.strip() and len(text.strip()) > 3:
                        print(f"  - {text.strip()[:60]}")
        
        print("\n🔍 Browser will close in 30 seconds...")
        await page.wait_for_timeout(30000)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test())