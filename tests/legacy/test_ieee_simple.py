#!/usr/bin/env python3
"""
Simple IEEE Access Test - One paper, detailed analysis
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright


async def test_simple_ieee_access():
    """Test a simple IEEE paper access to confirm the issue."""
    
    # Try an IEEE Access paper - these are usually open access
    test_doi = "10.1109/ACCESS.2020.2982225"
    
    print(f"\n🧪 SIMPLE IEEE ACCESS TEST")
    print(f"DOI: {test_doi}")
    print(f"Paper: IEEE Access (Open Access journal)")
    print("-" * 60)
    
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Navigate directly to the paper
            url = f"https://doi.org/{test_doi}"
            print(f"🌐 Navigating to: {url}")
            
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(3000)
            
            current_url = page.url
            print(f"📍 Current URL: {current_url}")
            
            # Look for PDF access immediately (no login needed for open access)
            pdf_button = await page.query_selector('a[href*="/stamp/stamp.jsp"]')
            if pdf_button:
                href = await pdf_button.get_attribute('href')
                print(f"📄 PDF button found: {href}")
                
                # Test clicking the PDF button
                print("🖱️  Clicking PDF button...")
                await pdf_button.click()
                await page.wait_for_timeout(5000)
                
                final_url = page.url
                print(f"📍 After click URL: {final_url}")
                
                if '/stamp/stamp.jsp' in final_url:
                    print("🎉 SUCCESS: PDF opened directly!")
                    
                    # Check if we can see a PDF viewer or download option
                    download_btn = await page.query_selector('button[title*="Download"], cr-icon-button#download')
                    if download_btn:
                        print("💾 Download button found in PDF viewer!")
                    else:
                        print("💾 No explicit download button, but PDF is accessible")
                        
                    return True
                    
                elif final_url == current_url:
                    print("❌ PDF click failed - no navigation occurred")
                    return False
                else:
                    print(f"⚠️  PDF click redirected to: {final_url}")
                    return False
                    
            else:
                print("❌ No PDF button found")
                
                # Check if there's a different access pattern
                open_access_indicators = [
                    "Open Access",
                    "Download PDF",
                    "Full Text PDF",
                    "View PDF"
                ]
                
                for indicator in open_access_indicators:
                    elements = await page.query_selector_all(f'*:has-text("{indicator}")')
                    if elements:
                        print(f"✅ Found access indicator: '{indicator}'")
                        
                return False
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
            
        finally:
            print(f"\n⏸️  Browser staying open for 30 seconds for manual inspection...")
            await page.wait_for_timeout(30000)
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_simple_ieee_access())
    if result:
        print("\n🎉 CONCLUSION: IEEE PDF access works for this paper!")
    else:
        print("\n❌ CONCLUSION: IEEE PDF access issue confirmed.")