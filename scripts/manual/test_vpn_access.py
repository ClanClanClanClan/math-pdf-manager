#!/usr/bin/env python3
"""
TEST VPN ACCESS
===============

Quick test to verify if VPN connection enables Wiley PDF access.
"""

import asyncio
import subprocess
from playwright.async_api import async_playwright

async def test_wiley_access():
    """Test Wiley PDF access with current connection"""
    
    print("🔍 TESTING WILEY PDF ACCESS")
    print("=" * 50)
    
    # Check VPN status
    try:
        result = subprocess.run(["/opt/cisco/secureclient/bin/vpn", "status"], 
                              capture_output=True, text=True, timeout=10)
        
        if "state: Connected" in result.stdout:
            print("✅ VPN connected")
            vpn_connected = True
        else:
            print("❌ VPN not connected")
            vpn_connected = False
    except:
        print("❌ VPN status check failed")
        vpn_connected = False
    
    # Test direct PDF access
    test_url = "https://onlinelibrary.wiley.com/doi/pdf/10.1002/anie.202004934"
    
    print(f"\nTesting PDF URL: {test_url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            response = await page.goto(test_url, timeout=30000)
            
            status = response.status if response else "No response"
            content_type = response.headers.get('content-type', '') if response else ""
            
            print(f"Response status: {status}")
            print(f"Content-Type: {content_type}")
            
            if status == 200 and 'pdf' in content_type.lower():
                print("🎉 SUCCESS: PDF is accessible!")
                
                # Get PDF size
                pdf_buffer = await response.body()
                size_mb = len(pdf_buffer) / (1024 * 1024)
                print(f"PDF size: {size_mb:.2f} MB")
                
                # Save test PDF
                with open("vpn_test.pdf", "wb") as f:
                    f.write(pdf_buffer)
                
                print("✅ Test PDF saved as 'vpn_test.pdf'")
                success = True
                
            elif status == 403:
                print("❌ FORBIDDEN: Need VPN connection or institutional access")
                success = False
            else:
                print(f"❌ FAILED: Unexpected response")
                success = False
            
            await browser.close()
            return success, vpn_connected
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            await browser.close()
            return False, vpn_connected

async def main():
    """Main test"""
    
    print("🧪 VPN ACCESS TEST")
    print("=" * 60)
    print("Testing if current network setup can access Wiley PDFs")
    print("=" * 60)
    
    success, vpn_connected = await test_wiley_access()
    
    print(f"\n{'='*20} RESULTS {'='*20}")
    print(f"VPN Connected: {'✅' if vpn_connected else '❌'}")
    print(f"PDF Access: {'✅' if success else '❌'}")
    
    if success:
        print(f"\n🎉 READY FOR WILEY DOWNLOADS!")
        print(f"Your network setup can access subscription content")
        print(f"Run the full downloader now")
    else:
        if not vpn_connected:
            print(f"\n💡 NEXT STEPS:")
            print(f"1. Connect to ETH VPN using Cisco Secure Client")
            print(f"2. Try connecting to: vpn.ethz.ch or sslvpn.ethz.ch")
            print(f"3. Run this test again to verify access")
        else:
            print(f"\n💡 VPN connected but PDF access still blocked")
            print(f"May need different VPN server or network configuration")

if __name__ == "__main__":
    asyncio.run(main())