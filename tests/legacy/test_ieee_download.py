#!/usr/bin/env python3
"""
Test IEEE institutional download
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.publishers.institutional import download_with_institutional_access

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_ieee_download():
    """Test downloading a paper from IEEE."""
    
    # Test with a known IEEE paper
    test_doi = "10.1109/JPROC.2018.2820126"
    
    print(f"\n🧪 Testing IEEE institutional download")
    print(f"DOI: {test_doi}")
    print("-" * 50)
    
    try:
        # Download the paper
        path, metadata = await download_with_institutional_access(
            doi=test_doi,
            publisher="ieee",
            output_dir=Path("test_downloads"),
            headless=False,  # Show browser for debugging
            timeout=180000  # 3 minutes
        )
        
        if path and path.exists():
            print(f"\n✅ SUCCESS! Downloaded to: {path}")
            print(f"File size: {path.stat().st_size:,} bytes")
        else:
            print(f"\n❌ FAILED!")
            print(f"Error: {metadata.get('error', 'Unknown error')}")
            print(f"Final state: {metadata.get('state', 'Unknown')}")
        
        print("\nMetadata:")
        for key, value in metadata.items():
            if key not in ['start_time', 'end_time']:
                print(f"  {key}: {value}")
        
        return path is not None
        
    except Exception as e:
        print(f"\n❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_ieee_download())
    sys.exit(0 if success else 1)