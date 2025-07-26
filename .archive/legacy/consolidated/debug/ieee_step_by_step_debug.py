#!/usr/bin/env python3
"""
IEEE Step by Step Debug
=======================

Debug each step of the IEEE authentication flow.
"""

import asyncio
import nest_asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("step_debug")

nest_asyncio.apply()

async def step_by_step_debug():
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
    
    output_dir = Path("step_debug")
    output_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            logger.info("=" * 60)
            logger.info("STEP 1: Navigate to IEEE")
            logger.info("=" * 60)
            await page.goto(ieee_url, wait_until='networkidle')
            await page.wait_for_timeout(3000)
            await page.screenshot(path=output_dir / "01_ieee_page.png")
            logger.info(f"Current URL: {page.url}")
            
            logger.info("=" * 60)
            logger.info("STEP 2: Accept Cookies")
            logger.info("=" * 60)
            accept = await page.query_selector('button:has-text("Accept All")')
            if accept:
                await accept.click()
                await page.wait_for_timeout(1000)
                logger.info("Cookies accepted")
            else:
                logger.info("No cookie banner found")
            await page.screenshot(path=output_dir / "02_after_cookies.png")
            
            logger.info("=" * 60)
            logger.info("STEP 3: Click Institutional Sign In")
            logger.info("=" * 60)
            inst = await page.wait_for_selector('a:has-text("Institutional Sign In")')
            await inst.click()
            await page.wait_for_timeout(3000)
            await page.screenshot(path=output_dir / "03_modal_open.png")
            logger.info("Modal should be open now")
            
            logger.info("=" * 60)
            logger.info("STEP 4: Click Access Through Your Institution")
            logger.info("=" * 60)
            
            # Try the exact selector
            access_button = await page.query_selector('button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn')
            if access_button:
                logger.info("Found button with exact class selector")
                await access_button.click()
                await page.wait_for_timeout(3000)
                await page.screenshot(path=output_dir / "04_after_button_click.png")
                
                # Check what happened
                current_url = page.url
                logger.info(f"Current URL after button click: {current_url}")
                
                # Check for new windows
                all_pages = context.pages
                logger.info(f"Number of browser pages: {len(all_pages)}")
                
                if len(all_pages) > 1:
                    logger.info("New window/tab opened!")
                    new_page = all_pages[-1]
                    await new_page.wait_for_load_state('networkidle')
                    logger.info(f"New page URL: {new_page.url}")
                    page = new_page  # Switch to new page
                    await page.screenshot(path=output_dir / "05_new_window.png")
                
                # Check for iframe
                iframes = await page.query_selector_all('iframe')
                logger.info(f"Found {len(iframes)} iframes")
                
                for i, iframe in enumerate(iframes):
                    src = await iframe.get_attribute('src')
                    if src and 'seamless' in src:
                        logger.info(f"SeamlessAccess iframe {i}: {src}")
                        frame = await iframe.content_frame()
                        if frame:
                            content = await frame.content()
                            logger.info(f"Iframe content length: {len(content)}")
                            if len(content) > 100:
                                logger.info("Iframe has content, switching to it")
                                page = frame
                                break
                
                logger.info("=" * 60)
                logger.info("STEP 5: Search for ETH")
                logger.info("=" * 60)
                
                # Look for search input
                search_selectors = [
                    'input[type="search"]',
                    'input[placeholder*="institution"]',
                    'input[placeholder*="organization"]',
                    'input[type="text"]'
                ]
                
                search_input = None
                for selector in search_selectors:
                    try:
                        search_input = await page.wait_for_selector(selector, timeout=3000)
                        if search_input and await search_input.is_visible():
                            logger.info(f"Found search input: {selector}")
                            break
                    except Exception as e:
                        logger.debug(f"Selector {selector} not found")
                        continue
                
                if search_input:
                    logger.info("Filling search with 'ETH Zurich'")
                    await search_input.fill("ETH Zurich")
                    await page.wait_for_timeout(2000)
                    
                    if hasattr(page, 'screenshot'):
                        await page.screenshot(path=output_dir / "06_after_search.png")
                    
                    logger.info("=" * 60)
                    logger.info("STEP 6: Click ETH Option")
                    logger.info("=" * 60)
                    
                    # Look for ETH in results
                    eth_selectors = [
                        'text="ETH Zurich"',
                        'li:has-text("ETH Zurich")',
                        'div:has-text("ETH Zurich")',
                        'a:has-text("ETH")',
                        '[value*="ethz"]'
                    ]
                    
                    eth_found = False
                    for selector in eth_selectors:
                        try:
                            eth_option = await page.wait_for_selector(selector, timeout=3000)
                            if eth_option:
                                logger.info(f"Found ETH option: {selector}")
                                await eth_option.click()
                                eth_found = True
                                break
                        except Exception as e:
                            logger.debug(f"ETH selector {selector} not found")
                            continue
                    
                    if eth_found:
                        logger.info("Clicked ETH option, waiting for redirect...")
                        await page.wait_for_timeout(5000)
                        
                        # Switch back to main page if needed
                        main_page = context.pages[0]
                        current_url = main_page.url
                        logger.info(f"Main page URL: {current_url}")
                        
                        if 'ethz' in current_url or 'aai' in current_url:
                            logger.info("Redirected to ETH login page!")
                            page = main_page
                            
                            logger.info("=" * 60)
                            logger.info("STEP 7: Fill ETH Login")
                            logger.info("=" * 60)
                            
                            await page.screenshot(path=output_dir / "07_eth_login.png")
                            
                            # Fill login form
                            username_field = await page.wait_for_selector('[name="j_username"], [id="username"]', timeout=10000)
                            password_field = await page.wait_for_selector('[name="j_password"], [id="password"]', timeout=10000)
                            
                            await username_field.fill(username)
                            await password_field.fill(password)
                            
                            # Submit
                            submit = await page.query_selector('[type="submit"]')
                            await submit.click()
                            
                            logger.info("Submitted login, waiting for authentication...")
                            await page.wait_for_timeout(5000)
                            
                            logger.info("=" * 60)
                            logger.info("STEP 8: Check Authentication Result")
                            logger.info("=" * 60)
                            
                            final_url = page.url
                            logger.info(f"Final URL: {final_url}")
                            await page.screenshot(path=output_dir / "08_final_state.png")
                            
                            if 'ieee' in final_url:
                                logger.info("✅ Successfully authenticated and returned to IEEE!")
                                return True
                            else:
                                logger.warning(f"Authentication may have failed, final URL: {final_url}")
                        else:
                            logger.warning(f"Not at ETH login page, current URL: {current_url}")
                    else:
                        logger.warning("Could not find ETH option")
                        
                        # Debug what's available
                        if hasattr(page, 'content'):
                            content = await page.content()
                            logger.debug(f"Page content preview: {content[:500]}...")
                else:
                    logger.warning("Could not find search input")
                    
                    # Debug what's available
                    if hasattr(page, 'content'):
                        content = await page.content()
                        logger.debug(f"Page content preview: {content[:500]}...")
            else:
                logger.error("Could not find access button!")
            
            # Keep browser open for inspection
            logger.info("Browser will stay open for 30 seconds...")
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()
            await page.screenshot(path=output_dir / "error.png")
            return False
        finally:
            await browser.close()

if __name__ == "__main__":
    success = asyncio.run(step_by_step_debug())
    if success:
        logger.info("✅ Authentication successful!")
    else:
        logger.error("❌ Authentication failed!")