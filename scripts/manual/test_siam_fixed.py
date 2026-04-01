#!/usr/bin/env python3
"""
Test SIAM with Fixed Download
=============================

This test ensures SIAM properly downloads and saves PDFs.
"""

import sys
from pathlib import Path
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

# Enable logging to see what's happening
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s - %(message)s')

from src.publishers.siam_publisher import SIAMPublisher
from src.publishers import AuthenticationConfig
from src.secure_credential_manager import get_credential_manager

print("\n" + "="*60)
print("TESTING SIAM WITH FIXED DOWNLOAD")
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
test_doi = "10.1137/S0097539795293172"  # Shor's algorithm
print(f"\nTarget DOI: {test_doi}")

# IMPORTANT: Set the pending download identifier BEFORE authentication
# This tells the browser automation which paper to download
siam._pending_download_identifier = test_doi

output_path = Path("SIAM_FIXED_TEST") / f"siam_{test_doi.replace('/', '_')}.pdf"
output_path.parent.mkdir(exist_ok=True)

print("\nSTEP 1: Authenticating with browser (this will download the PDF)...")
print("NOTE: Browser window will open and download the PDF during authentication\n")

# The download_paper method will:
# 1. Check for cached PDF data (won't exist yet)
# 2. Call authenticate() which will use browser automation
# 3. During browser auth, it will download the PDF and cache it
# 4. Then use the cached PDF data
result = siam.download_paper(test_doi, output_path)

if result.success and output_path.exists():
    file_size = output_path.stat().st_size
    print(f"\n✅ SIAM DOWNLOAD SUCCESSFUL!")
    print(f"Size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
    print(f"Saved to: {output_path}")
    
    # Verify PDF
    with open(output_path, 'rb') as f:
        header = f.read(8)
        print(f"PDF Header: {header}")
        
        if header.startswith(b'%PDF'):
            print("✅ Valid PDF file!")
            
            # Try to get text
            import subprocess
            try:
                result_text = subprocess.run(['pdftotext', str(output_path), '-'], 
                                      capture_output=True, text=True)
                if result_text.stdout:
                    lines = result_text.stdout.strip().split('\n')
                    print(f"✅ Extracted {len(lines)} lines of text")
                    print("\nFirst few lines:")
                    for i, line in enumerate(lines[:10]):
                        if line.strip():
                            print(f"  {i+1}: '{line.strip()}'")
                            
                    # Check for Shor's algorithm content
                    full_text = result_text.stdout.lower()
                    if 'quantum' in full_text and 'shor' in full_text:
                        print("\n✅ Verified: This is Shor's quantum algorithm paper!")
                    elif 'polynomial' in full_text and 'factorization' in full_text:
                        print("\n✅ Verified: This is the prime factorization paper!")
            except Exception as e:
                print(f"Could not extract text: {e}")
else:
    print(f"\n❌ SIAM download failed")
    if hasattr(result, 'error_message'):
        print(f"Error: {result.error_message}")
    
    # Check if browser automation ran but didn't save the file
    if hasattr(siam, '_cached_pdf_data') and siam._cached_pdf_data:
        print("\n⚠️  Browser downloaded PDF data but failed to save to file")
        print(f"Cached PDF size: {len(siam._cached_pdf_data):,} bytes")