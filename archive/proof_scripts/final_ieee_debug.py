#!/usr/bin/env python3
"""
Final IEEE Debug Test
====================

Complete analysis of the IEEE modal structure.
"""

import asyncio
from playwright.async_api import async_playwright

async def final_debug():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        )
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
            }
        )
        
        # Add script to remove webdriver property
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        """)
        
        page = await context.new_page()
        
        print("Going to IEEE...")
        await page.goto("https://doi.org/10.1109/JPROC.2018.2820126")
        await page.wait_for_timeout(5000)
        
        # Accept cookies
        try:
            await page.click('button:has-text("Accept All")')
            await page.wait_for_timeout(1000)
        except:
            pass
        
        print("Clicking Institutional Sign In...")
        await page.click('a:has-text("Institutional Sign In")')
        await page.wait_for_timeout(2000)
        
        # Wait for modal
        modal = await page.query_selector('ngb-modal-window')
        if modal:
            print("✓ Modal found")
            
            # Wait and take screenshots periodically
            for i in range(10):  # Wait up to 20 seconds
                await page.wait_for_timeout(2000)
                await page.screenshot(path=f"ieee_modal_{i:02d}.png")
                
                # Check modal content
                modal_text = await modal.text_content()
                print(f"[{i*2}s] Modal text: {modal_text[:100]}...")
                
                # Look for buttons
                buttons = await modal.query_selector_all('button')
                print(f"[{i*2}s] Found {len(buttons)} buttons")
                
                if buttons:
                    for j, btn in enumerate(buttons):
                        text = await btn.text_content()
                        visible = await btn.is_visible()
                        enabled = await btn.is_enabled() 
                        classes = await btn.get_attribute('class') or ''
                        print(f"  Button {j}: '{text}' visible={visible} enabled={enabled}")
                        print(f"    classes: {classes[:80]}...")
                        
                        # If this looks like the right button, try clicking it
                        if visible and enabled and text and ('access' in text.lower() or 'institution' in text.lower()):
                            print(f"  🎯 This looks like the right button: '{text}'")
                            print("  Would click this button if this were not debug mode")
                
                # Check if loading is complete
                if 'Loading' not in modal_text:
                    print("✓ Loading appears to be complete")
                    break
        
        print("\n=== FINAL STATE ===")
        modal_html = await modal.innerHTML()
        print(f"Final modal HTML: {modal_html[:500]}...")
        
        print("\nBrowser staying open for 60 seconds for manual inspection...")
        await page.wait_for_timeout(60000)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(final_debug())