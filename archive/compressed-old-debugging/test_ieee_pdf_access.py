#!/usr/bin/env python3
"""
Test IEEE PDF Access
====================

Test if we already have PDF access after authentication flow.
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def test_pdf_access():
    """Test direct PDF access after authentication."""
    
    output_dir = Path("ieee_pdf_test")
    output_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        try:
            # Try direct access to IEEE stamp URL
            doc_id = "8347162"
            stamp_url = f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={doc_id}"
            
            print(f"🚀 Testing direct access to: {stamp_url}")
            response = await page.goto(stamp_url, wait_until='networkidle', timeout=30000)
            
            if response:
                print(f"Response status: {response.status}")
                content_type = response.headers.get('content-type', '')
                print(f"Content-type: {content_type}")
                
                if response.status == 200:
                    content = await response.body()
                    print(f"Content size: {len(content)} bytes")
                    
                    if content.startswith(b'%PDF'):
                        print("🎉 SUCCESS! Got PDF directly without authentication!")
                        pdf_path = output_dir / "ieee_paper_direct.pdf"
                        with open(pdf_path, 'wb') as f:
                            f.write(content)
                        print(f"📁 PDF saved to: {pdf_path}")
                        return True
                    else:
                        print("📄 Content is HTML, checking for PDF iframe...")
                        
                        # Wait for page to load fully
                        await page.wait_for_timeout(5000)
                        
                        # Look for PDF iframe
                        pdf_frame = await page.query_selector('iframe[src*="pdf"], iframe#pdf, iframe[src*="stamp"]')
                        if pdf_frame:
                            src = await pdf_frame.get_attribute('src')
                            print(f"📄 Found PDF iframe: {src}")
                            
                            if src:
                                if not src.startswith('http'):
                                    src = f"https://ieeexplore.ieee.org{src}"
                                
                                print(f"🔄 Navigating to iframe source: {src}")
                                pdf_response = await page.goto(src, wait_until='networkidle')
                                pdf_content = await pdf_response.body()
                                
                                if pdf_content.startswith(b'%PDF'):
                                    print("🎉 SUCCESS! Downloaded PDF from iframe!")
                                    pdf_path = output_dir / "ieee_paper_iframe.pdf"
                                    with open(pdf_path, 'wb') as f:
                                        f.write(pdf_content)
                                    print(f"📁 PDF saved to: {pdf_path}")
                                    print(f"📊 PDF size: {len(pdf_content)} bytes")
                                    return True
                                else:
                                    print("❌ Iframe content is not PDF")
                        else:
                            print("❌ No PDF iframe found")
                            
                            # Take screenshot to see what's on page
                            await page.screenshot(path=output_dir / "stamp_page.png")
                            print("📸 Screenshot saved to stamp_page.png")
                            
                            # Check page content
                            page_text = await page.text_content('body')
                            if 'sign' in page_text.lower() or 'login' in page_text.lower():
                                print("🔐 Page requires authentication")
                            else:
                                print("❓ Unknown page content")
                
            return False
            
        except Exception as e:
            print(f"❌ Error: {e}")
            await page.screenshot(path=output_dir / "error.png")
            return False
        finally:
            print("Keeping browser open for 10 seconds...")
            await asyncio.sleep(10)
            await browser.close()

if __name__ == "__main__":
    success = asyncio.run(test_pdf_access())
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}: PDF access test")