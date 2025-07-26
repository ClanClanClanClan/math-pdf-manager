#!/usr/bin/env python3
"""
Simple SIAM Test
===============

Simplified test that bypasses the auth_manager and tests SIAM directly.
"""

import asyncio
import nest_asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("simple_siam")

nest_asyncio.apply()

async def simple_siam_test():
    from playwright.async_api import async_playwright
    
    # Get credentials
    from secure_credential_manager import get_credential_manager
    cm = get_credential_manager()
    username, password = cm.get_eth_credentials()
    
    output_dir = Path("simple_siam")
    output_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            # Go directly to SIAM URL that works
            siam_url = "https://epubs.siam.org/doi/10.1137/S0036142997325199"
            logger.info(f"Going to SIAM: {siam_url}")
            
            await page.goto(siam_url, wait_until='domcontentloaded', timeout=45000)
            await page.wait_for_timeout(3000)
            
            logger.info("✅ Connected to SIAM page")
            
            # Click institutional access
            access_link = await page.query_selector('a:has-text("Access via your Institution")')
            if access_link:
                await access_link.click()
                await page.wait_for_timeout(5000)
                logger.info("✅ Clicked institutional access")
                
                # Fill institution search
                try:
                    search_input = await page.wait_for_selector('#shibboleth_search input', timeout=10000)
                    await search_input.fill("ETH Zurich")
                    await search_input.press('Enter')
                    logger.info("✅ Searched for ETH Zurich")
                    await page.wait_for_timeout(5000)
                    
                    # Check if we're redirected to ETH login or elsewhere
                    current_url = page.url
                    logger.info(f"After search URL: {current_url}")
                    
                    if 'ethz' in current_url or 'aai' in current_url:
                        # ETH login page
                        logger.info("🎯 At ETH login page - filling credentials")
                        await page.fill('[name="j_username"], [id="username"]', username)
                        await page.fill('[name="j_password"], [id="password"]', password)
                        
                        submit = await page.query_selector('[type="submit"]')
                        await submit.click()
                        logger.info("✅ Submitted ETH login")
                        
                        # Wait for redirect back to SIAM
                        await page.wait_for_timeout(8000)
                        final_url = page.url
                        logger.info(f"Final URL: {final_url}")
                        
                        if 'siam' in final_url:
                            logger.info("🎉 AUTHENTICATION SUCCESSFUL!")
                            
                            # Now try to download PDF
                            pdf_selectors = [
                                'a:has-text("PDF")',
                                'button:has-text("PDF")',
                                'a[href*=".pdf"]',
                                '[href*="pdf"]',
                                'a:has-text("Download")'
                            ]
                            
                            for selector in pdf_selectors:
                                try:
                                    pdf_element = await page.query_selector(selector)
                                    if pdf_element:
                                        text = await pdf_element.text_content()
                                        href = await pdf_element.get_attribute('href')
                                        logger.info(f"Found PDF option: '{text}' -> {href}")
                                        
                                        if href and 'pdf' in href.lower():
                                            if not href.startswith('http'):
                                                href = f"https://epubs.siam.org{href}"
                                            
                                            logger.info(f"🎯 Downloading PDF: {href}")
                                            pdf_response = await page.goto(href, timeout=30000)
                                            content = await pdf_response.body()
                                            
                                            if content.startswith(b'%PDF'):
                                                pdf_path = output_dir / "SIAM_PAPER.pdf"
                                                with open(pdf_path, 'wb') as f:
                                                    f.write(content)
                                                
                                                if pdf_path.exists():
                                                    file_size = pdf_path.stat().st_size
                                                    logger.info(f"🏆 SIAM PDF SAVED: {pdf_path}")
                                                    logger.info(f"📊 Size: {file_size} bytes")
                                                    
                                                    # Verify it's actually a PDF
                                                    with open(pdf_path, 'rb') as f:
                                                        header = f.read(4)
                                                        if header == b'%PDF':
                                                            logger.info("✅ VERIFIED: Valid PDF file!")
                                                            return True
                                                        else:
                                                            logger.warning("⚠️ File is not a valid PDF")
                                            else:
                                                logger.warning(f"Not PDF content: {content[:100]}")
                                            
                                            break
                                except Exception as e:
                                    logger.debug(f"PDF selector failed: {e}")
                                    continue
                        else:
                            logger.error(f"Authentication failed - not at SIAM: {final_url}")
                    else:
                        logger.error(f"Not redirected to ETH login: {current_url}")
                        
                except Exception as e:
                    logger.error(f"Institution search failed: {e}")
            else:
                logger.error("Institutional access link not found")
            
            return False
            
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            logger.info("Browser open for 10 seconds...")
            await asyncio.sleep(10)
            await browser.close()

if __name__ == "__main__":
    success = asyncio.run(simple_siam_test())
    if success:
        logger.info("🏆 SIAM TEST SUCCESSFUL!")
    else:
        logger.error("💥 SIAM test failed")