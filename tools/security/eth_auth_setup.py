#!/usr/bin/env python3
"""
ETH Zurich Authentication Setup
===============================

Interactive setup for ETH institutional access to academic publishers.
Handles real-world authentication flows for major publishers.
"""

import os
import getpass
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from urllib.parse import urlparse

try:
    from playwright.sync_api import sync_playwright, Page, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

from .auth_manager import get_auth_manager, AuthConfig, AuthMethod

logger = logging.getLogger("eth_auth_setup")

# ETH Zurich specific configuration
ETH_IDP_BASE = "https://idp.ethz.ch"
ETH_WAYF_URLS = {
    # Publisher-specific "via institution" URLs that lead to ETH
    "ieee": "https://ieeexplore.ieee.org/servlet/wayf.jsp",
    "acm": "https://dl.acm.org/action/ssostart",
    "springer": "https://link.springer.com/signup-login",
    "elsevier": "https://www.sciencedirect.com/user/login",
    "wiley": "https://onlinelibrary.wiley.com/action/ssostart",
    "cambridge": "https://www.cambridge.org/core/login",
    "oxford": "https://academic.oup.com/journals/pages/access_purchase/society",
    "taylor_francis": "https://www.tandfonline.com/action/ssostart",
}


class ETHAuthSetup:
    """Interactive setup for ETH authentication."""
    
    def __init__(self):
        self.auth_manager = get_auth_manager()
        self.eth_username = None
        self.eth_password = None
    
    def collect_credentials(self):
        """Securely collect ETH credentials from user."""
        print("🔐 ETH Zurich Authentication Setup")
        print("=" * 50)
        print("This will securely store your ETH credentials for institutional access.")
        print("Credentials are encrypted and stored in your system keyring.\n")
        
        # Get ETH username
        self.eth_username = input("ETH Username (e.g., jdoe): ").strip()
        if not self.eth_username:
            raise ValueError("Username required")
        
        # Get ETH password securely
        self.eth_password = getpass.getpass("ETH Password: ")
        if not self.eth_password:
            raise ValueError("Password required")
        
        print(f"\n✓ Credentials collected for user: {self.eth_username}")
    
    def test_eth_login(self) -> bool:
        """Test ETH login flow to validate credentials."""
        if not PLAYWRIGHT_AVAILABLE:
            print("⚠️  Cannot test login - Playwright not available")
            return False
        
        print("\n🧪 Testing ETH login...")
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)  # Show browser for debugging
                page = browser.new_page()
                
                # Navigate to ETH login page
                eth_login_url = f"{ETH_IDP_BASE}/idp/profile/SAML2/Redirect/SSO"
                page.goto(eth_login_url)
                
                # Look for ETH login form
                username_field = page.query_selector('input[name="j_username"], input[name="username"], input[id="username"]')
                password_field = page.query_selector('input[name="j_password"], input[name="password"], input[id="password"]')
                
                if username_field and password_field:
                    print("📝 Found ETH login form, testing credentials...")
                    
                    # Fill credentials
                    username_field.fill(self.eth_username)
                    password_field.fill(self.eth_password)
                    
                    # Find submit button
                    submit_btn = page.query_selector('input[type="submit"], button[type="submit"], button:has-text("Login"), button:has-text("Sign in")')
                    if submit_btn:
                        submit_btn.click()
                        
                        # Wait for response
                        page.wait_for_load_state('networkidle', timeout=10000)
                        
                        # Check for success indicators
                        current_url = page.url
                        page_content = page.content()
                        
                        # Common error indicators
                        error_indicators = [
                            "invalid", "error", "failed", "incorrect",
                            "authentication failed", "login failed"
                        ]
                        
                        if any(indicator in page_content.lower() for indicator in error_indicators):
                            print("❌ Login test failed - check your credentials")
                            browser.close()
                            return False
                        
                        # Success indicators
                        if "logout" in page_content.lower() or "sign out" in page_content.lower():
                            print("✅ ETH login test successful!")
                            browser.close()
                            return True
                        
                        print("⚠️  Login result unclear - manual verification may be needed")
                        input("Press Enter after verifying login status in browser...")
                        
                browser.close()
                return True
                
        except Exception as e:
            print(f"❌ Login test failed: {e}")
            return False
    
    def discover_publisher_flows(self, publishers: List[str]) -> Dict[str, Dict]:
        """Discover authentication flows for specific publishers."""
        flows = {}
        
        if not PLAYWRIGHT_AVAILABLE:
            print("⚠️  Cannot discover flows - Playwright not available")
            return flows
        
        print(f"\n🔍 Discovering authentication flows for {len(publishers)} publishers...")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            
            for publisher in publishers:
                print(f"\n📚 Checking {publisher.upper()}...")
                
                try:
                    page = browser.new_page()
                    
                    # Start at publisher's institutional access page
                    if publisher in ETH_WAYF_URLS:
                        page.goto(ETH_WAYF_URLS[publisher])
                        
                        # Look for ETH in institution list
                        eth_selectors = [
                            'a:has-text("ETH Zurich")',
                            'a:has-text("Swiss Federal Institute")',
                            'option:has-text("ETH Zurich")',
                            'option:has-text("Swiss Federal Institute")',
                            '[value*="ethz"]',
                            '[href*="ethz"]'
                        ]
                        
                        eth_link = None
                        for selector in eth_selectors:
                            eth_link = page.query_selector(selector)
                            if eth_link:
                                break
                        
                        if eth_link:
                            print(f"  ✓ Found ETH option for {publisher}")
                            
                            # Get the target URL
                            if eth_link.get_attribute('href'):
                                target_url = eth_link.get_attribute('href')
                            elif eth_link.get_attribute('value'):
                                target_url = eth_link.get_attribute('value')
                            else:
                                target_url = None
                            
                            flows[publisher] = {
                                'wayf_url': ETH_WAYF_URLS[publisher],
                                'eth_selector': selector,
                                'target_url': target_url,
                                'status': 'found'
                            }
                        else:
                            print(f"  ❌ Could not find ETH option for {publisher}")
                            flows[publisher] = {
                                'wayf_url': ETH_WAYF_URLS[publisher],
                                'status': 'not_found'
                            }
                    
                    page.close()
                    
                except Exception as e:
                    print(f"  ❌ Error checking {publisher}: {e}")
                    flows[publisher] = {'status': 'error', 'error': str(e)}
            
            browser.close()
        
        return flows
    
    def setup_publisher_configs(self, flows: Dict[str, Dict]):
        """Create authentication configs for publishers."""
        print("\n⚙️  Setting up publisher configurations...")
        
        for publisher, flow_info in flows.items():
            if flow_info.get('status') == 'found':
                config = AuthConfig(
                    service_name=f"eth_{publisher}",
                    auth_method=AuthMethod.SHIBBOLETH,
                    base_url=flow_info['wayf_url'],
                    shibboleth_idp=flow_info.get('target_url') or ETH_IDP_BASE,
                    username=self.eth_username,
                    password=self.eth_password,  # Will be stored securely
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                    }
                )
                
                self.auth_manager.add_config(config)
                print(f"  ✓ Configured eth_{publisher}")
            else:
                print(f"  ⚠️  Skipped {publisher} (status: {flow_info.get('status')})")
    
    def test_download(self, publisher: str, test_doi: str) -> bool:
        """Test downloading a paper through institutional access."""
        print(f"\n🧪 Testing download from {publisher}...")
        
        try:
            from scripts.downloader import acquire_paper_by_metadata
            
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                file_path, attempts = acquire_paper_by_metadata(
                    f"Test paper {test_doi}",
                    tmpdir,
                    doi=test_doi,
                    auth_service=f"eth_{publisher}"
                )
                
                if file_path and os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    print(f"  ✅ Download successful: {file_size} bytes")
                    return True
                else:
                    print(f"  ❌ Download failed")
                    for attempt in attempts:
                        print(f"    - {attempt.strategy}: {attempt.result.value}")
                    return False
                    
        except Exception as e:
            print(f"  ❌ Download test error: {e}")
            return False
    
    def run_interactive_setup(self):
        """Run the complete interactive setup process."""
        try:
            # Step 1: Collect credentials
            self.collect_credentials()
            
            # Step 2: Test ETH login
            if not self.test_eth_login():
                response = input("\n⚠️  ETH login test failed. Continue anyway? (y/N): ")
                if response.lower() != 'y':
                    print("Setup cancelled.")
                    return False
            
            # Step 3: Choose publishers to configure
            available_publishers = list(ETH_WAYF_URLS.keys())
            print(f"\n📚 Available publishers: {', '.join(available_publishers)}")
            
            publisher_input = input("\nWhich publishers to configure? (comma-separated, or 'all'): ").strip()
            
            if publisher_input.lower() == 'all':
                selected_publishers = available_publishers
            else:
                selected_publishers = [p.strip() for p in publisher_input.split(',') if p.strip()]
                selected_publishers = [p for p in selected_publishers if p in available_publishers]
            
            if not selected_publishers:
                print("No valid publishers selected.")
                return False
            
            # Step 4: Discover authentication flows
            flows = self.discover_publisher_flows(selected_publishers)
            
            # Step 5: Setup configs
            self.setup_publisher_configs(flows)
            
            # Step 6: Optional test
            test_response = input("\n🧪 Test download with a sample paper? (y/N): ")
            if test_response.lower() == 'y':
                test_publisher = input(f"Which publisher to test? ({', '.join(selected_publishers)}): ").strip()
                test_doi = input("Test DOI (e.g., 10.1109/ACCESS.2023.1234567): ").strip()
                
                if test_publisher in selected_publishers and test_doi:
                    self.test_download(test_publisher, test_doi)
            
            print("\n🎉 ETH authentication setup complete!")
            print(f"Configured {len([f for f in flows.values() if f.get('status') == 'found'])} publishers")
            
            return True
            
        except KeyboardInterrupt:
            print("\n\nSetup cancelled by user.")
            return False
        except Exception as e:
            print(f"\n❌ Setup failed: {e}")
            return False


def main():
    """Main setup function."""
    print("ETH Zurich Institutional Access Setup")
    print("=====================================\n")
    
    if not PLAYWRIGHT_AVAILABLE:
        print("❌ This setup requires Playwright for browser automation.")
        print("Install with: pip install playwright")
        print("Then run: playwright install chromium")
        return
    
    setup = ETHAuthSetup()
    success = setup.run_interactive_setup()
    
    if success:
        print("\n✅ Setup completed successfully!")
        print("\nNext steps:")
        print("1. Test downloads with: python -c \"from scripts.downloader import *\"")
        print("2. Use auth_service='eth_<publisher>' in download calls")
        print("3. Check ~/.academic_papers/auth/ for config files")
    else:
        print("\n❌ Setup failed or was cancelled.")


if __name__ == "__main__":
    main()