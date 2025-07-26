#!/usr/bin/env python3
"""
Elsevier Cookie Approach
========================

Alternative approach: Use saved CloudFlare cookies or explore API endpoints.
"""

import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright
import sys
import time
import requests

sys.path.insert(0, str(Path(__file__).parent))

class ElsevierCookieApproach:
    def __init__(self):
        self.output_dir = Path("elsevier_cookies")
        self.output_dir.mkdir(exist_ok=True)
        self.cookie_file = self.output_dir / "cloudflare_cookies.json"
        
    def log(self, message):
        timestamp = time.strftime('%H:%M:%S')
        print(f"[{timestamp}] {message}")
    
    async def save_cookies_after_manual_solve(self):
        """Let user manually solve CloudFlare, then save cookies"""
        
        self.log("🍪 COOKIE APPROACH: Manual solve + cookie reuse")
        self.log("=" * 60)
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)
                context = await browser.new_context()
                page = await context.new_page()
                
                # Navigate to Elsevier
                self.log("\n📌 Please solve CloudFlare manually:")
                self.log("1. The browser will open to Elsevier")
                self.log("2. Solve the CloudFlare challenge manually")
                self.log("3. Once you see the article page, press Enter here")
                
                await page.goto("https://www.sciencedirect.com/science/article/pii/S0021999119305169")
                
                # Wait for user to solve
                input("\n⏸️  Press Enter after solving CloudFlare...")
                
                # Save cookies
                cookies = await context.cookies()
                with open(self.cookie_file, 'w') as f:
                    json.dump(cookies, f)
                
                self.log(f"✅ Saved {len(cookies)} cookies to {self.cookie_file}")
                
                # Also save as requests-compatible format
                session_cookies = {}
                for cookie in cookies:
                    session_cookies[cookie['name']] = cookie['value']
                
                requests_cookie_file = self.output_dir / "requests_cookies.json"
                with open(requests_cookie_file, 'w') as f:
                    json.dump(session_cookies, f)
                
                self.log(f"✅ Saved requests-compatible cookies to {requests_cookie_file}")
                
                await browser.close()
                
                return True
                
        except Exception as e:
            self.log(f"❌ Error: {e}")
            return False
    
    async def test_with_saved_cookies(self):
        """Test accessing Elsevier with saved cookies"""
        
        if not self.cookie_file.exists():
            self.log("❌ No saved cookies found. Run save_cookies_after_manual_solve() first")
            return False
        
        self.log("🍪 Testing with saved CloudFlare cookies")
        self.log("=" * 60)
        
        try:
            # Load cookies
            with open(self.cookie_file, 'r') as f:
                cookies = json.load(f)
            
            self.log(f"✅ Loaded {len(cookies)} cookies")
            
            # Test with Playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)
                context = await browser.new_context()
                
                # Add cookies
                await context.add_cookies(cookies)
                
                page = await context.new_page()
                
                # Try accessing paper
                self.log("\n🔄 Accessing paper with cookies...")
                await page.goto("https://www.sciencedirect.com/science/article/pii/S0021999119305169")
                await page.wait_for_timeout(5000)
                
                # Check if we bypassed CloudFlare
                page_content = await page.content()
                if 'Are you a robot?' not in page_content:
                    self.log("✅ CloudFlare bypassed with cookies!")
                    
                    # Take screenshot
                    await page.screenshot(path="elsevier_cookie_success.png")
                    
                    # Now try to access PDF
                    # ... (continue with institutional login)
                    
                    return True
                else:
                    self.log("❌ Cookies didn't bypass CloudFlare")
                
                await browser.close()
                
        except Exception as e:
            self.log(f"❌ Error: {e}")
        
        return False
    
    def test_api_endpoints(self):
        """Explore Elsevier API endpoints that might bypass CloudFlare"""
        
        self.log("🔬 Exploring Elsevier API endpoints")
        self.log("=" * 60)
        
        test_doi = "10.1016/j.jcp.2019.07.031"
        pii = "S0021999119305169"
        
        # Various API endpoints to try
        endpoints = [
            # Direct PDF endpoint
            f"https://www.sciencedirect.com/science/article/pii/{pii}/pdfft?isDTMRedir=true&download=true",
            
            # API endpoints
            f"https://api.elsevier.com/content/article/pii/{pii}",
            f"https://api.elsevier.com/content/article/doi/{test_doi}",
            
            # Alternative domains
            f"https://pdf.sciencedirectassets.com/article/{pii}",
            f"https://reader.elsevier.com/reader/pii/{pii}",
            
            # Metadata endpoint
            f"https://www.sciencedirect.com/sdfe/arp/pii/{pii}/meta",
            
            # CrossRef API (sometimes has full text links)
            f"https://api.crossref.org/works/{test_doi}"
        ]
        
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json, application/pdf, text/html'
        })
        
        # Load cookies if available
        requests_cookie_file = self.output_dir / "requests_cookies.json"
        if requests_cookie_file.exists():
            with open(requests_cookie_file, 'r') as f:
                cookies = json.load(f)
                session.cookies.update(cookies)
                self.log("✅ Loaded saved cookies for requests")
        
        for endpoint in endpoints:
            self.log(f"\n🔍 Testing: {endpoint}")
            try:
                response = session.get(endpoint, timeout=10, allow_redirects=False)
                self.log(f"   Status: {response.status_code}")
                self.log(f"   Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
                
                if response.status_code == 200:
                    if 'pdf' in response.headers.get('Content-Type', '').lower():
                        self.log("   ✅ Found PDF endpoint!")
                        # Save PDF
                        pdf_path = self.output_dir / f"elsevier_api_{pii}.pdf"
                        with open(pdf_path, 'wb') as f:
                            f.write(response.content)
                        self.log(f"   ✅ Saved PDF: {pdf_path}")
                        return True
                    elif 'json' in response.headers.get('Content-Type', '').lower():
                        data = response.json()
                        self.log(f"   📄 JSON response with {len(data)} keys")
                        # Look for PDF URLs in JSON
                        if 'pdf' in str(data).lower():
                            self.log("   ℹ️ JSON contains PDF references")
                elif response.status_code == 302:
                    self.log(f"   ➡️ Redirect to: {response.headers.get('Location', 'Unknown')}")
                    
            except Exception as e:
                self.log(f"   ❌ Error: {e}")
        
        return False

async def main():
    approach = ElsevierCookieApproach()
    
    print("\n🔧 Choose approach:")
    print("1. Save cookies after manual CloudFlare solve")
    print("2. Test with previously saved cookies")
    print("3. Explore API endpoints")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        success = await approach.save_cookies_after_manual_solve()
    elif choice == "2":
        success = await approach.test_with_saved_cookies()
    elif choice == "3":
        success = approach.test_api_endpoints()
    else:
        print("Invalid choice")
        return
    
    if success:
        print("\n🎉 Success!")
    else:
        print("\n⚠️ Approach needs refinement")
        print("\nNext steps:")
        print("1. Try the ultrathink bypass script")
        print("2. Use manual cookie approach")
        print("3. Consider using Sci-Hub for recent papers too")

if __name__ == "__main__":
    asyncio.run(main())