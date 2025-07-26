#!/usr/bin/env python3
"""
IEEE Direct Discovery
====================

Try direct SeamlessAccess discovery URL.
"""

import asyncio
import nest_asyncio
import logging
from pathlib import Path
from urllib.parse import quote

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("direct_discovery")

nest_asyncio.apply()

async def direct_discovery_test():
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
    
    output_dir = Path("direct_discovery")
    output_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Try to construct the SeamlessAccess discovery URL
            # This is often in the format: https://service.seamlessaccess.org/ds/?entityID=<entity>&return=<return_url>
            
            # First, let's try to go directly to SeamlessAccess discovery
            logger.info("Step 1: Going directly to SeamlessAccess discovery...")
            discovery_url = "https://service.seamlessaccess.org/ds/"
            
            await page.goto(discovery_url, wait_until='networkidle')
            await page.wait_for_timeout(3000)
            await page.screenshot(path=output_dir / "01_discovery.png")
            
            # Look for search input on the discovery page
            logger.info("Step 2: Looking for search input on discovery page...")
            
            search_selectors = [
                'input[aria-label="Search for your Institution"]',
                'input.inst-typeahead-input',
                'input[role="search"]',
                'input[type="search"]',
                'input[placeholder*="institution"]',
                'input[type="text"]'
            ]
            
            search_input = None
            for selector in search_selectors:
                try:
                    search_input = await page.wait_for_selector(selector, timeout=3000)
                    if search_input and await search_input.is_visible():
                        logger.info(f"✅ Found search input: {selector}")
                        break
                except Exception as e:
                    continue
            
            if search_input:
                logger.info("Step 3: Filling search with 'ETH Zurich'...")
                await search_input.fill("ETH Zurich")
                await page.wait_for_timeout(3000)
                await page.screenshot(path=output_dir / "02_after_search.png")
                
                # Look for ETH in results
                logger.info("Step 4: Looking for ETH in results...")
                eth_selectors = [
                    'text="ETH Zurich"',
                    'li:has-text("ETH Zurich")',
                    'div:has-text("ETH Zurich")',
                    'a:has-text("ETH Zurich")',
                    'button:has-text("ETH Zurich")',
                    'text=/ETH.*Zurich/i'
                ]
                
                eth_option = None
                for selector in eth_selectors:
                    try:
                        eth_option = await page.wait_for_selector(selector, timeout=5000)
                        if eth_option:
                            logger.info(f"✅ Found ETH: {selector}")
                            break
                    except Exception as e:
                        continue
                
                if eth_option:
                    logger.info("Step 5: Clicking ETH Zurich...")
                    await eth_option.click()
                    await page.wait_for_timeout(3000)
                    await page.screenshot(path=output_dir / "03_after_eth_click.png")
                    
                    current_url = page.url
                    logger.info(f"Current URL: {current_url}")
                    
                    # If we're redirected to ETH, continue with login
                    if 'ethz' in current_url or 'aai' in current_url:
                        logger.info("Step 6: At ETH login page!")
                        
                        # Fill credentials
                        await page.fill('[name="j_username"], [id="username"]', username)
                        await page.fill('[name="j_password"], [id="password"]', password)
                        
                        # Submit
                        submit = await page.query_selector('[type="submit"]')
                        await submit.click()
                        
                        logger.info("Step 7: Authenticating...")
                        await page.wait_for_timeout(5000)
                        
                        final_url = page.url
                        logger.info(f"Final URL: {final_url}")
                        
                        # Now navigate to IEEE with authenticated session
                        logger.info("Step 8: Navigating to IEEE with authenticated session...")
                        await page.goto(ieee_url, wait_until='networkidle')
                        await page.wait_for_timeout(3000)
                        
                        current_url = page.url
                        logger.info(f"IEEE URL: {current_url}")
                        
                        if 'ieee' in current_url:
                            logger.info("✅ Successfully at IEEE with authentication!")
                            
                            # Try PDF download
                            doc_id = current_url.split('/document/')[1].split('/')[0] if '/document/' in current_url else None
                            if doc_id:
                                stamp_url = f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={doc_id}"
                                logger.info(f"Step 9: Trying PDF download: {stamp_url}")
                                
                                response = await page.goto(stamp_url, wait_until='networkidle')
                                content = await response.body()
                                
                                if content.startswith(b'%PDF'):
                                    pdf_path = output_dir / "ieee_paper.pdf"
                                    with open(pdf_path, 'wb') as f:
                                        f.write(content)
                                    logger.info(f"✅ PDF downloaded: {pdf_path}")
                                    return True
                                else:
                                    logger.info("Stamp page returned HTML, checking for PDF iframe...")
                                    iframe = await page.query_selector('iframe[src*="pdf"]')
                                    if iframe:
                                        src = await iframe.get_attribute('src')
                                        if not src.startswith('http'):
                                            src = f"https://ieeexplore.ieee.org{src}"
                                        
                                        pdf_response = await page.goto(src)
                                        pdf_content = await pdf_response.body()
                                        
                                        if pdf_content.startswith(b'%PDF'):
                                            pdf_path = output_dir / "ieee_paper.pdf"
                                            with open(pdf_path, 'wb') as f:
                                                f.write(pdf_content)
                                            logger.info(f"✅ PDF downloaded from iframe: {pdf_path}")
                                            return True
                    else:
                        logger.warning(f"Not redirected to ETH: {current_url}")
                        
                        # Maybe we need to specify IEEE as the service provider
                        # Try alternative approach with IEEE entity ID
                        logger.info("Trying with IEEE entity ID...")
                        
                        # Common IEEE entity IDs for Shibboleth
                        ieee_entities = [
                            "https://ieeexplore.ieee.org",
                            "https://shibboleth.ieee.org",
                            "urn:mace:incommon:ieeexplore.ieee.org"
                        ]
                        
                        for entity in ieee_entities:
                            try:
                                discovery_with_entity = f"https://service.seamlessaccess.org/ds/?entityID={quote(entity)}&return={quote(ieee_url)}"
                                logger.info(f"Trying: {discovery_with_entity}")
                                
                                await page.goto(discovery_with_entity, wait_until='networkidle')
                                await page.wait_for_timeout(3000)
                                
                                # Check if this loads differently
                                current_url = page.url
                                if current_url != discovery_url:
                                    logger.info(f"Different URL loaded: {current_url}")
                                    break
                            except Exception as e:
                                continue
                else:
                    logger.warning("ETH option not found")
                    
                    # Debug what's available
                    text_content = await page.text_content('body')
                    logger.info(f"Page content: {text_content[:300]}...")
            else:
                logger.warning("Search input not found on discovery page")
                
                # Maybe the discovery page works differently
                # Check page content
                content = await page.content()
                with open(output_dir / "discovery_page.html", "w") as f:
                    f.write(content)
                logger.info("Discovery page content saved")
            
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
    success = asyncio.run(direct_discovery_test())
    if success:
        logger.info("✅ Direct discovery approach successful!")
    else:
        logger.error("❌ Direct discovery approach failed!")