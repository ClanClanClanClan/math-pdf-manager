#!/usr/bin/env python3
"""
ETH VPN APPROACH FOR WILEY
==========================

Investigate automating ETH VPN connection to bypass publisher restrictions
"""

import asyncio
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def check_cisco_secure_client():
    """Check if Cisco Secure Client is available"""
    
    print("🔍 CHECKING CISCO SECURE CLIENT")
    print("=" * 50)
    
    # Common paths for Cisco Secure Client on macOS
    cisco_paths = [
        "/opt/cisco/secureclient/bin/vpn",
        "/Applications/Cisco/Cisco Secure Client.app/Contents/MacOS/Cisco Secure Client",
        "/usr/local/bin/vpn",
        "/opt/cisco/anyconnect/bin/vpn"
    ]
    
    found_path = None
    for path in cisco_paths:
        if Path(path).exists():
            found_path = path
            print(f"✅ Found Cisco client at: {path}")
            break
    
    if not found_path:
        print("❌ Cisco Secure Client not found")
        print("💡 Alternative approaches:")
        print("   1. Use ETH proxy servers")
        print("   2. Route through ETH network")
        print("   3. Use ETH's EZproxy service")
        return None
    
    return found_path

def check_eth_vpn_config():
    """Check for ETH VPN configuration"""
    
    print("\n🔍 CHECKING ETH VPN CONFIGURATION")
    print("=" * 50)
    
    # Common VPN config locations
    config_paths = [
        "~/Library/Preferences/com.cisco.secureclient.plist",
        "~/.cisco/",
        "/etc/vpn/",
    ]
    
    for path in config_paths:
        expanded_path = Path(path).expanduser()
        if expanded_path.exists():
            print(f"✅ Found VPN config at: {expanded_path}")
        else:
            print(f"❌ No config at: {expanded_path}")
    
    print("\n💡 ETH VPN connection typically requires:")
    print("   - ETH username/password")
    print("   - VPN server: vpn.ethz.ch")
    print("   - Two-factor authentication")

async def test_eth_proxy_approach():
    """Test using ETH proxy instead of VPN"""
    
    print("\n🔍 TESTING ETH PROXY APPROACH")
    print("=" * 50)
    
    # ETH provides HTTP proxies for students
    eth_proxies = [
        "proxy.ethz.ch:3128",
        "proxy.student.ethz.ch:3128",
        "www-cache.ethz.ch:3128"
    ]
    
    from playwright.async_api import async_playwright
    
    for proxy in eth_proxies:
        print(f"\n🔄 Testing proxy: {proxy}")
        
        try:
            async with async_playwright() as p:
                # Launch browser with proxy
                browser = await p.chromium.launch(
                    headless=True,
                    proxy={
                        "server": f"http://{proxy}",
                        # Note: Would need ETH credentials for proxy auth
                    }
                )
                
                context = await browser.new_context()
                page = await context.new_page()
                
                # Test if we can reach Wiley through ETH proxy
                test_url = "https://onlinelibrary.wiley.com/"
                
                response = await page.goto(test_url, timeout=10000)
                status = response.status if response else "No response"
                
                print(f"   Status: {status}")
                
                if status == 200:
                    print("   ✅ Proxy connection successful")
                    
                    # Check if we're coming from ETH IP
                    await page.goto("https://ipinfo.io/json")
                    content = await page.content()
                    if 'ethz' in content.lower() or 'eth zurich' in content.lower():
                        print("   ✅ Successfully routing through ETH network")
                    else:
                        print("   ❌ Not routing through ETH network")
                else:
                    print(f"   ❌ Proxy failed with status: {status}")
                
                await browser.close()
                
        except Exception as e:
            print(f"   ❌ Proxy test failed: {str(e)}")

def investigate_alternative_wiley_access():
    """Investigate alternative ways to access Wiley"""
    
    print("\n🔍 ALTERNATIVE WILEY ACCESS METHODS")
    print("=" * 50)
    
    print("1. 🎓 ETH Library Portal")
    print("   - Access through library.ethz.ch")
    print("   - Pre-authenticated access")
    print("   - Bypass publisher login entirely")
    
    print("\n2. 🔗 EZproxy Links")
    print("   - ETH provides EZproxy service")
    print("   - URLs like: wiley.com.ezproxy.ethz.ch")
    print("   - Already authenticated through ETH")
    
    print("\n3. 📚 Direct Database Access")
    print("   - Access through ETH database subscriptions")
    print("   - May have different access patterns")
    
    print("\n4. 🌐 Alternative Domains")
    print("   - Wiley has multiple access points")
    print("   - onlinelibrary.wiley.com vs wiley.com")
    print("   - Regional variations")

async def test_eth_library_portal():
    """Test accessing Wiley through ETH library portal"""
    
    print("\n🔍 TESTING ETH LIBRARY PORTAL ACCESS")
    print("=" * 50)
    
    from playwright.async_api import async_playwright
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Try ETH library portal
            library_url = "https://library.ethz.ch/"
            print(f"📍 Navigating to: {library_url}")
            
            await page.goto(library_url)
            await page.wait_for_timeout(3000)
            
            # Look for database/journal access
            print("🔍 Looking for journal database access...")
            
            # Take screenshot
            await page.screenshot(path='eth_library_portal.png')
            print("📸 Screenshot: eth_library_portal.png")
            
            print("⏸️ Keeping browser open for manual exploration...")
            await page.wait_for_timeout(30000)
            
            await browser.close()
            
    except Exception as e:
        print(f"❌ Library portal test failed: {str(e)}")

async def main():
    """Main investigation function"""
    
    print("🧠 ETH VPN / ALTERNATIVE ACCESS INVESTIGATION")
    print("=" * 80)
    
    # Check for Cisco client
    cisco_path = check_cisco_secure_client()
    
    # Check VPN config
    check_eth_vpn_config()
    
    # Test proxy approach
    await test_eth_proxy_approach()
    
    # Investigate alternatives
    investigate_alternative_wiley_access()
    
    # Test library portal
    await test_eth_library_portal()
    
    print("\n💡 RECOMMENDATIONS:")
    print("1. 🎯 Try ETH library portal first (library.ethz.ch)")
    print("2. 🔗 Look for EZproxy URLs for Wiley")
    print("3. 🌐 Test alternative Wiley domains")
    print("4. 📞 Contact ETH IT for VPN automation guidance")

if __name__ == "__main__":
    asyncio.run(main())