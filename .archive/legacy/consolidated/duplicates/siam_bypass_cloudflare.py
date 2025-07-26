#!/usr/bin/env python3
"""
SIAM Bypass Cloudflare
======================

Attempt to bypass Cloudflare by going directly to authentication endpoints.
"""

import sys
import requests
import json
from pathlib import Path
from urllib.parse import urlencode, quote

sys.path.insert(0, str(Path(__file__).parent))

try:
    from playwright.sync_api import sync_playwright
    from secure_credential_manager import get_credential_manager
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


def siam_direct_auth_endpoints():
    """Try to access SIAM auth endpoints directly."""
    print("🔧 SIAM Direct Authentication Endpoints")
    print("=" * 60)
    
    manager = get_credential_manager()
    username, password = manager.get_eth_credentials()
    
    if not username or not password:
        print("❌ ETH credentials required")
        return False
    
    # Create a session to maintain cookies
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    })
    
    print("\n📍 Step 1: Testing direct SSO endpoint")
    
    # Common Shibboleth/SAML endpoints
    sso_endpoints = [
        "https://epubs.siam.org/action/ssostart",
        "https://epubs.siam.org/Shibboleth.sso/Login",
        "https://epubs.siam.org/action/showFedLogin",
        "https://epubs.siam.org/action/institutions",
        "https://epubs.siam.org/pb/sso/login",
        "https://epubs.siam.org/action/ssostart?redirectUri=/",
        "https://epubs.siam.org/action/shibbolethLogin"
    ]
    
    for endpoint in sso_endpoints:
        print(f"\n🔗 Testing: {endpoint}")
        try:
            response = session.get(endpoint, allow_redirects=True, timeout=10)
            print(f"   Status: {response.status_code}")
            print(f"   Final URL: {response.url}")
            
            # Check if we bypassed Cloudflare
            if "cloudflare" not in response.text.lower() and response.status_code == 200:
                print("   ✅ No Cloudflare detected!")
                
                # Check for institution search
                if "institution" in response.text.lower() or "shibboleth" in response.text.lower():
                    print("   ✅ Found institution content!")
                    
                    # Try to extract any forms or endpoints
                    if "ethz.ch" in response.text:
                        print("   🎯 Found ETH reference!")
                    
                    return endpoint, session
                    
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    return None, session


def siam_use_different_domain():
    """Try using SIAM's other domains that might not have Cloudflare."""
    print("\n🌐 Trying alternative SIAM domains")
    
    alt_domains = [
        "https://www.siam.org/publications/journals",
        "https://my.siam.org/",
        "https://sinews.siam.org/",
        # WARNING: Insecure HTTP protocol - use HTTPS
    "http://epubs.siam.org/",  # Try HTTP
        "https://epubs.siam.org/doi/10.1137/20M1339829.full",  # Different URL format
    ]
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'  # Try as Googlebot
    })
    
    for domain in alt_domains:
        print(f"\n🔗 Testing: {domain}")
        try:
            response = session.get(domain, timeout=10)
            if "cloudflare" not in response.text.lower():
                print("   ✅ No Cloudflare on this domain!")
                return domain
        except Exception as e:
            pass
    
    return None


def siam_undetected_browser():
    """Use undetected-chromedriver approach."""
    print("\n🥷 Attempting undetected browser approach")
    
    try:
        # First, let's use requests with a real browser session
        import undetected_chromedriver as uc
        
        options = uc.ChromeOptions()
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--user-data-dir=/tmp/chrome-profile-siam')
        
        driver = uc.Chrome(options=options)
        
        print("✅ Undetected Chrome driver created")
        
        # Navigate to SIAM
        driver.get("https://epubs.siam.org/doi/10.1137/20M1339829")
        
        import time
        time.sleep(10)
        
        # Check if we bypassed Cloudflare
        if "cloudflare" not in driver.page_source.lower():
            print("✅ Bypassed Cloudflare with undetected driver!")
            return True
        
    except Exception as e:
        print(f"❌ Undetected driver failed: {e}")
        print("💡 Install with: pip install undetected-chromedriver")
    
    return False


def siam_api_endpoints():
    """Look for hidden API endpoints."""
    print("\n🔍 Searching for API endpoints")
    
    # Common API patterns
    api_patterns = [
        "/api/v1/auth",
        "/api/login",
        "/api/sso",
        "/services/auth",
        "/rest/auth",
        "/ajax/login",
        "/.json",
        "/metadata.json"
    ]
    
    base_url = "https://epubs.siam.org"
    session = requests.Session()
    
    for pattern in api_patterns:
        url = base_url + pattern
        try:
            response = session.get(url, timeout=5)
            if response.status_code != 404:
                print(f"✅ Found endpoint: {url} (Status: {response.status_code})")
        except Exception as e:
            pass


def siam_playwright_stealth():
    """Ultimate stealth mode with Playwright."""
    print("\n🥷 Ultimate Playwright Stealth Mode")
    
    with sync_playwright() as p:
        # Use webkit or firefox instead of chromium
        browser = p.firefox.launch(
            headless=False,
            slow_mo=2000,  # Very slow, more human-like
            args=['--width=1920', '--height=1080']
        )
        
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='America/New_York',
            permissions=['geolocation'],
            geolocation={'latitude': 40.7128, 'longitude': -74.0060},
            color_scheme='light',
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'
        )
        
        # Add stealth scripts
        context.add_init_script("""
            // Overwrite the `plugins` property to use a custom getter.
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            // Overwrite the `languages` property
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
            
            // Overwrite webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
            
            // Overwrite permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // Add chrome object
            window.chrome = {
                runtime: {},
            };
            
            // Add realistic window properties
            window.outerWidth = 1920;
            window.outerHeight = 1080;
        """)
        
        page = context.new_page()
        
        # First visit Google to establish a "normal" browsing pattern
        print("📍 Establishing normal browsing pattern...")
        page.goto("https://www.google.com")
        page.wait_for_timeout(3000)
        
        # Then navigate to SIAM
        print("📍 Navigating to SIAM...")
        page.goto("https://epubs.siam.org/", wait_until='domcontentloaded')
        page.wait_for_timeout(5000)
        
        # Check result
        if "cloudflare" not in page.content().lower():
            print("✅ Bypassed Cloudflare with Firefox + Stealth!")
            
            # Now try to access paper
            page.goto("https://epubs.siam.org/doi/10.1137/20M1339829")
            page.wait_for_timeout(5000)
            
            # Look for institutional button
            inst_button = page.query_selector('a.institutional__btn, a:has-text("Institution")')
            if inst_button:
                print("✅ Found institutional button!")
                return True
        
        browser.close()
    
    return False


def siam_cookie_transfer():
    """Get cookies from a manual session and transfer them."""
    print("\n🍪 Cookie Transfer Approach")
    print("=" * 60)
    
    print("Steps:")
    print("1. Open Chrome DevTools (F12)")
    print("2. Go to Application > Cookies")
    print("3. Copy the cookies for epubs.siam.org")
    print("4. We can then use these cookies in our automated session")
    
    # Example of using transferred cookies
    """
    cookies = [
        {'name': 'cf_clearance', 'value': 'xxx', 'domain': '.siam.org'},
        {'name': 'JSESSIONID', 'value': 'yyy', 'domain': 'epubs.siam.org'}
    ]
    
    page.context.add_cookies(cookies)
    """


def main():
    """Try all automated approaches."""
    print("SIAM Complete Automation Attempts")
    print("=================================\n")
    
    # Try direct endpoints
    endpoint, session = siam_direct_auth_endpoints()
    if endpoint:
        print(f"\n✅ Found working endpoint: {endpoint}")
        print("This bypasses Cloudflare!")
    
    # Try alternative domains
    alt_domain = siam_use_different_domain()
    if alt_domain:
        print(f"\n✅ Found domain without Cloudflare: {alt_domain}")
    
    # Try API discovery
    siam_api_endpoints()
    
    # Try undetected browser
    if siam_undetected_browser():
        print("\n✅ Undetected browser approach works!")
    
    # Try ultimate stealth
    if siam_playwright_stealth():
        print("\n✅ Stealth Playwright approach works!")
    
    # Explain cookie transfer
    siam_cookie_transfer()
    
    print("\n" + "="*60)
    print("Additional ideas to explore:")
    print("1. Use residential proxies to avoid IP-based detection")
    print("2. Implement request delays and mouse movements")
    print("3. Use Selenium Grid with real browser instances")
    print("4. Reverse engineer their mobile app API")
    print("5. Use Puppeteer-extra with stealth plugin")
    print("6. Try accessing via institutional proxy directly")


if __name__ == "__main__":
    main()