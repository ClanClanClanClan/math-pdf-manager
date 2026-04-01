#!/usr/bin/env python3
"""
Test Enhanced Elsevier PDF Download
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright
from src.publishers.institutional.base import ETHAuthenticator
from src.publishers.institutional.publishers.elsevier_navigator import (
    ELSEVIER_CONFIG,
    ElsevierNavigator,
)
from src.secure_credential_manager import get_credential_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_elsevier():
    """Test Elsevier with enhanced PDF download."""
    
    # Get credentials
    cred_manager = get_credential_manager()
    username = cred_manager.get_credential('eth_username')
    password = cred_manager.get_credential('eth_password')
    
    if not username or not password:
        raise ValueError("ETH credentials not found")
    
    # Create output directory
    output_dir = Path.cwd() / "elsevier_enhanced_test"
    output_dir.mkdir(exist_ok=True)
    
    # Test paper - one that has worked before
    doi = "10.1016/j.jcp.2024.113362"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox'
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            accept_downloads=True  # Enable downloads
        )
        
        page = await context.new_page()
        
        try:
            # Create navigator
            navigator = ElsevierNavigator(page, ELSEVIER_CONFIG)
            navigator.eth_auth = ETHAuthenticator(page, username, password)
            
            # Navigate to paper
            logger.info(f"Navigating to DOI: {doi}")
            success = await navigator.navigate_to_paper(doi)
            
            if not success:
                logger.error("Failed to navigate to paper")
                return
            
            # Authenticate
            logger.info("Starting authentication...")
            await navigator.navigate_to_login()
            await navigator.select_eth_institution()
            await navigator.eth_auth.perform_login()
            await navigator.navigate_after_auth()
            
            # Download PDF with enhanced method
            logger.info("Attempting PDF download...")
            result = await navigator.download_pdf(output_dir)
            
            if result:
                # Check what we got
                file_size = result.stat().st_size
                
                if result.suffix == '.pdf':
                    # Check if it's a real PDF
                    with open(result, 'rb') as f:
                        header = f.read(4)
                        is_pdf = (header == b'%PDF')
                    
                    if is_pdf:
                        logger.info(f"✅ SUCCESS: Downloaded real PDF!")
                        logger.info(f"   File: {result.name}")
                        logger.info(f"   Size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
                    else:
                        logger.info(f"⚠️  Downloaded file but not a PDF")
                        logger.info(f"   File: {result.name}")
                        logger.info(f"   Size: {file_size:,} bytes")
                else:
                    logger.info(f"📝 Created access confirmation file")
                    logger.info(f"   File: {result.name}")
                    
                    # Read the confirmation file to see what it says
                    with open(result, 'r') as f:
                        content = f.read()
                        logger.info(f"   Content:\n{content}")
            else:
                logger.error("❌ FAILED: No file created")
                
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_elsevier())