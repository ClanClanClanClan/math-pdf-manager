#!/usr/bin/env python3
"""
IEEE Final Working Test
=======================

Final test to verify IEEE authentication and PDF download works completely.
"""

import asyncio
import nest_asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("final_test")

nest_asyncio.apply()

async def final_ieee_test():
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
    
    output_dir = Path("final_test")
    output_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            logger.info("🚀 Starting IEEE authentication and download test...")
            
            # Navigate to IEEE
            logger.info("Step 1: Navigate to IEEE...")
            await page.goto(ieee_url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(3000)
            
            # Accept cookies
            accept = await page.query_selector('button:has-text("Accept All")')
            if accept:
                await accept.click()
                await page.wait_for_timeout(1000)
                logger.info("✅ Cookies accepted")
            
            # Start authentication
            logger.info("Step 2: Start authentication flow...")
            inst = await page.wait_for_selector('a:has-text("Institutional Sign In")', timeout=10000)
            await inst.click()
            await page.wait_for_timeout(3000)
            logger.info("✅ Clicked Institutional Sign In")
            
            # Click Access Through Your Institution
            access_btn = await page.wait_for_selector('button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn', timeout=10000)
            await access_btn.click()
            await page.wait_for_timeout(3000)
            logger.info("✅ Clicked Access Through Your Institution")
            
            # Fill search input
            search_input = await page.wait_for_selector('input[aria-label="Search for your Institution"]', timeout=10000)
            await search_input.fill("ETH Zurich")
            await search_input.press('Enter')
            await page.wait_for_timeout(3000)
            logger.info("✅ Searched for ETH Zurich")
            
            # Click ETH result
            eth_link = await page.wait_for_selector('a[id*="ETH Zurich"]', timeout=10000)
            await eth_link.click()
            await page.wait_for_timeout(5000)
            logger.info("✅ Clicked ETH Zurich")
            
            # Check if at ETH login
            current_url = page.url
            if 'ethz' in current_url or 'aai' in current_url:
                logger.info("✅ Reached ETH login page")
                
                # Fill credentials
                await page.fill('[name="j_username"], [id="username"]', username)
                await page.fill('[name="j_password"], [id="password"]', password)
                
                # Submit
                submit = await page.query_selector('[type="submit"]')
                await submit.click()
                
                logger.info("Step 3: Authenticating with ETH...")
                await page.wait_for_timeout(5000)
                
                # Check if back at IEEE
                final_url = page.url
                if 'ieee' in final_url:
                    logger.info("✅ Authentication successful - returned to IEEE!")
                    
                    # Extract document ID
                    doc_id = final_url.split('/document/')[1].split('/')[0] if '/document/' in final_url else None
                    if doc_id:
                        logger.info(f"📄 Document ID: {doc_id}")
                        
                        logger.info("Step 4: Attempting PDF download...")
                        
                        # Method 1: Try stamp URL
                        stamp_url = f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={doc_id}"
                        logger.info(f"Trying stamp URL: {stamp_url}")
                        
                        response = await page.goto(stamp_url, wait_until='domcontentloaded', timeout=30000)
                        await page.wait_for_timeout(3000)  # Wait for page to load
                        
                        # Check if we got PDF directly
                        content = await response.body()
                        if content.startswith(b'%PDF'):
                            pdf_path = output_dir / "ieee_paper.pdf"
                            with open(pdf_path, 'wb') as f:
                                f.write(content)
                            logger.info(f"✅ PDF downloaded directly: {pdf_path}")
                            logger.info(f"📊 PDF size: {len(content)} bytes")
                            return True
                        
                        # Method 2: Look for PDF iframe
                        logger.info("Looking for PDF iframe...")
                        await page.wait_for_timeout(5000)  # Wait for iframe to load
                        
                        iframes = await page.query_selector_all('iframe')
                        logger.info(f"Found {len(iframes)} iframes")
                        
                        for i, iframe in enumerate(iframes):
                            src = await iframe.get_attribute('src')
                            if src and ('pdf' in src.lower() or 'stamp' in src or 'getPDF' in src):
                                if not src.startswith('http'):
                                    src = f"https://ieeexplore.ieee.org{src}"
                                
                                logger.info(f"🎯 Found PDF iframe {i}: {src}")
                                
                                # Try to get PDF with retries
                                for attempt in range(3):
                                    try:
                                        logger.info(f"PDF download attempt {attempt + 1}/3...")
                                        await page.wait_for_timeout(2000)  # Wait for PDF generation
                                        
                                        iframe_response = await page.goto(src, wait_until='domcontentloaded', timeout=30000)
                                        iframe_content = await iframe_response.body()
                                        
                                        logger.info(f"Response: {iframe_response.status}, Content: {len(iframe_content)} bytes")
                                        
                                        if iframe_content.startswith(b'%PDF'):
                                            pdf_path = output_dir / "ieee_paper.pdf"
                                            with open(pdf_path, 'wb') as f:
                                                f.write(iframe_content)
                                            logger.info(f"✅ SUCCESS! PDF downloaded: {pdf_path}")
                                            logger.info(f"📊 PDF size: {len(iframe_content)} bytes")
                                            return True
                                        elif len(iframe_content) < 1000:
                                            # Probably loading page, wait more
                                            logger.info(f"Small response ({len(iframe_content)} bytes), waiting longer...")
                                            await page.wait_for_timeout(5000)
                                        else:
                                            logger.info(f"Got {len(iframe_content)} bytes but not PDF format")
                                            
                                    except Exception as e:
                                        logger.warning(f"Attempt {attempt + 1} failed: {e}")
                                
                                break  # Found the right iframe, stop looking
                        
                        # Method 3: Try download buttons on document page
                        logger.info("Trying download buttons on document page...")
                        doc_url = f"https://ieeexplore.ieee.org/document/{doc_id}"
                        await page.goto(doc_url, wait_until='domcontentloaded')
                        await page.wait_for_timeout(3000)
                        
                        # Look for PDF download links
                        pdf_links = await page.query_selector_all('a:has-text("PDF"), button:has-text("PDF")')
                        logger.info(f"Found {len(pdf_links)} PDF links/buttons")
                        
                        for i, link in enumerate(pdf_links):
                            try:
                                logger.info(f"Trying PDF link {i + 1}...")
                                await link.click()
                                await page.wait_for_timeout(3000)
                                
                                # Check if URL changed to PDF
                                if page.url.endswith('.pdf') or 'stamp.jsp' in page.url:
                                    response = await page.goto(page.url)
                                    content = await response.body()
                                    if content.startswith(b'%PDF'):
                                        pdf_path = output_dir / "ieee_paper.pdf"
                                        with open(pdf_path, 'wb') as f:
                                            f.write(content)
                                        logger.info(f"✅ PDF downloaded via button: {pdf_path}")
                                        return True
                            except Exception as e:
                                logger.warning(f"PDF link {i + 1} failed: {e}")
                        
                        logger.warning("Could not download PDF with any method")
                        await page.screenshot(path=output_dir / "final_state.png")
                        
                else:
                    logger.error(f"❌ Not returned to IEEE: {final_url}")
            else:
                logger.error(f"❌ Not at ETH login: {current_url}")
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            logger.info("Browser will close in 10 seconds...")
            await asyncio.sleep(10)
            await browser.close()

if __name__ == "__main__":
    success = asyncio.run(final_ieee_test())
    if success:
        logger.info("🎉 IEEE TEST PASSED! Authentication and PDF download working!")
    else:
        logger.error("💥 IEEE test failed")
    exit(0 if success else 1)