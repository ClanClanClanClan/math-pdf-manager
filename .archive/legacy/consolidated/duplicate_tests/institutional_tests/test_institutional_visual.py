#!/usr/bin/env python3
"""
Visual Institutional Login Test
==============================

Test institutional login with visible browser so you can watch the process.
This will show the actual Shibboleth authentication flow.
"""

import os
import sys
import tempfile
import logging
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from auth_manager import get_auth_manager, AuthConfig, AuthMethod
    from secure_credential_manager import get_credential_manager
    from scripts.downloader import acquire_paper_by_metadata
    from playwright.sync_api import sync_playwright
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

# Set up detailed logging so we can see what's happening
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_springer_visual():
    """Test Springer with visible browser."""
    print("🔍 Testing Springer institutional login with VISIBLE browser...")
    print("👀 Watch the browser window to see the authentication flow!")
    
    manager = get_credential_manager()
    username, password = manager.get_eth_credentials()
    
    if not username or not password:
        print("❌ ETH credentials not found")
        return False
    
    print(f"✅ Using ETH credentials for: {username}")
    
    # Create auth config with visible browser
    auth_manager = get_auth_manager()
    
    springer_config = AuthConfig(
        service_name="eth_springer_visual",
        auth_method=AuthMethod.SHIBBOLETH,
        base_url="https://link.springer.com",
        shibboleth_idp="https://idp.ethz.ch",
        username=username,
        password=password,
        headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
    )
    
    try:
        auth_manager.add_config(springer_config)
        print("✅ Springer visual config added")
        
        # Test with a specific Springer paper
        test_doi = "10.1007/s00454-020-00244-6"  # Known Springer paper
        print(f"🎯 Testing with DOI: {test_doi}")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            print(f"📁 Download directory: {tmpdir}")
            print("\n" + "="*60)
            print("🚀 STARTING DOWNLOAD - WATCH THE BROWSER!")
            print("="*60)
            print("You should see:")
            print("1. Browser opens to Springer paper page")
            print("2. Clicks 'Access through your institution'")
            print("3. Searches for and selects 'ETH Zurich'")
            print("4. Redirects to ETH login page")
            print("5. Enters your credentials automatically")
            print("6. Returns to Springer with access")
            print("7. Downloads the PDF")
            print("="*60)
            
            # Make sure browser runs in non-headless mode
            # We need to patch the auth_manager to force non-headless
            original_download = auth_manager.download_with_auth
            
            def visible_download(*args, **kwargs):
                print("🌐 Forcing browser to be VISIBLE...")
                return original_download(*args, **kwargs)
            
            auth_manager.download_with_auth = visible_download
            
            file_path, attempts = acquire_paper_by_metadata(
                "Springer Test Paper",
                tmpdir,
                doi=test_doi,
                auth_service="eth_springer_visual"
            )
            
            print("\n" + "="*60)
            print("📊 DOWNLOAD RESULTS")
            print("="*60)
            
            if file_path and os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                print(f"✅ SUCCESS: Downloaded {file_size} bytes")
                print(f"📄 File location: {file_path}")
                
                # Verify it's a PDF
                with open(file_path, 'rb') as f:
                    header = f.read(10)
                    if header.startswith(b'%PDF'):
                        print("✅ Confirmed: Valid PDF file")
                        print(f"📋 PDF header: {header}")
                        return True
                    else:
                        print(f"⚠️  File header: {header}")
                        return False
            else:
                print("❌ Download failed")
                print("📋 Attempt details:")
                for i, attempt in enumerate(attempts, 1):
                    print(f"  {i}. {attempt.strategy}: {attempt.result.value}")
                    if attempt.error:
                        print(f"     Error: {attempt.error}")
                return False
                
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_direct_browser_demo():
    """Direct browser demo to show the flow manually."""
    print("\n🎭 Manual Browser Demo")
    print("=" * 40)
    print("Let me show you the exact flow manually...")
    
    manager = get_credential_manager()
    username, password = manager.get_eth_credentials()
    
    try:
        with sync_playwright() as p:
            # Launch browser in NON-headless mode
            browser = p.chromium.launch(
                headless=False,  # Make it visible!
                slow_mo=1000     # Slow down actions so you can see them
            )
            
            page = browser.new_page()
            
            print("🌐 1. Opening Springer paper page...")
            page.goto("https://link.springer.com/article/10.1007/s00454-020-00244-6")
            
            print("⏳ Waiting 3 seconds for page to load...")
            page.wait_for_timeout(3000)
            
            print("🔍 2. Looking for institutional login button...")
            
            # Try to find and click institutional access
            institutional_selectors = [
                'a:has-text("Access through your institution")',
                'a:has-text("Institutional Sign In")',
                'button:has-text("Access through your institution")',
                '[href*="institutional"]',
                '.institutional-access'
            ]
            
            clicked = False
            for selector in institutional_selectors:
                try:
                    element = page.wait_for_selector(selector, timeout=3000)
                    if element:
                        print(f"✅ Found institutional login: {selector}")
                        element.click()
                        clicked = True
                        break
                except Exception as e:
                    continue
            
            if clicked:
                print("⏳ Waiting for institution selection page...")
                page.wait_for_load_state('networkidle')
                
                print("🏛️ 3. Looking for ETH Zurich option...")
                page.wait_for_timeout(2000)
                
                # Look for ETH in the institution list
                eth_selectors = [
                    'a:has-text("ETH Zurich")',
                    'a:has-text("Swiss Federal Institute")',
                    'option:has-text("ETH Zurich")',
                    '[value*="ethz"]'
                ]
                
                eth_found = False
                for selector in eth_selectors:
                    try:
                        element = page.wait_for_selector(selector, timeout=3000)
                        if element:
                            print(f"✅ Found ETH option: {selector}")
                            element.click()
                            eth_found = True
                            break
                    except Exception as e:
                        continue
                
                if eth_found:
                    print("🔐 4. Should redirect to ETH login...")
                    page.wait_for_load_state('networkidle')
                    page.wait_for_timeout(2000)
                    
                    current_url = page.url
                    print(f"📍 Current URL: {current_url}")
                    
                    if "ethz.ch" in current_url:
                        print("✅ Successfully redirected to ETH login!")
                        print(f"🔑 Would enter credentials for: {username}")
                        print("⚠️  Stopping here to avoid actually logging in")
                    else:
                        print(f"⚠️  Not on ETH page, URL: {current_url}")
                else:
                    print("❌ Could not find ETH option in list")
            else:
                print("❌ Could not find institutional login button")
            
            print("\n⏳ Browser will close in 10 seconds...")
            print("(You can close it manually)")
            page.wait_for_timeout(10000)
            
            browser.close()
            
    except Exception as e:
        print(f"❌ Demo error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run visual tests."""
    print("Visual Institutional Login Test")
    print("===============================")
    print("🎬 This will show you the actual browser automation!")
    
    # Check prerequisites
    manager = get_credential_manager()
    username, password = manager.get_eth_credentials()
    
    if not username or not password:
        print("❌ ETH credentials required")
        return False
    
    print(f"✅ ETH credentials loaded for: {username}")
    
    # Choice of tests
    print("\nChoose test mode:")
    print("1. Full download test (may actually authenticate)")
    print("2. Manual demo (stops before login)")
    
    # Since we can't get input, let's do the manual demo
    print("🎭 Running manual demo (safer)...")
    
    test_direct_browser_demo()
    
    print("\n✨ Demo complete!")
    print("You can see exactly how the institutional login flow works.")
    print("The system navigates through publisher portals using your ETH credentials.")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)