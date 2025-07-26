#!/usr/bin/env python3
"""
IEEE Enter Search Test
=====================

Test pressing Enter after search and clicking the result.
"""

import asyncio
import nest_asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("enter_search")

nest_asyncio.apply()

async def test_enter_search():
    from playwright.async_api import async_playwright
    
    # Get credentials
    from secure_credential_manager import get_credential_manager
    cm = get_credential_manager()
    username, password = cm.get_eth_credentials()
    
    if not username or not password:
        logger.error("No ETH credentials found!")
        return False
    
    test_doi = "10.1109/JPROC.2018.2820126"
    ieee_url = f"https://doi.org/{test_doi}"
    
    output_dir = Path("enter_search")
    output_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            logger.info("Navigate to IEEE...")
            await page.goto(ieee_url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(3000)
            
            # Accept cookies
            accept = await page.query_selector('button:has-text("Accept All")')
            if accept:
                await accept.click()
                await page.wait_for_timeout(1000)
            
            # Click institutional sign in
            inst = await page.wait_for_selector('a:has-text("Institutional Sign In")')
            await inst.click()
            await page.wait_for_timeout(3000)
            
            # Click Access Through Your Institution button
            access_btn = await page.wait_for_selector('button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn')
            logger.info("Clicking Access Through Your Institution...")
            await access_btn.click()
            await page.wait_for_timeout(3000)
            
            # Find and fill search input
            search_input = await page.wait_for_selector('input[aria-label="Search for your Institution"]', timeout=10000)
            logger.info("✅ Found search input, filling with 'ETH Zurich'...")
            await search_input.fill("ETH Zurich")
            
            # Press Enter to trigger search
            logger.info("Pressing Enter to search...")
            await search_input.press('Enter')
            await page.wait_for_timeout(3000)
            
            await page.screenshot(path=output_dir / "after_enter.png")
            
            # Look for the ETH Zurich result link
            logger.info("Looking for ETH Zurich result...")
            
            # From the HTML, the result appears as a link with specific classes
            eth_selectors = [
                'a[id*="ETH Zurich"]',
                'a.stats-Global_Inst_signin_typeahead:has-text("ETH Zurich")',
                'a:has-text("ETH Zurich - ETH Zurich")',
                'a[href*="wayf.jsp"]:has-text("ETH")',
                '.selection-item a:has-text("ETH")',
                'text="ETH Zurich - ETH Zurich"'
            ]
            
            eth_link = None
            for selector in eth_selectors:
                try:
                    eth_link = await page.wait_for_selector(selector, timeout=3000)
                    if eth_link:
                        logger.info(f"✅ Found ETH link: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Selector failed: {selector}")
                    continue
            
            if eth_link:
                logger.info("✅ Clicking ETH Zurich link...")
                await eth_link.click()
                await page.wait_for_timeout(5000)
                
                current_url = page.url
                logger.info(f"Current URL: {current_url}")
                
                if 'ethz' in current_url or 'aai' in current_url:
                    logger.info("✅ Redirected to ETH login!")
                    await page.screenshot(path=output_dir / "eth_login.png")
                    
                    # Fill login form
                    logger.info("Filling ETH credentials...")
                    await page.fill('[name="j_username"], [id="username"]', username)
                    await page.fill('[name="j_password"], [id="password"]', password)
                    
                    # Submit
                    submit = await page.query_selector('[type="submit"]')
                    await submit.click()
                    
                    logger.info("Authenticating...")
                    await page.wait_for_timeout(5000)
                    
                    final_url = page.url
                    logger.info(f"Final URL: {final_url}")
                    
                    if 'ieee' in final_url:
                        logger.info("✅ SUCCESS! Authenticated and returned to IEEE!")
                        await page.screenshot(path=output_dir / "back_to_ieee.png")
                        
                        # Try PDF download
                        doc_id = final_url.split('/document/')[1].split('/')[0] if '/document/' in final_url else None
                        if doc_id:
                            stamp_url = f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={doc_id}"
                            logger.info(f"Trying PDF download from: {stamp_url}")
                            
                            response = await page.goto(stamp_url, wait_until='networkidle')
                            content = await response.body()
                            
                            if content.startswith(b'%PDF'):
                                pdf_path = output_dir / "ieee_paper.pdf"
                                with open(pdf_path, 'wb') as f:
                                    f.write(content)
                                logger.info(f"✅ PDF downloaded successfully: {pdf_path}")
                                return True
                            else:
                                logger.info("Stamp page returned HTML, checking for PDF iframe...")
                                
                                # Wait for page to load
                                await page.wait_for_timeout(3000)
                                
                                # Look for PDF iframe
                                iframe = await page.query_selector('iframe[src*="pdf"]')
                                if iframe:
                                    src = await iframe.get_attribute('src')
                                    if not src.startswith('http'):
                                        src = f"https://ieeexplore.ieee.org{src}"
                                    
                                    logger.info(f"Found PDF iframe: {src}")
                                    pdf_response = await page.goto(src)
                                    pdf_content = await pdf_response.body()
                                    
                                    if pdf_content.startswith(b'%PDF'):
                                        pdf_path = output_dir / "ieee_paper.pdf"
                                        with open(pdf_path, 'wb') as f:
                                            f.write(pdf_content)
                                        logger.info(f"✅ PDF downloaded from iframe: {pdf_path}")
                                        return True
                                else:
                                    logger.warning("No PDF iframe found")
                                    await page.screenshot(path=output_dir / "stamp_page.png")
                        else:
                            logger.warning("Could not extract document ID from URL")
                    else:
                        logger.warning(f"Not returned to IEEE: {final_url}")
                else:
                    logger.warning(f"Not redirected to ETH: {current_url}")
            else:
                logger.warning("ETH result link not found")
                
                # Debug what's available
                page_content = await page.content()
                with open(output_dir / "page_content.html", "w") as f:
                    f.write(page_content)
                logger.info("Page content saved for debugging")
            
            logger.info("Browser staying open for inspection...")
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            await browser.close()

if __name__ == "__main__":
    success = asyncio.run(test_enter_search())
    if success:
        logger.info("✅ Enter search test successful!")
    else:
        logger.error("❌ Enter search test failed!")