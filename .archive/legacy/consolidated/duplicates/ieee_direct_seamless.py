#!/usr/bin/env python3
"""
IEEE Direct SeamlessAccess
==========================

Try going directly to SeamlessAccess discovery service.
"""

import asyncio
import nest_asyncio
import logging
from pathlib import Path
from urllib.parse import quote

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("direct_seamless")

nest_asyncio.apply()

async def direct_seamless_test():
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
    
    output_dir = Path("direct_seamless")
    output_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # First, let's understand the IEEE auth flow better
            logger.info("Step 1: Navigate to IEEE...")
            await page.goto(ieee_url, wait_until='networkidle')
            await page.wait_for_timeout(3000)
            
            # Accept cookies
            logger.info("Step 2: Accept cookies...")
            accept = await page.query_selector('button:has-text("Accept All")')
            if accept:
                await accept.click()
                await page.wait_for_timeout(1000)
            
            # Instead of clicking Institutional Sign In, let's try the direct approach
            # Many publishers use a direct link to their discovery service
            logger.info("Step 3: Looking for alternative auth methods...")
            
            # Check all links on the page
            all_links = await page.query_selector_all('a')
            for link in all_links:
                href = await link.get_attribute('href')
                text = await link.text_content()
                if href and ('shibboleth' in href.lower() or 'wayf' in href.lower() or 'discovery' in href.lower()):
                    logger.info(f"Found potential auth link: {text} -> {href}")
            
            # Try the IEEE Shibboleth URL directly
            # IEEE might have a direct Shibboleth endpoint
            logger.info("Step 4: Trying direct Shibboleth approach...")
            
            # Common IEEE Shibboleth patterns
            shibboleth_urls = [
                f"https://ieeexplore.ieee.org/servlet/wayf.jsp?target={quote(ieee_url)}",
                f"https://ieeexplore.ieee.org/Shibboleth.sso/Login?target={quote(ieee_url)}",
                f"https://ieeexplore.ieee.org/servlet/Login?logout=false&url={quote(ieee_url)}"
            ]
            
            for shib_url in shibboleth_urls:
                logger.info(f"Trying: {shib_url}")
                try:
                    response = await page.goto(shib_url, wait_until='networkidle', timeout=10000)
                    await page.wait_for_timeout(2000)
                    
                    current_url = page.url
                    logger.info(f"Current URL: {current_url}")
                    
                    if 'wayf' in current_url or 'discovery' in current_url or 'seamless' in current_url:
                        logger.info("✅ Reached discovery service!")
                        break
                except Exception as e:
                    logger.warning(f"Failed: {e}")
                    continue
            
            # If we're at a discovery service, search for ETH
            if 'wayf' in page.url or 'discovery' in page.url or 'seamless' in page.url:
                logger.info("Step 5: At discovery service, searching for ETH...")
                
                # Look for search input
                search_input = await page.query_selector('input[type="search"], input[type="text"]')
                if search_input:
                    await search_input.fill("ETH Zurich")
                    await page.wait_for_timeout(2000)
                    
                    # Click ETH
                    eth_option = await page.wait_for_selector('text="ETH Zurich"', timeout=5000)
                    await eth_option.click()
                    await page.wait_for_load_state('networkidle')
                    
                    # Now we should be at ETH login
                    if 'ethz' in page.url or 'aai' in page.url:
                        logger.info("Step 6: At ETH login page!")
                        
                        # Fill credentials
                        await page.fill('input[name="j_username"], input[id="username"]', username)
                        await page.fill('input[name="j_password"], input[id="password"]', password)
                        
                        # Submit
                        submit = await page.query_selector('[type="submit"]')
                        await submit.click()
                        
                        # Wait for auth
                        logger.info("Step 7: Authenticating...")
                        await page.wait_for_timeout(5000)
                        
                        # Check if we're back at IEEE
                        if 'ieee' in page.url:
                            logger.info("✅ Successfully authenticated!")
                            
                            # Try to download PDF
                            doc_id = page.url.split('/document/')[1].split('/')[0] if '/document/' in page.url else None
                            if doc_id:
                                stamp_url = f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={doc_id}"
                                logger.info(f"Step 8: Trying PDF download from: {stamp_url}")
                                
                                response = await page.goto(stamp_url, wait_until='networkidle')
                                content = await response.body()
                                
                                if content.startswith(b'%PDF'):
                                    pdf_path = output_dir / "ieee_paper.pdf"
                                    with open(pdf_path, 'wb') as f:
                                        f.write(content)
                                    logger.info(f"✅ PDF downloaded to: {pdf_path}")
                                    return True
            else:
                # Fall back to the modal approach but with better handling
                logger.info("Direct approach failed, trying modal approach...")
                
                # Go back to IEEE page
                await page.goto(ieee_url, wait_until='networkidle')
                await page.wait_for_timeout(2000)
                
                # Click institutional sign in
                inst = await page.wait_for_selector('a:has-text("Institutional Sign In")')
                await inst.click()
                await page.wait_for_timeout(3000)
                
                # Look for the modal and examine it more carefully
                modal = await page.query_selector('ngb-modal-window')
                if modal:
                    # Get the modal's HTML to understand it better
                    modal_html = await modal.inner_html()
                    logger.info("Modal HTML preview:")
                    logger.info(modal_html[:500] + "...")
                    
                    # Save full HTML for analysis
                    with open(output_dir / "modal.html", "w") as f:
                        f.write(modal_html)
                    logger.info(f"Full modal HTML saved to {output_dir}/modal.html")
            
            # Take final screenshot
            await page.screenshot(path=output_dir / "final_state.png")
            logger.info("Browser will stay open for inspection...")
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            await browser.close()

if __name__ == "__main__":
    success = asyncio.run(direct_seamless_test())
    if success:
        logger.info("✅ Test successful!")
    else:
        logger.error("❌ Test failed!")