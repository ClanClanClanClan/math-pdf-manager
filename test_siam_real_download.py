#!/usr/bin/env python3
"""
Test SIAM Real PDF Download
===========================

This test verifies SIAM can download real PDFs with browser automation.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

def test_siam_download():
    """Test SIAM with full browser automation"""
    print("\n" + "="*60)
    print("Testing SIAM Publisher with Browser Authentication")
    print("="*60)
    
    try:
        from src.publishers.siam_publisher import SIAMPublisher
        from src.publishers import AuthenticationConfig
        from src.secure_credential_manager import get_credential_manager
        
        # Get credentials
        cm = get_credential_manager()
        username, password = cm.get_eth_credentials()
        
        if not username or not password:
            print("✗ No ETH credentials found")
            return False
        
        print(f"✓ Using ETH credentials: {username[:3]}***")
        
        # Create auth config
        auth_config = AuthenticationConfig(
            username=username,
            password=password,
            institutional_login='eth'
        )
        
        # Create SIAM publisher
        siam = SIAMPublisher(auth_config)
        
        # Test download - this should trigger browser automation
        test_doi = "10.1137/S0097539795293172"
        print(f"Testing DOI: {test_doi}")
        print("\nNOTE: This will open a browser window and may take 30-60 seconds...")
        
        output_path = Path("siam_test_downloads") / f"siam_{test_doi.replace('/', '_')}.pdf"
        output_path.parent.mkdir(exist_ok=True)
        
        # Enable debug logging
        import logging
        logging.basicConfig(level=logging.INFO)
        
        result = siam.download_paper(test_doi, output_path)
        
        if result.success and output_path.exists():
            file_size = output_path.stat().st_size
            print(f"\n✅ SIAM download successful!")
            print(f"   Size: {file_size / 1024 / 1024:.2f} MB")
            print(f"   Saved to: {output_path}")
            
            # Verify PDF content
            with open(output_path, 'rb') as f:
                header = f.read(8)
                print(f"   PDF Header: {header}")
                
                if header.startswith(b'%PDF'):
                    print("   ✓ Verified: Valid PDF file")
                    
                    # Check if it has actual content
                    f.seek(0)
                    content = f.read(1000)
                    if b'obj' in content and b'stream' in content:
                        print("   ✓ Contains PDF objects and streams")
                    
                    # Try to extract text
                    try:
                        import subprocess
                        text_output = subprocess.run(
                            ['pdftotext', str(output_path), '-'],
                            capture_output=True,
                            text=True
                        )
                        if text_output.returncode == 0 and text_output.stdout:
                            lines = text_output.stdout.strip().split('\n')
                            print(f"   ✓ Extracted {len(lines)} lines of text")
                            print("   First few lines:")
                            for line in lines[:5]:
                                if line.strip():
                                    print(f"     '{line.strip()}'")
                    except:
                        pass
                    
                    return True
                else:
                    print("   ✗ Not a valid PDF header")
        else:
            print(f"\n✗ SIAM download failed: {result.error_message if hasattr(result, 'error_message') else 'Unknown error'}")
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    
    return False

if __name__ == "__main__":
    success = test_siam_download()
    
    if success:
        print("\n" + "="*60)
        print("✅ SIAM CAN DOWNLOAD REAL PDFs!")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("❌ SIAM download test failed")
        print("="*60)
    
    # List any downloaded files
    output_dir = Path("siam_test_downloads")
    if output_dir.exists():
        pdfs = list(output_dir.glob("*.pdf"))
        if pdfs:
            print(f"\nDownloaded files in {output_dir}:")
            for pdf in pdfs:
                size_mb = pdf.stat().st_size / 1024 / 1024
                print(f"  - {pdf.name} ({size_mb:.2f} MB)")