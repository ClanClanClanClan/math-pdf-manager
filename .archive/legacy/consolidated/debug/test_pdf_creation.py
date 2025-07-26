#!/usr/bin/env python3
"""
Test PDF Creation
=================

Test that we can create and verify PDF files.
"""

import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("pdf_test")

def test_pdf_creation():
    """Test creating a dummy PDF to verify file operations work."""
    
    output_dir = Path("pdf_test")
    output_dir.mkdir(exist_ok=True)
    
    # Create a minimal PDF content (this is a very basic PDF structure)
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Hello World) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000010 00000 n 
0000000053 00000 n 
0000000125 00000 n 
0000000185 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
279
%%EOF"""
    
    # Test writing PDF file
    pdf_path = output_dir / "test.pdf"
    
    try:
        # Write the PDF
        with open(pdf_path, 'wb') as f:
            f.write(pdf_content)
        
        logger.info(f"✅ PDF file created: {pdf_path}")
        
        # Verify the file exists
        if pdf_path.exists():
            file_size = pdf_path.stat().st_size
            logger.info(f"✅ File exists, size: {file_size} bytes")
            
            # Verify it starts with PDF header
            with open(pdf_path, 'rb') as f:
                header = f.read(8)
                if header.startswith(b'%PDF'):
                    logger.info("✅ Valid PDF header confirmed")
                    
                    # Test that we can read the full content back
                    f.seek(0)
                    read_content = f.read()
                    if read_content == pdf_content:
                        logger.info("✅ Content verification successful")
                        logger.info(f"🎉 PDF creation test PASSED!")
                        return True
                    else:
                        logger.error("❌ Content mismatch")
                else:
                    logger.error("❌ Invalid PDF header")
        else:
            logger.error("❌ File was not created")
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return False
    
    return False

def test_auth_manager_config():
    """Test that auth manager is properly configured."""
    
    try:
        from auth_manager import get_auth_manager
        from secure_credential_manager import get_credential_manager
        
        logger.info("✅ Auth manager imports successful")
        
        # Test credential manager
        cm = get_credential_manager()
        username, password = cm.get_eth_credentials()
        
        if username and password:
            logger.info("✅ ETH credentials found")
            logger.info(f"Username: {username[:3]}***")
        else:
            logger.warning("⚠️  ETH credentials not found")
        
        # Test auth manager
        auth_manager = get_auth_manager()
        logger.info("✅ Auth manager created successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Auth manager test failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("=== Testing PDF File Operations ===")
    pdf_test = test_pdf_creation()
    
    logger.info("\n=== Testing Auth Manager Configuration ===")
    auth_test = test_auth_manager_config()
    
    if pdf_test and auth_test:
        logger.info("\n🎉 ALL TESTS PASSED - System is ready for PDF downloads!")
    else:
        logger.error("\n💥 Some tests failed")
        
    exit(0 if pdf_test and auth_test else 1)