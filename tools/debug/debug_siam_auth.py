#!/usr/bin/env python3
"""Debug SIAM authentication flow"""

import asyncio
from playwright.async_api import async_playwright
import os

async def debug_siam_auth():
    """Debug SIAM authentication with visual browser"""
    
    async with async_playwright() as p:
        # Launch browser in visual mode
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Navigate to SIAM
        print("Navigating to SIAM...")
        await page.goto("https://epubs.siam.org/doi/10.1137/S0097539795293172")
        
        # Wait for manual interaction
        print("\nBrowser opened. Please:")
        print("1. Click 'Access via your Institution'")
        print("2. Search for and select 'ETH Zurich'")
        print("3. Complete ETH login")
        print("\nPress Enter when done...")
        input()
        
        # Check final state
        final_url = page.url
        print(f"\nFinal URL: {final_url}")
        
        # Extract cookies
        cookies = await context.cookies()
        print(f"\nFound {len(cookies)} cookies:")
        for cookie in cookies[:5]:  # First 5 cookies
            print(f"  {cookie['name']}: {cookie['value'][:20]}...")
        
        # Check if we can access the PDF
        pdf_url = "https://epubs.siam.org/doi/pdf/10.1137/S0097539795293172"
        print(f"\nTrying to access PDF: {pdf_url}")
        
        response = await page.goto(pdf_url)
        if response:
            print(f"Status: {response.status}")
            content_type = response.headers.get('content-type', '')
            print(f"Content-Type: {content_type}")
            
            if 'pdf' in content_type.lower():
                print("✅ SUCCESS: Can access PDF!")
            else:
                print("❌ Still blocked, likely need better cookie extraction")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_siam_auth())