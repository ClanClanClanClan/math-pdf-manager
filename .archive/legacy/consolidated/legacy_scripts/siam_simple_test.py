#!/usr/bin/env python3
"""
SIAM Simple Test
================

Test SIAM access and identify authentication requirements.
"""

import sys
import time
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from playwright.sync_api import sync_playwright
    from secure_credential_manager import get_credential_manager
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


def test_siam_access():
    """Test SIAM access patterns."""
    print("🧪 Testing SIAM Access Patterns")
    print("=" * 50)
    
    # Test URLs
    test_urls = [
        ("Open Access Paper", "https://epubs.siam.org/doi/10.1137/19M1274067"),
        ("Regular Paper", "https://epubs.siam.org/doi/10.1137/20M1339829"),
        ("PDF Direct", "https://epubs.siam.org/doi/pdf/10.1137/20M1339829")
    ]
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=500,
            args=['--start-maximized']
        )
        
        page = browser.new_page()
        
        for name, url in test_urls:
            print(f"\n📄 Testing: {name}")
            print(f"🔗 URL: {url}")
            
            try:
                page.goto(url, wait_until='domcontentloaded', timeout=30000)
                page.wait_for_timeout(5000)
                
                # Check what we got
                current_url = page.url
                page_title = page.title()
                
                print(f"📍 Current URL: {current_url}")
                print(f"📋 Page title: {page_title[:80]}...")
                
                # Check for various indicators
                page_text = page.content()
                
                if "cloudflare" in page_text.lower():
                    print("🔒 Cloudflare challenge detected")
                    print("⏳ Waiting 10 seconds for challenge...")
                    page.wait_for_timeout(10000)
                    
                    # Re-check after wait
                    page_text = page.content()
                    current_url = page.url
                
                # Check for PDF
                if current_url.endswith('.pdf') or 'application/pdf' in page_text[:1000]:
                    print("✅ PDF accessible!")
                    
                    # Check if it's actually displaying
                    screenshot_path = f"siam_test_{name.replace(' ', '_').lower()}.png"
                    page.screenshot(path=screenshot_path)
                    print(f"📸 Screenshot: {screenshot_path}")
                    
                # Check for access restrictions
                elif any(x in page_text.lower() for x in ['access denied', '403', 'forbidden', 'subscription', 'purchase']):
                    print("❌ Access restricted - login required")
                    
                    # Look for login options
                    login_buttons = page.query_selector_all('a:has-text("sign in"), button:has-text("sign in"), a:has-text("log in"), button:has-text("log in"), a:has-text("institution")')
                    if login_buttons:
                        print(f"🔑 Found {len(login_buttons)} login option(s)")
                    
                # Check for article page
                elif "doi" in current_url and any(x in page_text for x in ['Abstract', 'References', 'Download']):
                    print("📄 Article page loaded")
                    
                    # Look for PDF links
                    pdf_links = page.query_selector_all('a[href*="pdf"], button:has-text("PDF"), a:has-text("Download")')
                    print(f"📥 Found {len(pdf_links)} PDF link(s)")
                    
                    if pdf_links:
                        for i, link in enumerate(pdf_links[:3]):
                            try:
                                href = link.get_attribute('href')
                                text = link.text_content()
                                print(f"  {i+1}. Text: '{text}', Href: '{href}'")
                            except Exception as e:
                                pass
                
                else:
                    print("❓ Unknown page type")
                
            except Exception as e:
                print(f"❌ Error: {e}")
        
        print("\n⏳ Browser stays open for 30 seconds...")
        page.wait_for_timeout(30000)
        browser.close()


def main():
    """Run SIAM access test."""
    print("SIAM Access Test")
    print("================")
    print("Testing different SIAM URLs to understand access patterns\n")
    
    test_siam_access()
    
    print("\n" + "="*60)
    print("SIAM Access Test Complete")
    print("Check screenshots and output to understand access requirements")


if __name__ == "__main__":
    main()