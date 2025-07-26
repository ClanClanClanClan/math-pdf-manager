#!/usr/bin/env python3
"""
Debug IEEE Download
===================

Detailed debugging of IEEE PDF download with screenshots and verbose logging.
"""

import os
import asyncio
import nest_asyncio
import logging
from datetime import datetime
from pathlib import Path

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("ieee_debug")

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

async def debug_ieee_download():
    """Debug IEEE download process with detailed logging."""
    from playwright.async_api import async_playwright
    
    # Test parameters
    test_doi = "10.1109/JPROC.2018.2820126"
    ieee_url = f"https://doi.org/{test_doi}"
    
    # Create debug directory
    debug_dir = Path("ieee_debug_output")
    debug_dir.mkdir(exist_ok=True)
    
    logger.info(f"🔍 Starting IEEE debug session")
    logger.info(f"📄 DOI: {test_doi}")
    logger.info(f"🔗 URL: {ieee_url}")
    logger.info(f"📁 Debug output: {debug_dir}")
    
    async with async_playwright() as p:
        # Launch browser in non-headless mode for debugging
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Enable console logging
        page.on("console", lambda msg: logger.debug(f"Browser console: {msg.text}"))
        
        try:
            # Step 1: Navigate to DOI URL
            logger.info("Step 1: Navigating to DOI URL...")
            response = await page.goto(ieee_url, wait_until='networkidle')
            await page.screenshot(path=debug_dir / "01_initial_page.png")
            
            current_url = page.url
            page_title = await page.title()
            logger.info(f"Current URL: {current_url}")
            logger.info(f"Page title: {page_title}")
            logger.info(f"Response status: {response.status if response else 'No response'}")
            
            # Step 2: Check if we need to authenticate
            logger.info("Step 2: Checking authentication status...")
            
            # Look for institutional access links
            institutional_selectors = [
                'text="Institutional Sign In"',
                'text="Access through your institution"',
                'text="Sign in through your institution"',
                'a:has-text("Institution")',
                'a:has-text("Sign In")',
                'button:has-text("Sign In")'
            ]
            
            needs_auth = False
            for selector in institutional_selectors:
                element = await page.query_selector(selector)
                if element:
                    logger.info(f"Found institutional login element: {selector}")
                    needs_auth = True
                    await element.click()
                    await page.wait_for_load_state('networkidle')
                    await page.screenshot(path=debug_dir / "02_after_institutional_click.png")
                    break
            
            # Step 3: Extract document ID
            logger.info("Step 3: Extracting document ID...")
            current_url = page.url
            doc_id = None
            
            if '/document/' in current_url:
                doc_id = current_url.split('/document/')[1].split('/')[0]
                logger.info(f"Extracted doc ID from URL: {doc_id}")
            else:
                # Try to find IEEE links on the page
                ieee_links = await page.query_selector_all('a[href*="ieeexplore.ieee.org"]')
                logger.info(f"Found {len(ieee_links)} IEEE links on page")
                
                for i, link in enumerate(ieee_links):
                    href = await link.get_attribute('href')
                    text = await link.text_content()
                    logger.debug(f"IEEE link {i}: {href} (text: {text})")
                    if href and '/document/' in href:
                        doc_id = href.split('/document/')[1].split('/')[0].split('?')[0]
                        logger.info(f"Extracted doc ID from link: {doc_id}")
                        
                        # Click the link to go to IEEE page
                        await link.click()
                        await page.wait_for_load_state('networkidle')
                        await page.screenshot(path=debug_dir / "03_ieee_document_page.png")
                        break
            
            if not doc_id:
                logger.error("Could not extract document ID!")
                return False
            
            # Step 4: Look for PDF download options
            logger.info("Step 4: Looking for PDF download options...")
            current_url = page.url
            logger.info(f"Current URL: {current_url}")
            
            # Debug: List all links on the page
            all_links = await page.query_selector_all('a')
            logger.info(f"Total links on page: {len(all_links)}")
            
            pdf_links = []
            for link in all_links[:20]:  # Check first 20 links
                href = await link.get_attribute('href')
                text = await link.text_content()
                if href and ('pdf' in href.lower() or 'PDF' in text or 'stamp' in href):
                    pdf_links.append((href, text))
                    logger.debug(f"Potential PDF link: {href} (text: {text})")
            
            # Debug: List all buttons
            all_buttons = await page.query_selector_all('button')
            logger.info(f"Total buttons on page: {len(all_buttons)}")
            
            for i, button in enumerate(all_buttons[:10]):  # Check first 10 buttons
                text = await button.text_content()
                classes = await button.get_attribute('class')
                if text and ('PDF' in text or 'Download' in text):
                    logger.debug(f"Button {i}: {text} (classes: {classes})")
            
            # Step 5: Try stamp URL
            logger.info("Step 5: Trying stamp.jsp URL...")
            stamp_url = f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={doc_id}"
            logger.info(f"Stamp URL: {stamp_url}")
            
            response = await page.goto(stamp_url, wait_until='networkidle')
            await page.screenshot(path=debug_dir / "04_stamp_page.png")
            
            if response:
                logger.info(f"Stamp page status: {response.status}")
                content_type = response.headers.get('content-type', '')
                logger.info(f"Content-Type: {content_type}")
                
                # Check if we got a PDF
                content = await response.body()
                if content.startswith(b'%PDF'):
                    logger.info("✅ Got PDF content from stamp URL!")
                    with open(debug_dir / "downloaded.pdf", 'wb') as f:
                        f.write(content)
                    return True
                else:
                    logger.info("Stamp URL returned HTML, not PDF")
                    
                    # Check for iframes on stamp page
                    iframes = await page.query_selector_all('iframe')
                    logger.info(f"Found {len(iframes)} iframes on stamp page")
                    
                    for i, iframe in enumerate(iframes):
                        src = await iframe.get_attribute('src')
                        logger.debug(f"Iframe {i} src: {src}")
            
            # Step 6: Try clicking PDF buttons
            logger.info("Step 6: Trying to click PDF download buttons...")
            
            # Go back to document page
            doc_url = f"https://ieeexplore.ieee.org/document/{doc_id}"
            await page.goto(doc_url, wait_until='networkidle')
            await page.screenshot(path=debug_dir / "05_document_page_retry.png")
            
            # More specific IEEE selectors
            download_selectors = [
                'a.stats-document-abstract-downloadPdf',
                'button.stats-document-abstract-downloadPdf',
                'a[aria-label*="PDF"]',
                'button[aria-label*="PDF"]',
                'a.pdf-btn-link',
                'xpl-document-details .pdf-btn-link',
                '[class*="pdf-download"]',
                'a[href*="stamp.jsp"]'
            ]
            
            for selector in download_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    logger.info(f"Found {len(elements)} elements for selector: {selector}")
                    
                    for element in elements:
                        if await element.is_visible():
                            text = await element.text_content()
                            logger.info(f"Clicking element: {selector} (text: {text})")
                            await element.click()
                            await page.wait_for_timeout(3000)
                            
                            # Check if we navigated to a PDF
                            if page.url.endswith('.pdf') or 'stamp.jsp' in page.url:
                                logger.info(f"Navigated to: {page.url}")
                                return True
                except Exception as e:
                    logger.error(f"Error with selector {selector}: {e}")
            
            logger.error("Could not find working PDF download method")
            return False
            
        except Exception as e:
            logger.error(f"Debug session failed: {e}")
            await page.screenshot(path=debug_dir / "error_final_state.png")
            return False
        finally:
            # Keep browser open for manual inspection
            logger.info("Browser will remain open for 30 seconds for manual inspection...")
            await asyncio.sleep(30)
            await browser.close()

async def main():
    """Run the debug session."""
    success = await debug_ieee_download()
    if success:
        logger.info("✅ Debug session successful!")
    else:
        logger.error("❌ Debug session failed!")
    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)