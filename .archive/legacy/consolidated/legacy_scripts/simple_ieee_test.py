#!/usr/bin/env python3
"""
Simple IEEE Test
================

Direct test of IEEE download functionality.
"""

import os
import tempfile
import logging
from auth_manager import get_auth_manager

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("simple_ieee_test")

def test_direct_ieee_download():
    """Test direct IEEE download with authentication."""
    
    # Test DOI 
    test_doi = "10.1109/JPROC.2018.2820126"
    ieee_url = f"https://doi.org/{test_doi}"
    
    logger.info(f"🧪 Testing direct IEEE download")
    logger.info(f"📄 DOI: {test_doi}")
    logger.info(f"🔗 URL: {ieee_url}")
    
    # Get auth manager
    auth_manager = get_auth_manager()
    
    # Test download
    with tempfile.TemporaryDirectory() as tmpdir:
        dst_path = os.path.join(tmpdir, "test_paper.pdf")
        
        logger.info("🔄 Attempting download with authentication...")
        
        success = auth_manager.download_with_auth(ieee_url, "eth_ieee", dst_path)
        
        if success and os.path.exists(dst_path):
            file_size = os.path.getsize(dst_path)
            logger.info(f"✅ Download successful!")
            logger.info(f"📊 File size: {file_size} bytes")
            
            # Check if it's a PDF
            with open(dst_path, 'rb') as f:
                header = f.read(4)
                if header == b'%PDF':
                    logger.info("✅ Valid PDF file")
                else:
                    logger.warning("⚠️  File is not a PDF")
                    
            return True
        else:
            logger.error("❌ Download failed")
            return False

if __name__ == "__main__":
    success = test_direct_ieee_download()
    exit(0 if success else 1)