#!/usr/bin/env python3
"""
VERIFY ETH ACCESS
=================

Quick test to verify if ETH VPN/network access is working for Wiley.
"""

import asyncio
from playwright.async_api import async_playwright

async def test_eth_access():
    """Test if we can access Wiley PDFs with current network"""
    
    print("🔍 TESTING ETH NETWORK ACCESS TO WILEY")
    print("=" * 60)
    
    test_url = "https://onlinelibrary.wiley.com/doi/pdf/10.1002/anie.202004934"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        print(f"Testing direct PDF access: {test_url}")
        
        try:
            response = await page.goto(test_url, timeout=30000)
            status = response.status if response else "No response"
            content_type = response.headers.get('content-type', '') if response else ""
            
            print(f"Status: {status}")
            print(f"Content-Type: {content_type}")
            
            if status == 200 and 'pdf' in content_type.lower():
                print("🎉 SUCCESS: PDF accessible!")
                print("✅ ETH network access is working")
                
                # Try to get the PDF
                pdf_buffer = await response.body()
                if len(pdf_buffer) > 1000:
                    print(f"📄 PDF size: {len(pdf_buffer)} bytes")
                    
                    # Save it
                    with open("eth_test.pdf", "wb") as f:
                        f.write(pdf_buffer)
                    
                    print("✅ PDF saved as eth_test.pdf")
                    result = True
                else:
                    print("❌ PDF too small")
                    result = False
                    
            elif status == 403:
                print("❌ FORBIDDEN: ETH network access required")
                print("💡 Please connect to ETH VPN first")
                result = False
            else:
                print(f"❌ FAILED: Unexpected response")
                result = False
            
            await page.wait_for_timeout(5000)
            await browser.close()
            return result
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            await browser.close()
            return False

if __name__ == "__main__":
    success = asyncio.run(test_eth_access())
    if success:
        print("\n🎯 Ready to proceed with full Wiley downloads!")
    else:
        print("\n⚠️ ETH VPN connection needed first")