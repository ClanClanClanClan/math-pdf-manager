#!/usr/bin/env python3
"""
Test IEEE Ultra Navigator
This tests the advanced PDF download solution with all bypass methods.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright
from src.publishers.institutional.base import ETHAuthenticator
from src.publishers.institutional.ieee_ultra_navigator import (
    IEEEUltraNavigator,
    create_ultra_browser_context,
)
from src.secure_credential_manager import get_credential_manager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_ieee_ultra():
    """Test the IEEE Ultra Navigator with all bypass methods."""
    
    # Test DOI
    test_doi = "10.1109/JPROC.2018.2820126"
    output_path = Path(f"ieee_ultra_{test_doi.replace('/', '_')}.pdf")
    
    print(f"\n{'='*70}")
    print(f"🚀 IEEE ULTRA NAVIGATOR TEST")
    print(f"{'='*70}")
    print(f"DOI: {test_doi}")
    print(f"Output: {output_path}")
    print()
    print("This test implements:")
    print("✅ Maximum browser stealth configuration")
    print("✅ JavaScript injection to override blocks")
    print("✅ Direct PDF URL construction")
    print("✅ Session transfer mechanism")
    print("✅ Cookie extraction and replay")
    print("✅ Forced navigation techniques")
    print()
    print("Starting test...")
    print()
    
    async with async_playwright() as p:
        # Create ultra-stealth browser
        print("🛡️  Creating ultra-stealth browser configuration...")
        browser, context = await create_ultra_browser_context(p)
        
        page = await context.new_page()
        
        # Apply additional stealth on page level
        await page.add_init_script("""
            // Additional page-level stealth
            
            // Override toString methods to look normal
            Object.defineProperty(Function.prototype, 'toString', {
                value: function() {
                    if (this === window.navigator.permissions.query) {
                        return 'function query() { [native code] }';
                    }
                    return Function.prototype.toString.call(this);
                }
            });
            
            // Add realistic window properties
            window.screen.orientation = {
                angle: 0,
                type: 'landscape-primary'
            };
            
            // Add battery API
            navigator.getBattery = () => Promise.resolve({
                charging: true,
                chargingTime: 0,
                dischargingTime: Infinity,
                level: 1
            });
            
            // Add connection API
            navigator.connection = {
                effectiveType: '4g',
                rtt: 50,
                downlink: 10,
                saveData: false
            };
            
            // Console log to verify
            console.log('Ultra-stealth mode activated');
        """)
        
        try:
            # Get credentials
            cm = get_credential_manager()
            username, password = cm.get_eth_credentials()
            
            # Create navigator instance
            navigator = IEEEUltraNavigator(page=page)
            
            # Create ETH authenticator
            eth_auth = ETHAuthenticator(page, username, password)
            
            # Navigate to paper
            url = f"https://doi.org/{test_doi}"
            print(f"🌐 Navigating to: {url}")
            
            success = await navigator.navigate_to_publication(url)
            if success:
                print(f"✅ Navigation successful")
                print(f"📍 Current URL: {page.url}")
            else:
                print(f"❌ Navigation failed")
                return
            
            # Check authentication status
            print(f"\n🔐 AUTHENTICATION")
            print("-" * 50)
            
            auth_state = await navigator.check_authentication_status()
            print(f"Current auth state: {auth_state.value}")
            
            if auth_state.value != "authenticated":
                print("Starting authentication flow...")
                
                # Initiate login
                if await navigator.initiate_login():
                    print("✅ Login initiated")
                else:
                    print("❌ Failed to initiate login")
                    return
                
                # Select institution
                if await navigator.select_institution("ETH Zurich"):
                    print("✅ Institution selected")
                else:
                    print("❌ Failed to select institution")
                    return
                
                # Wait for redirect to ETH
                await page.wait_for_timeout(8000)
                
                # Perform ETH login
                if 'ethz.ch' in page.url.lower():
                    print("📍 At ETH login page")
                    
                    if await eth_auth.perform_login():
                        print("✅ ETH login successful")
                    else:
                        print("❌ ETH login failed")
                        return
                    
                    # Wait for redirect back to IEEE
                    await page.wait_for_timeout(10000)
                    
                    if 'ieeexplore.ieee.org' in page.url:
                        print("✅ Redirected back to IEEE")
                    else:
                        print(f"❓ Unexpected URL: {page.url}")
                else:
                    print(f"❌ Not redirected to ETH. Current URL: {page.url}")
                    return
                
                # Verify authentication
                auth_state = await navigator.check_authentication_status()
                if auth_state.value == "authenticated":
                    print("🎉 AUTHENTICATION SUCCESSFUL!")
                else:
                    print("❌ Authentication verification failed")
                    return
            else:
                print("✅ Already authenticated")
            
            # Check for PDF button
            print(f"\n📄 PDF ACCESS")
            print("-" * 50)
            
            pdf_button = await page.query_selector('a[href*="/stamp/stamp.jsp"]')
            if pdf_button:
                href = await pdf_button.get_attribute('href')
                print(f"✅ PDF button found: {href}")
            else:
                print("❌ No PDF button found")
                
                # Look for any PDF-related elements
                pdf_elements = await page.query_selector_all('*:has-text("PDF"), *:has-text("Download")')
                print(f"Found {len(pdf_elements)} PDF-related elements")
                
                if not pdf_elements:
                    print("❌ No PDF access available")
                    return
            
            # Attempt PDF download with all methods
            print(f"\n🎯 ATTEMPTING PDF DOWNLOAD")
            print("-" * 50)
            print("This will try multiple bypass methods in sequence:")
            print("1. JavaScript injection override")
            print("2. Direct URL construction")
            print("3. Session transfer to clean context")
            print("4. Cookie extraction and replay")
            print("5. Forced navigation")
            print()
            
            success = await navigator.download_pdf(output_path)
            
            if success and output_path.exists():
                file_size = output_path.stat().st_size
                print(f"\n✅ SUCCESS! PDF downloaded")
                print(f"📁 File: {output_path}")
                print(f"📊 Size: {file_size:,} bytes")
                
                if file_size > 1000:  # At least 1KB
                    print(f"✅ File size looks valid")
                    
                    # Verify it's a PDF
                    with open(output_path, 'rb') as f:
                        header = f.read(4)
                        if header == b'%PDF':
                            print(f"✅ File is a valid PDF")
                        else:
                            print(f"❌ File doesn't appear to be a PDF")
                else:
                    print(f"❌ File size too small - might be an error page")
            else:
                print(f"\n❌ FAILED: Could not download PDF")
                print(f"All bypass methods were unsuccessful")
                
                # Final diagnostic
                print(f"\n🔍 FINAL DIAGNOSTIC")
                print("-" * 50)
                
                # Check current page state
                current_url = page.url
                current_title = await page.title()
                
                print(f"Current URL: {current_url}")
                print(f"Current title: {current_title}")
                
                # Check for error messages
                error_elements = await page.query_selector_all('*:has-text("error"), *:has-text("denied"), *:has-text("restricted")')
                if error_elements:
                    print(f"Found {len(error_elements)} error-related elements")
                    for elem in error_elements[:3]:
                        text = await elem.text_content()
                        print(f"  - {text[:100]}")
                
                # Check console for errors
                console_errors = []
                page.on("pageerror", lambda exc: console_errors.append(str(exc)))
                await page.wait_for_timeout(1000)
                
                if console_errors:
                    print(f"Console errors: {len(console_errors)}")
                    for error in console_errors[:3]:
                        print(f"  - {error[:100]}")
            
            print(f"\n⏸️  Browser staying open for 30 seconds for inspection...")
            await page.wait_for_timeout(30000)
            
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            await browser.close()
            print(f"\n{'='*70}")
            print(f"Test completed")
            print(f"{'='*70}")


if __name__ == "__main__":
    asyncio.run(test_ieee_ultra())