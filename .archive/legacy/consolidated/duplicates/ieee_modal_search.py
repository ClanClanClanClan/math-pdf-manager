#!/usr/bin/env python3
"""
IEEE Modal Search Test
=====================

Test the modal search functionality.
"""

import asyncio
import nest_asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("modal_search")

nest_asyncio.apply()

async def test_modal_search():
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
    
    output_dir = Path("modal_search")
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
            await page.screenshot(path=output_dir / "01_modal_opened.png")
            
            # Click Access Through Your Institution button
            access_btn = await page.wait_for_selector('button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn')
            logger.info("Found access button, clicking...")
            await access_btn.click()
            await page.wait_for_timeout(3000)
            await page.screenshot(path=output_dir / "02_after_button_click.png")
            
            # Now look for the search input in the modal
            logger.info("Looking for search input in modal...")
            
            modal_search_selectors = [
                'input[aria-label="Search for your Institution"]',
                'input.inst-typeahead-input',
                'input[role="search"]'
            ]
            
            search_input = None
            for attempt in range(5):
                logger.info(f"Search attempt {attempt + 1}/5...")
                await page.wait_for_timeout(3000)
                
                for selector in modal_search_selectors:
                    try:
                        search_input = await page.query_selector(selector)
                        if search_input and await search_input.is_visible():
                            logger.info(f"✅ Found search input: {selector}")
                            break
                    except Exception as e:
                        continue
                
                if search_input:
                    break
                
                await page.screenshot(path=output_dir / f"03_attempt_{attempt + 1}.png")
            
            if search_input:
                logger.info("✅ Filling search with 'ETH Zurich'...")
                await search_input.fill("ETH Zurich")
                await page.wait_for_timeout(3000)
                await page.screenshot(path=output_dir / "04_after_search.png")
                
                # Look for ETH in results
                logger.info("Looking for ETH Zurich in results...")
                eth_selectors = [
                    'text="ETH Zurich"',
                    'li:has-text("ETH Zurich")',
                    'div:has-text("ETH Zurich")',
                    'a:has-text("ETH Zurich")',
                    'button:has-text("ETH Zurich")'
                ]
                
                eth_option = None
                for selector in eth_selectors:
                    try:
                        eth_option = await page.wait_for_selector(selector, timeout=5000)
                        if eth_option:
                            logger.info(f"✅ Found ETH option: {selector}")
                            break
                    except Exception as e:
                        continue
                
                if eth_option:
                    logger.info("✅ Clicking ETH Zurich...")
                    await eth_option.click()
                    await page.wait_for_timeout(5000)
                    await page.screenshot(path=output_dir / "05_after_eth_click.png")
                    
                    current_url = page.url
                    logger.info(f"Current URL: {current_url}")
                    
                    if 'ethz' in current_url or 'aai' in current_url:
                        logger.info("✅ Redirected to ETH login!")
                        
                        # Fill login form
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
                            
                            # Try PDF download
                            doc_id = final_url.split('/document/')[1].split('/')[0] if '/document/' in final_url else None
                            if doc_id:
                                stamp_url = f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={doc_id}"
                                logger.info(f"Trying PDF download: {stamp_url}")
                                
                                response = await page.goto(stamp_url, wait_until='networkidle')
                                content = await response.body()
                                
                                if content.startswith(b'%PDF'):
                                    pdf_path = output_dir / "ieee_paper.pdf"
                                    with open(pdf_path, 'wb') as f:
                                        f.write(content)
                                    logger.info(f"✅ PDF downloaded: {pdf_path}")
                                    return True
                        else:
                            logger.warning(f"Not returned to IEEE: {final_url}")
                    else:
                        logger.warning(f"Not redirected to ETH: {current_url}")
                else:
                    logger.warning("ETH option not found")
            else:
                logger.warning("Search input not found in modal")
            
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
    success = asyncio.run(test_modal_search())
    if success:
        logger.info("✅ Modal search test successful!")
    else:
        logger.error("❌ Modal search test failed!")