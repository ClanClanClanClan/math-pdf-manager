#!/usr/bin/env python3
"""
Project Euclid Investigation
============================

Investigate Project Euclid's authentication and download system.
"""

import asyncio
import nest_asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("euclid_invest")

nest_asyncio.apply()

async def investigate_euclid():
    from playwright.async_api import async_playwright
    
    # Test Project Euclid URLs
    test_urls = [
        "https://projecteuclid.org/",
        "https://projecteuclid.org/journals/annals-of-probability/volume-32/issue-1A/Concentration-of-the-spectral-measure-for-large-matrices/10.1214/aop/1078415845.full",  # Sample paper
        "https://doi.org/10.1214/aop/1078415845"  # DOI redirect to Euclid
    ]
    
    output_dir = Path("euclid_investigation")
    output_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            for i, url in enumerate(test_urls):
                logger.info(f"\n=== Testing Euclid URL {i+1}: {url} ===")
                
                try:
                    response = await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                    logger.info(f"✅ Connected: {response.status}")
                    
                    page_title = await page.title()
                    logger.info(f"Page title: {page_title}")
                    
                    # Look for authentication options
                    auth_selectors = [
                        'a:has-text("Sign In")',
                        'a:has-text("Login")', 
                        'a:has-text("Institutional")',
                        'a:has-text("Access")',
                        'a:has-text("Subscribe")',
                        '[href*="login"]',
                        '[href*="signin"]',
                        '[href*="institutional"]',
                        '[href*="shibboleth"]'
                    ]
                    
                    logger.info("Looking for authentication options...")
                    auth_found = []
                    
                    for selector in auth_selectors:
                        try:
                            elements = await page.query_selector_all(selector)
                            for element in elements:
                                text = await element.text_content()
                                href = await element.get_attribute('href')
                                if text and text.strip():
                                    auth_found.append(f"'{text.strip()}' -> {href}")
                        except Exception as e:
                            continue
                    
                    if auth_found:
                        logger.info("🔑 Authentication options found:")
                        for auth in auth_found[:5]:  # Show first 5
                            logger.info(f"  {auth}")
                    else:
                        logger.info("No authentication options found")
                    
                    # Look for PDF download options
                    pdf_selectors = [
                        'a:has-text("PDF")',
                        'button:has-text("PDF")',
                        'a[href*=".pdf"]',
                        '[href*="pdf"]',
                        '.pdf-download',
                        'a:has-text("Download")',
                        'a:has-text("Full Text")'
                    ]
                    
                    logger.info("Looking for PDF download options...")
                    pdf_found = []
                    
                    for selector in pdf_selectors:
                        try:
                            elements = await page.query_selector_all(selector)
                            for element in elements:
                                text = await element.text_content()
                                href = await element.get_attribute('href')
                                if text and text.strip():
                                    pdf_found.append(f"'{text.strip()}' -> {href}")
                        except Exception as e:
                            continue
                    
                    if pdf_found:
                        logger.info("📄 PDF options found:")
                        for pdf in pdf_found[:5]:
                            logger.info(f"  {pdf}")
                    else:
                        logger.info("No PDF options found")
                    
                    # Take screenshot
                    await page.screenshot(path=output_dir / f"euclid_{i+1}.png")
                    logger.info(f"📸 Screenshot saved: euclid_{i+1}.png")
                    
                    await page.wait_for_timeout(3000)
                    
                except Exception as e:
                    logger.error(f"❌ Failed to load {url}: {e}")
            
            logger.info("\n=== Project Euclid Investigation Complete ===")
            
        except Exception as e:
            logger.error(f"Error: {e}")
        finally:
            await asyncio.sleep(10)
            await browser.close()

if __name__ == "__main__":
    asyncio.run(investigate_euclid())