#!/usr/bin/env python3
"""
IEEE Network Debug
==================

Monitor network requests to understand what happens when button is clicked.
"""

import asyncio
import nest_asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("network_debug")

nest_asyncio.apply()

async def network_debug():
    from playwright.async_api import async_playwright
    
    output_dir = Path("network_debug")
    output_dir.mkdir(exist_ok=True)
    
    requests = []
    responses = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Monitor network
        def log_request(request):
            if 'seamless' in request.url.lower() or 'wayf' in request.url.lower() or 'shibboleth' in request.url.lower():
                logger.info(f"🟡 REQUEST: {request.method} {request.url}")
                requests.append(request.url)
        
        def log_response(response):
            if 'seamless' in response.url.lower() or 'wayf' in response.url.lower() or 'shibboleth' in response.url.lower():
                logger.info(f"🟢 RESPONSE: {response.status} {response.url}")
                responses.append(f"{response.status} {response.url}")
        
        page.on("request", log_request)
        page.on("response", log_response)
        
        try:
            logger.info("Navigating to IEEE...")
            await page.goto("https://doi.org/10.1109/JPROC.2018.2820126", wait_until='networkidle')
            await page.wait_for_timeout(3000)
            
            logger.info("Accepting cookies...")
            accept = await page.query_selector('button:has-text("Accept All")')
            if accept:
                await accept.click()
                await page.wait_for_timeout(1000)
            
            logger.info("Clicking Institutional Sign In...")
            inst = await page.wait_for_selector('a:has-text("Institutional Sign In")')
            await inst.click()
            await page.wait_for_timeout(3000)
            
            logger.info("Clicking Access Through Your Institution button...")
            access_button = await page.wait_for_selector('button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn')
            
            if access_button:
                logger.info("Button found, clicking and monitoring network...")
                await access_button.click()
                
                # Wait and monitor for 10 seconds
                for i in range(10):
                    await page.wait_for_timeout(1000)
                    logger.info(f"Waiting {i+1}/10 seconds...")
                
                # Check current state
                current_url = page.url
                logger.info(f"Current URL: {current_url}")
                
                # Check for new windows
                all_pages = context.pages
                logger.info(f"Number of pages: {len(all_pages)}")
                
                if len(all_pages) > 1:
                    new_page = all_pages[-1]
                    logger.info(f"New page URL: {new_page.url}")
                
                # Check iframe content again
                iframes = await page.query_selector_all('iframe')
                for i, iframe in enumerate(iframes):
                    src = await iframe.get_attribute('src')
                    if src and 'seamless' in src:
                        logger.info(f"SeamlessAccess iframe {i}: {src}")
                        frame = await iframe.content_frame()
                        if frame:
                            content = await frame.content()
                            logger.info(f"Iframe content length: {len(content)}")
                            
                            # Save iframe content for inspection
                            with open(output_dir / f"iframe_{i}_content.html", "w") as f:
                                f.write(content)
                            logger.info(f"Iframe content saved to iframe_{i}_content.html")
                
                # Try to trigger iframe manually
                logger.info("Trying to manually trigger iframe load...")
                
                # Look for JavaScript that might trigger the iframe
                js_result = await page.evaluate('''
                    () => {
                        // Look for any click handlers or JavaScript
                        const button = document.querySelector('button.stats-Global_Inst_sign_in_seamlessaccess_access_through_your_institution_btn');
                        if (button) {
                            const events = getEventListeners ? getEventListeners(button) : {};
                            return {
                                hasEvents: Object.keys(events).length > 0,
                                eventTypes: Object.keys(events)
                            };
                        }
                        return {hasEvents: false, eventTypes: []};
                    }
                ''')
                logger.info(f"Button event analysis: {js_result}")
                
                # Try clicking the SeamlessAccess iframe source directly
                iframe_src = "https://service.seamlessaccess.org/ps/"
                logger.info(f"Trying direct iframe source: {iframe_src}")
                
                try:
                    await page.goto(iframe_src, timeout=10000)
                    await page.wait_for_timeout(3000)
                    await page.screenshot(path=output_dir / "direct_seamless.png")
                    
                    current_content = await page.content()
                    logger.info(f"Direct SeamlessAccess content length: {len(current_content)}")
                    
                    with open(output_dir / "direct_seamless.html", "w") as f:
                        f.write(current_content)
                    
                    # Look for search input on direct page
                    search_input = await page.query_selector('input[type="search"], input[type="text"]')
                    if search_input:
                        logger.info("✅ Found search input on direct SeamlessAccess page!")
                        await search_input.fill("ETH Zurich")
                        await page.wait_for_timeout(2000)
                        
                        # Look for ETH in results
                        eth_option = await page.query_selector('text="ETH Zurich"')
                        if eth_option:
                            logger.info("✅ Found ETH option!")
                            await eth_option.click()
                            await page.wait_for_timeout(3000)
                            logger.info(f"After clicking ETH: {page.url}")
                    else:
                        logger.info("No search input found on direct page")
                        
                except Exception as e:
                    logger.warning(f"Direct access failed: {e}")
            
            logger.info("\nNetwork Summary:")
            logger.info(f"Requests captured: {len(requests)}")
            for req in requests:
                logger.info(f"  - {req}")
            logger.info(f"Responses captured: {len(responses)}")
            for resp in responses:
                logger.info(f"  - {resp}")
            
            # Save logs
            with open(output_dir / "network_log.txt", "w") as f:
                f.write("REQUESTS:\n")
                for req in requests:
                    f.write(f"{req}\n")
                f.write("\nRESPONSES:\n")
                for resp in responses:
                    f.write(f"{resp}\n")
            
            logger.info("Browser will stay open for inspection...")
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(network_debug())