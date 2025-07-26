#!/usr/bin/env python3
"""
Test Auth Manager
=================

Test the auth_manager directly.
"""

import asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("test_auth")

def test_auth_manager():
    from auth_manager import get_auth_manager
    
    output_dir = Path("auth_test")
    output_dir.mkdir(exist_ok=True)
    
    auth_manager = get_auth_manager()
    
    # Test IEEE download
    ieee_url = "https://doi.org/10.1109/JPROC.2018.2820126"
    pdf_path = output_dir / "ieee_paper.pdf"
    
    logger.info(f"Testing IEEE download: {ieee_url}")
    
    try:
        success = auth_manager.download_with_auth(ieee_url, "eth_ieee", str(pdf_path))
        
        if success and pdf_path.exists():
            logger.info(f"✅ SUCCESS! PDF downloaded: {pdf_path}")
            logger.info(f"PDF size: {pdf_path.stat().st_size} bytes")
            return True
        else:
            logger.error("❌ Download failed")
            return False
            
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_auth_manager()
    if success:
        logger.info("✅ Auth manager test successful!")
    else:
        logger.error("❌ Auth manager test failed!")