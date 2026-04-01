#!/usr/bin/env python3
"""
Test complete Springer institutional access flow
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright
from src.publishers.institutional.publishers.springer_navigator import (
    SPRINGER_CONFIG,
    SpringerNavigator,
)
from src.secure_credential_manager import get_credential_manager


async def test_springer_flow():
    """Test the complete Springer authentication flow."""
    
    test_doi = "10.1007/s00211-021-01234-3"
    print(f"🧪 Testing Springer complete flow with DOI: {test_doi}")
    
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        try:
            # Get credentials
            cm = get_credential_manager()
            username, password = cm.get_eth_credentials()
            
            # Navigate to the paper
            url = f"https://doi.org/{test_doi}"
            print(f"🌐 Navigating to: {url}")
            await page.goto(url, wait_until='networkidle', timeout=30000)
            
            # Create Springer navigator
            navigator = SpringerNavigator(page, SPRINGER_CONFIG)
            
            # Set up ETH authenticator
            from src.publishers.institutional.base import ETHAuthenticator
            navigator.eth_auth = ETHAuthenticator(page, username, password)
            
            print(f"📍 Starting page: {page.url}")
            
            # Step 1: Navigate to login
            print("\n🔐 Step 1: Navigate to institutional login...")
            login_success = await navigator.navigate_to_login()
            
            if not login_success:
                print("❌ Failed to navigate to login")
                await page.screenshot(path="springer_login_failed.png")
                return
            
            print("✅ Successfully navigated to WAYF page")
            print(f"📍 WAYF page: {page.url}")
            
            # Step 2: Select ETH institution
            print("\n🏛️  Step 2: Select ETH Zurich...")
            eth_success = await navigator.select_eth_institution()
            
            if not eth_success:
                print("❌ Failed to select ETH")
                await page.screenshot(path="springer_eth_failed.png")
                return
            
            print("✅ Successfully selected ETH, at ETH login")
            print(f"📍 ETH login page: {page.url}")
            
            # Step 3: ETH authentication
            print("\n🔑 Step 3: ETH authentication...")
            auth_success = await navigator.eth_auth.perform_login()
            
            if not auth_success:
                print("❌ ETH authentication failed")
                await page.screenshot(path="springer_auth_failed.png")
                return
            
            print("✅ ETH authentication successful")
            
            # Step 4: Handle post-auth redirect
            print("\n🔄 Step 4: Post-auth redirect...")
            redirect_success = await navigator.navigate_after_auth()
            
            if not redirect_success:
                print("❌ Post-auth redirect failed")
                await page.screenshot(path="springer_redirect_failed.png")
                return
            
            print("✅ Successfully returned to Springer")
            print(f"📍 Final page: {page.url}")
            
            # Step 5: Test PDF download
            print("\n📄 Step 5: Test PDF download...")
            downloads_dir = Path("downloads")
            downloads_dir.mkdir(exist_ok=True)
            
            pdf_path = await navigator.download_pdf(downloads_dir)
            
            if pdf_path:
                print(f"🎉 SUCCESS! PDF downloaded to: {pdf_path}")
                file_size = pdf_path.stat().st_size
                print(f"📊 File size: {file_size:,} bytes")
            else:
                print("❌ PDF download failed")
                await page.screenshot(path="springer_download_failed.png")
                return
            
            print(f"\n✅ COMPLETE SUCCESS - Springer institutional access working!")
            
        except Exception as e:
            print(f"❌ Error during test: {e}")
            await page.screenshot(path="springer_error.png")
            
        finally:
            input("Press Enter to close browser...")
            await browser.close()


if __name__ == "__main__":
    asyncio.run(test_springer_flow())