#!/usr/bin/env python3
"""
Simple ETH Authentication Test
=============================

A simplified test to verify ETH credentials and basic download functionality.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from secure_credential_manager import get_credential_manager
    from scripts.downloader import acquire_paper_by_metadata
    from metadata_fetcher import fetch_metadata_all_sources
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


def test_credentials():
    """Test if ETH credentials are available."""
    print("🔍 Checking ETH credentials...")
    
    manager = get_credential_manager()
    username, password = manager.get_eth_credentials()
    
    if username and password:
        print(f"✅ ETH credentials found for user: {username}")
        return True
    else:
        print("❌ ETH credentials not found")
        print("Set environment variables: ETH_USERNAME and ETH_PASSWORD")
        return False


def test_metadata():
    """Test metadata fetching."""
    print("\n📋 Testing metadata fetching...")
    
    # Test with a simple query
    try:
        results = fetch_metadata_all_sources("Attention Is All You Need")
        if results:
            print(f"✅ Found {len(results)} metadata results")
            for i, result in enumerate(results[:2]):  # Show first 2
                title = result.get('title', 'Unknown')
                doi = result.get('doi', 'No DOI')
                print(f"  {i+1}. {title[:50]}... (DOI: {doi})")
            return True
        else:
            print("❌ No metadata found")
            return False
    except Exception as e:
        print(f"❌ Metadata error: {e}")
        return False


def test_simple_download():
    """Test a simple open access download."""
    print("\n📥 Testing simple download...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            # Try downloading an open access paper
            file_path, attempts = acquire_paper_by_metadata(
                "Attention Is All You Need",
                tmpdir,
                doi="10.48550/arXiv.1706.03762"
            )
            
            if file_path and os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                print(f"✅ Download successful: {file_size} bytes")
                
                # Check if it's a valid PDF
                with open(file_path, 'rb') as f:
                    header = f.read(4)
                    if header == b'%PDF':
                        print("✅ Valid PDF file")
                    else:
                        print(f"⚠️  File may not be PDF (header: {header})")
                
                return True
            else:
                print("❌ Download failed")
                for attempt in attempts:
                    print(f"  - {attempt.strategy}: {attempt.result.value}")
                return False
                
        except Exception as e:
            print(f"❌ Download error: {e}")
            return False


def main():
    """Run simple tests."""
    print("ETH Authentication Simple Test")
    print("==============================\n")
    
    # Test credentials
    if not test_credentials():
        return False
    
    # Test metadata
    if not test_metadata():
        print("⚠️  Metadata test failed, but continuing...")
    
    # Test download
    if not test_simple_download():
        print("⚠️  Download test failed")
        return False
    
    print("\n🎉 Basic tests completed successfully!")
    print("\nNext steps:")
    print("1. Run: python eth_auth_setup.py")
    print("2. Test institutional downloads with your ETH credentials")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)