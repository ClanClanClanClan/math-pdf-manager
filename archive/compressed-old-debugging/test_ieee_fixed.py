#!/usr/bin/env python3
"""
Test Fixed IEEE Authentication
==============================

Test the modal-within-modal fix.
"""

import asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ieee_test")

async def test_ieee_auth():
    """Test IEEE authentication with modal fix."""
    from playwright.async_api import async_playwright
    
    test_doi = "10.1109/JPROC.2018.2820126"
    ieee_url = f"https://doi.org/{test_doi}"
    
    output_dir = Path("ieee_test_output")
    output_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Visible for debugging
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Navigate to IEEE
            logger.info("Navigating to IEEE document...")
            await page.goto(ieee_url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(5000)
            
            # Handle cookies
            logger.info("Accepting cookies...")
            accept_button = await page.query_selector('button:has-text("Accept All")')
            if accept_button:
                await accept_button.click()
                await page.wait_for_timeout(1000)
            
            # Click institutional sign in
            logger.info("Clicking Institutional Sign In...")
            inst_button = await page.wait_for_selector('a:has-text("Institutional Sign In")', timeout=10000)
            await inst_button.click()
            await page.wait_for_timeout(2000)
            
            # Find the first modal
            modal = await page.wait_for_selector('ngb-modal-window', timeout=5000)
            
            if modal:
                logger.info("Found first modal window")
                
                # Click the SeamlessAccess button
                access_button = await modal.query_selector('button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn')
                if access_button:
                    logger.info("Clicking 'Access Through Your Institution' button...")
                    await access_button.click()
                    await page.wait_for_timeout(3000)
                else:
                    logger.error("Could not find the SeamlessAccess button!")
                    return False
            
            # Wait for the second modal
            logger.info("Waiting for institution selector modal...")
            
            try:
                # The modal should contain "Search for your Institution" text
                institution_modal = await page.wait_for_selector('ngb-modal-window:has-text("Search for your Institution")', timeout=10000)
                
                if institution_modal:
                    logger.info("✅ Found institution search modal!")
                    
                    # Find the search input INSIDE this modal - it's the first text input
                    all_inputs = await institution_modal.query_selector_all('input')
                    search_input = None
                    
                    for inp in all_inputs:
                        inp_type = await inp.get_attribute('type') or 'text'
                        if inp_type == 'text':
                            search_input = inp
                            break
                    
                    if search_input:
                        logger.info("✅ Found institution search input!")
                        await search_input.fill("ETH Zurich")
                        await page.keyboard.press('Enter')
                        await page.wait_for_timeout(2000)
                        logger.info("✅ Searched for ETH Zurich")
                        
                        # Look for ETH option
                        logger.info("Looking for ETH Zurich option...")
                        try:
                            # Try multiple selectors
                            eth_selectors = [
                                'text="ETH Zurich"',
                                'button:has-text("ETH Zurich")',
                                'a:has-text("ETH Zurich")',
                                'div:has-text("ETH Zurich")',
                                ':text("ETH")',
                                '[role="option"]:has-text("ETH")'
                            ]
                            
                            eth_option = None
                            for selector in eth_selectors:
                                try:
                                    eth_option = await page.wait_for_selector(selector, timeout=2000)
                                    if eth_option:
                                        logger.info(f"✅ Found ETH option with selector: {selector}")
                                        break
                                except:
                                    continue
                            
                            if eth_option:
                                logger.info("✅ Clicking ETH Zurich option...")
                                await eth_option.click()
                                await page.wait_for_load_state('networkidle')
                                logger.info("✅ Clicked ETH Zurich")
                            else:
                                # Debug: list all clickable elements
                                logger.error("❌ Could not find ETH Zurich option with any selector")
                                clickables = await page.query_selector_all('a, button, div[role="option"], li')
                                logger.info(f"Found {len(clickables)} clickable elements after search:")
                                for i, elem in enumerate(clickables[:10]):  # First 10
                                    text = await elem.text_content()
                                    if text and text.strip():
                                        logger.info(f"  [{i}] {text.strip()[:80]}")
                        except Exception as e:
                            logger.error(f"❌ Error finding ETH option: {e}")
                    else:
                        logger.error("❌ Could not find search input in institution modal")
                else:
                    logger.error("❌ Institution search modal did not appear")
                    
                    # Debug: what modals are on the page?
                    all_modals = await page.query_selector_all('ngb-modal-window')
                    logger.info(f"Found {len(all_modals)} modals on page")
                    for i, modal in enumerate(all_modals):
                        text = await modal.text_content()
                        logger.info(f"Modal {i} text (first 100 chars): {text[:100] if text else 'None'}")
                        
            except Exception as e:
                logger.error(f"Error finding institution modal: {e}")
                await page.screenshot(path=output_dir / "modal_error.png")
                logger.info(f"Screenshot saved to {output_dir / 'modal_error.png'}")
            
            logger.info("\n🔍 KEEPING BROWSER OPEN FOR MANUAL INSPECTION")
            logger.info("Press Enter to close...")
            input()
            
        except Exception as e:
            logger.error(f"Error: {e}")
            await page.screenshot(path=output_dir / "error.png")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_ieee_auth())