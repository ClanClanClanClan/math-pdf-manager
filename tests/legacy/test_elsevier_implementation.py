#!/usr/bin/env python3
"""
Test Elsevier Implementation

Test the new Elsevier navigator with the working DOI found during research.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright
from src.publishers.institutional.base import ETHAuthenticator
from src.publishers.institutional.publishers.elsevier_navigator import (
    ELSEVIER_CONFIG,
    ElsevierNavigator,
)
from src.secure_credential_manager import get_credential_manager


async def test_elsevier_implementation():
    """Test Elsevier implementation with working DOI."""
    
    # Use the working DOI found during research
    working_doi = '10.1016/j.jmb.2021.166861'  # Journal of Molecular Biology
    
    print(f"\n{'='*70}")
    print(f"🧪 TESTING ELSEVIER IMPLEMENTATION")
    print(f"{'='*70}")
    print(f"Testing with: {working_doi}")
    print(f"Expected: DNA mechanics and its biological impact")
    
    async with async_playwright() as p:
        browser = await p.firefox.launch(
            headless=False,  # Visible for debugging
            firefox_user_prefs={
                "dom.webdriver.enabled": False,
                "useAutomationExtension": False,
            }
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            accept_downloads=True
        )
        page = await context.new_page()
        
        # Get credentials
        cm = get_credential_manager()
        username, password = cm.get_eth_credentials()
        
        try:
            # Create navigator first
            navigator = ElsevierNavigator(page, ELSEVIER_CONFIG)
            navigator.eth_auth = ETHAuthenticator(page, username, password)
            
            print(f"\n🌐 Step 1: Navigate to paper")
            navigation_success = await navigator.navigate_to_paper(working_doi)
            
            if not navigation_success:
                print(f"   ❌ Failed to navigate to ScienceDirect")
                return False
            
            current_url = page.url
            title = await page.title()
            print(f"   Current URL: {current_url}")
            print(f"   Title: {title[:60]}...")
            print(f"   ✅ Successfully at ScienceDirect")
            
            print(f"\n🔐 Step 2: Navigate to institutional login")
            login_success = await navigator.navigate_to_login()
            
            if not login_success:
                print(f"   ❌ Failed to navigate to login")
                
                # Debug: Check what's available on the page
                print(f"\n🔍 DEBUG: Looking for sign-in elements...")
                
                all_links = await page.query_selector_all('a, button')
                signin_elements = []
                
                for element in all_links[:20]:
                    try:
                        text = await element.inner_text()
                        href = await element.get_attribute('href')
                        
                        if text and any(term in text.lower() for term in ['sign', 'login', 'access', 'institutional', 'organization']):
                            signin_elements.append({
                                'text': text.strip()[:50],
                                'href': href[:80] if href else None,
                                'tag': await element.evaluate('el => el.tagName')
                            })
                    except:
                        continue
                
                if signin_elements:
                    print(f"   Found {len(signin_elements)} potential sign-in elements:")
                    for elem in signin_elements[:5]:
                        print(f"      • {elem['tag']}: '{elem['text']}' → {elem['href']}")
                else:
                    print(f"   No sign-in elements found")
                
                return False
            
            print(f"   ✅ Successfully navigated to login")
            
            print(f"\n🏛️  Step 3: Select ETH institution")
            eth_success = await navigator.select_eth_institution()
            
            if not eth_success:
                print(f"   ❌ Failed to select ETH")
                print(f"   Current URL: {page.url}")
                return False
            
            print(f"   ✅ Successfully selected ETH")
            
            print(f"\n🔑 Step 4: ETH authentication")
            auth_success = await navigator.eth_auth.perform_login()
            
            if not auth_success:
                print(f"   ❌ ETH authentication failed")
                return False
            
            print(f"   ✅ ETH authentication successful")
            
            print(f"\n🔄 Step 5: Post-auth redirect")
            redirect_success = await navigator.navigate_after_auth()
            
            if not redirect_success:
                print(f"   ❌ Post-auth redirect failed")
                print(f"   Current URL: {page.url}")
                return False
            
            print(f"   ✅ Post-auth successful - back at ScienceDirect with access")
            
            print(f"\n📄 Step 6: PDF download")
            downloads_dir = Path("elsevier_downloads")
            downloads_dir.mkdir(exist_ok=True)
            
            pdf_path = await navigator.download_pdf(downloads_dir)
            
            if pdf_path and pdf_path.exists():
                file_size = pdf_path.stat().st_size
                print(f"   ✅ PDF downloaded successfully!")
                print(f"   📁 File: {pdf_path}")
                print(f"   📊 Size: {file_size:,} bytes")
                
                if file_size > 1000:
                    print(f"\n🎉 ELSEVIER IMPLEMENTATION SUCCESS!")
                    print(f"   • Authentication: Working")
                    print(f"   • PDF Download: Working")
                    print(f"   • File size: Valid")
                    return True
                else:
                    print(f"\n⚠️  Downloaded file too small - may be error page")
                    return False
            else:
                print(f"   ❌ PDF download failed")
                
                # Debug: Check what download options are available
                print(f"\n🔍 DEBUG: Looking for download elements...")
                
                download_elements = await page.query_selector_all('a, button')
                pdf_elements = []
                
                for element in download_elements:
                    try:
                        text = await element.inner_text()
                        href = await element.get_attribute('href')
                        
                        if text and any(term in text.lower() for term in ['pdf', 'download', 'full text']):
                            pdf_elements.append({
                                'text': text.strip()[:50],
                                'href': href[:80] if href else None
                            })
                    except:
                        continue
                
                if pdf_elements:
                    print(f"   Found {len(pdf_elements)} potential download elements:")
                    for elem in pdf_elements[:5]:
                        print(f"      • '{elem['text']}' → {elem['href']}")
                else:
                    print(f"   No download elements found")
                
                return False
                
        except Exception as e:
            print(f"❌ Test error: {e}")
            return False
        
        finally:
            await browser.close()


async def main():
    """Run Elsevier test."""
    success = await test_elsevier_implementation()
    
    if success:
        print(f"\n{'='*70}")
        print(f"✅ ELSEVIER NAVIGATOR VALIDATION SUCCESSFUL")
        print(f"{'='*70}")
        print(f"• Third publisher successfully implemented")
        print(f"• Modular architecture validated with Elsevier")
        print(f"• Ready for production testing")
    else:
        print(f"\n{'='*70}")
        print(f"❌ ELSEVIER NAVIGATOR NEEDS DEBUGGING")
        print(f"{'='*70}")
        print(f"• Implementation requires refinement")
        print(f"• Check selectors and authentication flow")
        print(f"• May need alternative approach")


if __name__ == "__main__":
    asyncio.run(main())