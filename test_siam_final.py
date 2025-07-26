#!/usr/bin/env python3
"""
Final SIAM Test - Use Browser Download and Save Properly
=======================================================
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Monkey patch the SIAM publisher to use the browser download properly
def patch_siam_download():
    """Patch SIAM to use browser-downloaded PDF properly"""
    from src.publishers.siam_publisher import SIAMPublisher
    
    original_download_paper = SIAMPublisher.download_paper
    
    def patched_download_paper(self, paper_id: str, download_path):
        """Patched version that handles browser downloads correctly"""
        
        # Set the pending identifier
        self._pending_download_identifier = paper_id
        
        # Authenticate (this will download the PDF in browser)
        if not self.authenticate():
            from src.publishers import DownloadResult
            return DownloadResult(False, error_message="Authentication failed")
        
        # Check if we have cached PDF data from browser
        if hasattr(self, '_cached_pdf_data') and self._cached_pdf_data:
            print(f"✓ Using cached PDF data ({len(self._cached_pdf_data):,} bytes)")
            
            # Ensure parent directory exists
            download_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write cached PDF data
            with open(download_path, 'wb') as f:
                f.write(self._cached_pdf_data)
            
            # Verify it's a valid PDF
            with open(download_path, 'rb') as f:
                header = f.read(4)
                if header == b'%PDF':
                    from src.publishers import DownloadResult
                    return DownloadResult(True, file_path=download_path)
                else:
                    download_path.unlink()
                    from src.publishers import DownloadResult
                    return DownloadResult(False, error_message="Invalid PDF data")
        
        # Fallback to original method
        return original_download_paper(self, paper_id, download_path)
    
    # Apply the patch
    SIAMPublisher.download_paper = patched_download_paper

# Apply the patch
patch_siam_download()

from src.publishers.siam_publisher import SIAMPublisher
from src.publishers import AuthenticationConfig
from src.secure_credential_manager import get_credential_manager

print("\n" + "="*60)
print("FINAL SIAM TEST - WITH PATCH")
print("="*60)

# Get credentials
cm = get_credential_manager()
username, password = cm.get_eth_credentials()
print(f"Using ETH credentials: {username[:3]}***")

# Create auth config
auth_config = AuthenticationConfig(
    username=username,
    password=password,
    institutional_login='eth'
)

# Create SIAM publisher
siam = SIAMPublisher(auth_config)

# Test download
test_doi = "10.1137/S0097539795293172"
print(f"Downloading: {test_doi}")

output_path = Path("SIAM_FINAL") / f"siam_{test_doi.replace('/', '_')}.pdf"
output_path.parent.mkdir(exist_ok=True)

print("\nThis will open a browser window for authentication and download...")

result = siam.download_paper(test_doi, output_path)

if result.success and output_path.exists():
    file_size = output_path.stat().st_size
    print(f"\n✅ SIAM DOWNLOAD SUCCESSFUL!")
    print(f"Size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
    print(f"Saved to: {output_path}")
    
    # Verify content
    with open(output_path, 'rb') as f:
        header = f.read(8)
        if header.startswith(b'%PDF'):
            print("✅ Valid PDF file!")
            
            # Extract text
            import subprocess
            try:
                text_result = subprocess.run(['pdftotext', str(output_path), '-'], 
                                      capture_output=True, text=True)
                if text_result.stdout:
                    lines = text_result.stdout.strip().split('\n')
                    title_line = None
                    for line in lines[:20]:
                        if 'POLYNOMIAL-TIME' in line.upper() or 'QUANTUM COMPUTER' in line.upper():
                            title_line = line.strip()
                            break
                    
                    if title_line:
                        print(f"✅ Verified: Found title '{title_line}'")
                    else:
                        print("✅ PDF contains text content")
            except:
                pass
        else:
            print(f"❌ Invalid PDF header: {header}")
else:
    print(f"\n❌ SIAM download failed")
    if hasattr(result, 'error_message'):
        print(f"Error: {result.error_message}")

print(f"\n{'='*60}")
if result.success:
    print("✅ SIAM IS NOW WORKING - Downloads real PDFs!")
else:
    print("❌ SIAM still not working")
print(f"{'='*60}")