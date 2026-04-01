#!/usr/bin/env python3
"""
Test SIAM Direct Browser Download
=================================

Test if SIAM cached PDF mechanism works.
"""

import sys
from pathlib import Path
import asyncio

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_siam_browser_download():
    """Test SIAM browser download directly"""
    print("\n" + "="*60)
    print("Testing SIAM Direct Browser Download")
    print("="*60)
    
    try:
        from src.publishers.siam_publisher import SIAMPublisher
        from src.publishers import AuthenticationConfig
        from src.secure_credential_manager import get_credential_manager
        
        # Get credentials
        cm = get_credential_manager()
        username, password = cm.get_eth_credentials()
        
        print(f"✓ Using ETH credentials: {username[:3]}***")
        
        # Create auth config
        auth_config = AuthenticationConfig(
            username=username,
            password=password,
            institutional_login='eth'
        )
        
        # Create SIAM publisher
        siam = SIAMPublisher(auth_config)
        
        # Store the DOI for authentication
        test_doi = "10.1137/S0097539795293172"
        siam._pending_download_identifier = test_doi
        
        print(f"Testing DOI: {test_doi}")
        print("Authenticating with browser (this will open a window)...")
        
        # Just authenticate - this should download the PDF
        auth_success = siam.authenticate()
        
        if auth_success:
            print("✅ Authentication successful!")
            
            # Check if we have cached PDF data
            if hasattr(siam, '_cached_pdf_data') and siam._cached_pdf_data:
                pdf_data = siam._cached_pdf_data
                print(f"✅ Found cached PDF data: {len(pdf_data):,} bytes")
                
                # Save it
                output_path = Path("siam_direct_test") / f"siam_{test_doi.replace('/', '_')}.pdf"
                output_path.parent.mkdir(exist_ok=True)
                
                with open(output_path, 'wb') as f:
                    f.write(pdf_data)
                
                print(f"   Saved to: {output_path}")
                
                # Verify it's a real PDF
                with open(output_path, 'rb') as f:
                    header = f.read(8)
                    print(f"   PDF Header: {header}")
                    
                    if header.startswith(b'%PDF'):
                        print("   ✓ Valid PDF file!")
                        
                        # Get some metadata
                        f.seek(0)
                        content = f.read()
                        
                        # Count PDF objects
                        obj_count = content.count(b' obj')
                        print(f"   ✓ Contains {obj_count} PDF objects")
                        
                        # Check for common PDF structures
                        has_pages = b'/Pages' in content
                        has_catalog = b'/Catalog' in content
                        has_fonts = b'/Font' in content
                        
                        print(f"   ✓ Has Pages: {has_pages}")
                        print(f"   ✓ Has Catalog: {has_catalog}")
                        print(f"   ✓ Has Fonts: {has_fonts}")
                        
                        return True
            else:
                print("✗ No cached PDF data found after authentication")
        else:
            print("✗ Authentication failed")
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
    
    return False

if __name__ == "__main__":
    success = asyncio.run(test_siam_browser_download())
    
    if success:
        print("\n" + "="*60)
        print("✅ SIAM BROWSER DOWNLOAD WORKS!")
        print("The PDF was successfully downloaded during authentication")
        print("="*60)
        
        # Try to extract text
        output_path = Path("siam_direct_test") / "siam_10.1137_S0097539795293172.pdf"
        if output_path.exists():
            try:
                import subprocess
                result = subprocess.run(
                    ['pdftotext', str(output_path), '-'],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0 and result.stdout:
                    lines = [l.strip() for l in result.stdout.split('\n') if l.strip()]
                    print(f"\nExtracted {len(lines)} lines of text")
                    print("First few lines:")
                    for line in lines[:10]:
                        print(f"  '{line}'")
            except:
                pass