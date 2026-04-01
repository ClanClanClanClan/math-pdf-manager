#!/usr/bin/env python3
"""
WILEY PDF URL ANALYSIS
======================

Analyze what URLs the PDF links point to and try different access methods
"""

import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))

async def analyze_wiley_pdf_urls():
    """Analyze Wiley PDF URLs and access patterns"""
    
    print("🔍 WILEY PDF URL ANALYSIS")
    print("=" * 80)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled', '--start-maximized']
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = await context.new_page()
        
        # Navigate to article
        test_doi = "10.1002/anie.202004934"
        url = f"https://doi.org/{test_doi}"
        print(f"📍 Navigating to: {url}")
        await page.goto(url, wait_until='domcontentloaded')
        await page.wait_for_timeout(3000)
        
        # Accept cookies
        try:
            cookie_btn = await page.wait_for_selector('button:has-text("Accept All")', timeout=5000)
            if cookie_btn:
                await cookie_btn.click()
                await page.wait_for_timeout(2000)
        except:
            pass
        
        # Find all PDF-related links and analyze their URLs
        print("\n🔗 PDF LINK ANALYSIS:")
        pdf_selectors = [
            'a[href*="/pdf/"]',
            'a[href*="epdf"]',
            'a:has-text("PDF")',
            'a:has-text("Download PDF")',
            'a[href*="doi/pdf"]'
        ]
        
        pdf_urls = []
        for selector in pdf_selectors:
            try:
                links = await page.query_selector_all(selector)
                for link in links:
                    href = await link.get_attribute('href')
                    text = await link.inner_text()
                    visible = await link.is_visible()
                    
                    if href and visible:
                        # Make absolute URL
                        if href.startswith('/'):
                            href = f"https://onlinelibrary.wiley.com{href}"
                        
                        pdf_urls.append({
                            'url': href,
                            'text': text.strip(),
                            'selector': selector
                        })
                        print(f"   📎 '{text.strip()}' -> {href}")
            except:
                pass
        
        # Try different access methods for each PDF URL
        for i, pdf_info in enumerate(pdf_urls[:2], 1):  # Test first 2 URLs
            print(f"\n🧪 TESTING PDF URL {i}: {pdf_info['url']}")
            
            # Method 1: Direct navigation
            print("   Method 1: Direct navigation")
            try:
                new_page = await context.new_page()
                response = await new_page.goto(pdf_info['url'], wait_until='domcontentloaded')
                
                await new_page.wait_for_timeout(3000)
                final_url = new_page.url
                status = response.status if response else "No response"
                
                print(f"      Status: {status}")
                print(f"      Final URL: {final_url}")
                
                # Check if it's a PDF or login page
                if 'pdf' in final_url.lower():
                    print("      ✅ Looks like PDF URL")
                elif 'login' in final_url.lower():
                    print("      🔑 Redirected to login")
                else:
                    print("      ❓ Unknown redirect")
                
                await new_page.close()
                
            except Exception as e:
                print(f"      ❌ Failed: {str(e)}")
            
            # Method 2: Try with custom headers
            print("   Method 2: With custom headers")
            try:
                new_page = await context.new_page()
                
                # Set custom headers that might help
                await new_page.set_extra_http_headers({
                    'Referer': f"https://onlinelibrary.wiley.com/doi/{test_doi}",
                    'Accept': 'application/pdf,*/*',
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                })
                
                response = await new_page.goto(pdf_info['url'])
                await new_page.wait_for_timeout(2000)
                
                final_url = new_page.url
                content_type = response.headers.get('content-type', '') if response else ''
                
                print(f"      Content-Type: {content_type}")
                print(f"      Final URL: {final_url}")
                
                if 'pdf' in content_type:
                    print("      ✅ Got PDF content type!")
                
                await new_page.close()
                
            except Exception as e:
                print(f"      ❌ Failed: {str(e)}")
        
        # Check what cookies we have
        print(f"\n🍪 CURRENT COOKIES:")
        cookies = await context.cookies()
        for cookie in cookies[:5]:  # Show first 5 cookies
            print(f"   {cookie['name']}: {cookie['value'][:50]}...")
        
        # Try accessing article page with different approach
        print(f"\n🔄 ALTERNATIVE ACCESS PATTERNS:")
        
        # Pattern 1: Try individual login instead of institutional
        try:
            login_btn = await page.wait_for_selector('button:has-text("Login / Register")', timeout=5000)
            if login_btn:
                print("   Found Login/Register button - checking individual login")
                await login_btn.click()
                await page.wait_for_timeout(2000)
                
                # Look for individual login option
                individual_link = await page.wait_for_selector('a:has-text("Individual login")', timeout=5000)
                if individual_link:
                    print("   📝 Individual login available (but we'd need credentials)")
                else:
                    print("   ❌ No individual login found")
        except:
            print("   ❌ Could not find login options")
        
        print("\n⏸️ Browser staying open for inspection...")
        await page.wait_for_timeout(30000)
        
        await browser.close()
        
        return len(pdf_urls) > 0

if __name__ == "__main__":
    success = asyncio.run(analyze_wiley_pdf_urls())
    print(f"\n{'✅' if success else '❌'} Analysis complete")