#!/usr/bin/env python3
"""
Simple IEEE Bypass Test
Assumes user has already authenticated manually, then tests PDF download methods.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright


async def test_simple_bypass():
    """Simple test - navigate to paper and try to bypass PDF restrictions."""
    
    test_doi = "10.1109/JPROC.2018.2820126"
    
    print("\n" + "="*70)
    print("SIMPLE IEEE BYPASS TEST")
    print("="*70)
    print(f"DOI: {test_doi}")
    print("\nThis test will:")
    print("1. Navigate to the paper")
    print("2. Wait for you to manually authenticate if needed")
    print("3. Then test PDF access bypass methods")
    print()
    
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Apply stealth
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        # Navigate to paper
        url = f"https://doi.org/{test_doi}"
        print(f"Navigating to: {url}")
        await page.goto(url)
        await page.wait_for_timeout(3000)
        
        print(f"Current URL: {page.url}")
        
        # Extract arnumber
        arnumber = None
        if '/document/' in page.url:
            arnumber = page.url.split('/document/')[-1].strip('/')
            print(f"Arnumber: {arnumber}")
        
        print("\n" + "-"*50)
        print("Waiting 15 seconds for page to load...")
        print("(In a real scenario, user would authenticate manually here)")
        print("-"*50)
        
        await page.wait_for_timeout(15000)
        
        # Check for PDF button
        pdf_button = await page.query_selector('a[href*="/stamp/stamp.jsp"]')
        if pdf_button:
            print("✅ PDF button found")
            href = await pdf_button.get_attribute('href')
            print(f"PDF href: {href}")
        else:
            print("❌ No PDF button found")
            return
        
        print("\nTESTING BYPASS METHODS:")
        print("-"*50)
        
        # Method 1: Remove event listeners and click
        print("\nMethod 1: JavaScript override")
        await page.evaluate("""
            () => {
                const pdfButton = document.querySelector('a[href*="/stamp/stamp.jsp"]');
                if (pdfButton) {
                    // Clone to remove listeners
                    const newButton = pdfButton.cloneNode(true);
                    pdfButton.parentNode.replaceChild(newButton, pdfButton);
                    
                    // Clear handlers
                    newButton.onclick = null;
                    newButton.onmousedown = null;
                    
                    // Override preventDefault
                    const originalPreventDefault = Event.prototype.preventDefault;
                    Event.prototype.preventDefault = function() {
                        if (this.target && this.target.href && this.target.href.includes('/stamp/stamp.jsp')) {
                            return;
                        }
                        return originalPreventDefault.call(this);
                    };
                }
            }
        """)
        
        # Try clicking
        pdf_button = await page.query_selector('a[href*="/stamp/stamp.jsp"]')
        before_url = page.url
        await pdf_button.click()
        await page.wait_for_timeout(5000)
        after_url = page.url
        
        if after_url != before_url:
            print(f"✅ Navigation occurred: {after_url}")
            if '/stamp/stamp.jsp' in after_url:
                print("🎉 SUCCESS! Reached PDF viewer")
        else:
            print("❌ No navigation - trying next method")
            
            # Method 2: Force navigation
            print("\nMethod 2: Force navigation")
            pdf_url = f"https://ieeexplore.ieee.org/stamp/stamp.jsp?arnumber={arnumber}"
            await page.evaluate(f"window.location.href = '{pdf_url}'")
            await page.wait_for_timeout(5000)
            
            if '/stamp/stamp.jsp' in page.url:
                print(f"✅ Forced navigation worked: {page.url}")
            else:
                print(f"❌ Still blocked. Current URL: {page.url}")
        
        print("\nTest complete. Browser will stay open for 30 seconds...")
        await page.wait_for_timeout(30000)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(test_simple_bypass())