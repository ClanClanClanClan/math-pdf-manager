#!/usr/bin/env python3
"""
Test Project Euclid Download
============================

Test Project Euclid authentication and download.
"""

import logging
from pathlib import Path
from auth_manager import get_auth_manager

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("euclid_test")

def test_euclid_download():
    """Test Project Euclid paper download with authentication."""
    
    # Test Project Euclid paper URL (from our investigation)
    euclid_url = "https://projecteuclid.org/journals/annals-of-probability/volume-32/issue-1A/Concentration-of-the-spectral-measure-for-large-matrices/10.1214/aop/1078415845.full"
    
    logger.info(f"🧪 Testing Project Euclid download")
    logger.info(f"📄 URL: {euclid_url}")
    
    # Get auth manager
    auth_manager = get_auth_manager()
    
    # Test download
    output_dir = Path("euclid_test")
    output_dir.mkdir(exist_ok=True)
    dst_path = output_dir / "euclid_paper.pdf"
    
    logger.info("🔄 Attempting Project Euclid download with authentication...")
    
    success = auth_manager.download_with_auth(euclid_url, "eth_project_euclid", str(dst_path))
    
    if success and dst_path.exists():
        file_size = dst_path.stat().st_size
        logger.info(f"✅ Project Euclid download successful!")
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
        logger.error("❌ Project Euclid download failed")
        return False

if __name__ == "__main__":
    success = test_euclid_download()
    exit(0 if success else 1)