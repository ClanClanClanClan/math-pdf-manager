#!/usr/bin/env python3
"""
IEEE Manual Authentication Helper
=================================

Opens browser and guides through manual authentication.
"""

import os
import asyncio
import nest_asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ieee_manual")

nest_asyncio.apply()

async def manual_ieee_auth():
    """Manual IEEE authentication with guidance."""
    from playwright.async_api import async_playwright
    
    # Get credentials
    from secure_credential_manager import get_credential_manager
    cm = get_credential_manager()
    username, password = cm.get_eth_credentials()
    
    if not username or not password:
        logger.error("No ETH credentials found!")
        return False
    
    logger.info(f"ETH Username: {username}")
    logger.info(f"ETH Password: {'*' * len(password)}")
    
    test_doi = "10.1109/JPROC.2018.2820126"
    ieee_url = f"https://doi.org/{test_doi}"
    
    output_dir = Path("ieee_manual_output")
    output_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Navigate to IEEE
            logger.info("Navigating to IEEE document...")
            await page.goto(ieee_url, wait_until='networkidle')
            
            # Extract document ID
            await page.wait_for_timeout(3000)
            current_url = page.url
            doc_id = current_url.split('/document/')[1].split('/')[0] if '/document/' in current_url else None
            logger.info(f"Document ID: {doc_id}")
            
            # Instructions for manual auth
            logger.info("\n" + "="*60)
            logger.info("MANUAL AUTHENTICATION INSTRUCTIONS:")
            logger.info("1. Accept any cookie consent banners")
            logger.info("2. Click 'Institutional Sign In'")
            logger.info("3. In the popup, click 'Access through your institution'")
            logger.info("4. Search for 'ETH Zurich' and click it")
            logger.info("5. On the ETH login page:")
            logger.info(f"   - Username: {username}")
            logger.info(f"   - Password: [use your password]")
            logger.info("6. Submit the login form")
            logger.info("7. Wait for redirect back to IEEE")
            logger.info("="*60 + "\n")
            
            logger.info("Waiting 60 seconds for manual authentication...")
            logger.info("The script will then attempt to download the PDF.")
            
            # Wait for manual auth
            await asyncio.sleep(60)
            
            # Check if authenticated
            current_url = page.url
            logger.info(f"Current URL after wait: {current_url}")
            
            if 'ieee' in current_url and doc_id:
                logger.info("Attempting PDF download...")
                
                # Try stamp URL
                stamp_url = f"https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber={doc_id}"
                logger.info(f"Navigating to stamp URL: {stamp_url}")
                
                response = await page.goto(stamp_url, wait_until='networkidle')
                
                if response:
                    content = await response.body()
                    if content.startswith(b'%PDF'):
                        logger.info("✅ SUCCESS! Downloaded PDF")
                        pdf_path = output_dir / f"ieee_{doc_id}.pdf"
                        with open(pdf_path, 'wb') as f:
                            f.write(content)
                        logger.info(f"PDF saved to: {pdf_path}")
                        return True
                    else:
                        logger.info("Stamp URL returned HTML, not PDF")
                        
                        # Take screenshot
                        await page.screenshot(path=output_dir / "stamp_page.png")
                        
                        # Look for PDF in iframes
                        iframes = await page.query_selector_all('iframe')
                        logger.info(f"Found {len(iframes)} iframes")
                        
                        for i, iframe in enumerate(iframes):
                            src = await iframe.get_attribute('src')
                            if src and ('.pdf' in src or 'getPDF' in src):
                                logger.info(f"Found potential PDF iframe: {src}")
                                
                                if not src.startswith('http'):
                                    src = f"https://ieeexplore.ieee.org{src}"
                                
                                pdf_response = await page.goto(src)
                                if pdf_response:
                                    pdf_content = await pdf_response.body()
                                    if pdf_content.startswith(b'%PDF'):
                                        logger.info("✅ SUCCESS! Downloaded PDF from iframe")
                                        pdf_path = output_dir / f"ieee_{doc_id}.pdf"
                                        with open(pdf_path, 'wb') as f:
                                            f.write(pdf_content)
                                        logger.info(f"PDF saved to: {pdf_path}")
                                        return True
            
            logger.error("Could not download PDF")
            return False
            
        except Exception as e:
            logger.error(f"Error: {e}")
            return False
        finally:
            logger.info("Browser will remain open for inspection...")
            await asyncio.sleep(30)
            await browser.close()

if __name__ == "__main__":
    success = asyncio.run(manual_ieee_auth())
    exit(0 if success else 1)