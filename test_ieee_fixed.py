#!/usr/bin/env python3
"""
Test IEEE with Async Fix
========================
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.publishers.ieee_publisher import IEEEPublisher
from src.publishers import AuthenticationConfig
from src.secure_credential_manager import get_credential_manager

print("\n" + "="*60)
print("TESTING IEEE WITH ASYNC FIX")
print("="*60)

# Get credentials
cm = get_credential_manager()
username, password = cm.get_eth_credentials()

if not username or not password:
    print("❌ No ETH credentials found")
    exit(1)

print(f"✓ Using ETH credentials: {username[:3]}***")

# Create auth config
auth_config = AuthenticationConfig(
    username=username,
    password=password,
    institutional_login='eth'
)

# Create IEEE publisher
ieee = IEEEPublisher(auth_config)

# Test download
test_doi = "10.1109/5.726791"  # LeCun's CNN paper
print(f"Testing DOI: {test_doi}")
print("NOTE: Browser window will open for authentication...")

output_path = Path("IEEE_FIXED_TEST") / f"ieee_{test_doi.replace('/', '_')}.pdf"
output_path.parent.mkdir(exist_ok=True)

result = ieee.download_paper(test_doi, output_path)

if result.success and output_path.exists():
    file_size = output_path.stat().st_size
    print(f"\n✅ IEEE DOWNLOAD SUCCESSFUL!")
    print(f"Size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
    print(f"Saved to: {output_path}")
    
    # Verify PDF
    with open(output_path, 'rb') as f:
        header = f.read(8)
        if header.startswith(b'%PDF'):
            print("✅ Valid PDF file!")
            
            # Try to extract text
            import subprocess
            try:
                text_result = subprocess.run(['pdftotext', str(output_path), '-'], 
                                      capture_output=True, text=True)
                if text_result.stdout:
                    lines = text_result.stdout.strip().split('\n')
                    print(f"✅ Extracted {len(lines)} lines of text")
                    
                    # Look for the title
                    for line in lines[:10]:
                        if 'gradient' in line.lower() and 'learning' in line.lower():
                            print(f"✅ Found paper title: '{line.strip()}'")
                            break
            except:
                pass
        else:
            print(f"❌ Invalid PDF header: {header}")
else:
    print(f"\n❌ IEEE download failed")
    if hasattr(result, 'error_message'):
        print(f"Error: {result.error_message}")

print(f"\n{'='*60}")
if result.success:
    print("✅ IEEE ASYNC FIX SUCCESSFUL!")
else:
    print("❌ IEEE still has issues")
print(f"{'='*60}")