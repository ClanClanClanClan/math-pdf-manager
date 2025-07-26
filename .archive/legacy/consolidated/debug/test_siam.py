#!/usr/bin/env python3
"""
Test SIAM Download
==================

Test SIAM authentication and download.
"""

import logging
from pathlib import Path
from auth_manager import get_auth_manager

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("siam_test")

def test_siam_download():
    """Test SIAM paper download with authentication."""
    
    # Test SIAM paper DOI (use direct SIAM URL to avoid DOI redirect timeout)
    siam_doi = "10.1137/S0036142997325199"
    siam_url = f"https://epubs.siam.org/doi/{siam_doi}"
    
    logger.info(f"🧪 Testing SIAM download")
    logger.info(f"📄 DOI: {siam_doi}")
    logger.info(f"🔗 URL: {siam_url}")
    
    # Get auth manager
    auth_manager = get_auth_manager()
    
    # Test download
    output_dir = Path("siam_test")
    output_dir.mkdir(exist_ok=True)
    dst_path = output_dir / "siam_paper.pdf"
    
    logger.info("🔄 Attempting SIAM download with authentication...")
    
    success = auth_manager.download_with_auth(siam_url, "eth_siam", str(dst_path))
    
    if success and dst_path.exists():
        file_size = dst_path.stat().st_size
        logger.info(f"✅ SIAM download successful!")
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
        logger.error("❌ SIAM download failed")
        return False

if __name__ == "__main__":
    success = test_siam_download()
    exit(0 if success else 1)