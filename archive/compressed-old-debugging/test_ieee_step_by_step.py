#!/usr/bin/env python3
"""
IEEE Step by Step Test
======================

Test each step visually.
"""

import asyncio
import logging
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ieee_step")

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=1000)
        page = await browser.new_page()
        
        logger.info("=== STEP 1: Navigate to IEEE ===")
        await page.goto("https://doi.org/10.1109/JPROC.2018.2820126")
        await page.wait_for_timeout(5000)
        
        logger.info("=== STEP 2: Accept cookies ===")
        try:
            accept = await page.query_selector('button:has-text("Accept All")')
            if accept:
                await accept.click()
                logger.info("✓ Clicked Accept All")
                await page.wait_for_timeout(1000)
        except Exception as e:
            logger.info(f"No cookies to accept: {e}")
        
        logger.info("=== STEP 3: Find Institutional Sign In ===")
        # Look for all links with "Institutional"
        inst_links = await page.query_selector_all('a:has-text("Institutional")')
        logger.info(f"Found {len(inst_links)} institutional links")
        
        for i, link in enumerate(inst_links):
            text = await link.text_content()
            visible = await link.is_visible()
            logger.info(f"  Link {i}: '{text}' visible={visible}")
        
        logger.info("=== STEP 4: Click Institutional Sign In ===")
        try:
            inst_button = await page.wait_for_selector('a:has-text("Institutional Sign In")', timeout=10000)
            logger.info("✓ Found Institutional Sign In button")
            await inst_button.click()
            logger.info("✓ Clicked")
            await page.wait_for_timeout(2000)
        except Exception as e:
            logger.error(f"Failed to find/click Institutional Sign In: {e}")
            await page.screenshot(path="step4_error.png")
            return
        
        logger.info("=== STEP 5: Check for modal ===")
        modals = await page.query_selector_all('ngb-modal-window')
        logger.info(f"Found {len(modals)} modals")
        
        if modals:
            modal = modals[0]
            logger.info("=== STEP 6: Look for SeamlessAccess button in modal ===")
            
            # Try exact selector
            button = await modal.query_selector('button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn')
            if button:
                logger.info("✓ Found SeamlessAccess button with exact class")
            else:
                # Try broader search
                all_buttons = await modal.query_selector_all('button')
                logger.info(f"Found {len(all_buttons)} buttons in modal")
                for i, btn in enumerate(all_buttons):
                    text = await btn.text_content()
                    classes = await btn.get_attribute('class') or ''
                    logger.info(f"  Button {i}: '{text}' classes='{classes[:50]}...'")
                
                # Look for the button with "Access" text
                access_button = await modal.query_selector('button:has-text("Access")')
                if access_button:
                    logger.info("✓ Found button with 'Access' text")
                    button = access_button
            
            if button:
                logger.info("=== STEP 7: Click Access button ===")
                await button.click()
                logger.info("✓ Clicked")
                await page.wait_for_timeout(3000)
                
                logger.info("=== STEP 8: Check what happened ===")
                current_url = page.url
                logger.info(f"Current URL: {current_url}")
                
                # Check for second modal
                modals2 = await page.query_selector_all('ngb-modal-window')
                logger.info(f"Now have {len(modals2)} modals")
                
                if len(modals2) > 0:
                    logger.info("Looking for institution search in modal...")
                    modal2 = modals2[-1]  # Get the last (newest) modal
                    
                    # Find inputs
                    inputs = await modal2.query_selector_all('input')
                    logger.info(f"Found {len(inputs)} inputs in modal")
                    
                    for i, inp in enumerate(inputs):
                        inp_type = await inp.get_attribute('type') or 'text'
                        placeholder = await inp.get_attribute('placeholder') or ''
                        name = await inp.get_attribute('name') or ''
                        logger.info(f"  Input {i}: type={inp_type}, placeholder='{placeholder}', name='{name}'")
        
        logger.info("\nKeeping browser open for 30 seconds...")
        await page.wait_for_timeout(30000)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test())