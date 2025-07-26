#!/usr/bin/env python3
"""
FOCUSED WILEY TEST
==================

Test Wiley with a focused set of papers, including non-open access ones
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_wiley_focused():
    """Test Wiley with focused selection"""
    
    print("🎯 FOCUSED WILEY TEST")
    print("=" * 80)
    print("Testing with mix of open and subscription papers")
    print("=" * 80)
    
    # Create test directory
    pdf_dir = Path("wiley_focused_test")
    if pdf_dir.exists():
        import shutil
        shutil.rmtree(pdf_dir)
    pdf_dir.mkdir()
    
    # Mix of DOIs - some may be open access, some require subscription
    test_dois = [
        {
            "doi": "10.1002/anie.202004934",
            "title": "Angewandte Chemie - Template-Directed Copying",
            "expected_access": "subscription"
        },
        {
            "doi": "10.1111/jgs.16372", 
            "title": "Journal of the American Geriatrics Society",
            "expected_access": "subscription"
        },
        {
            "doi": "10.1002/adma.202004328",
            "title": "Advanced Materials",
            "expected_access": "subscription"
        }
    ]
    
    try:
        # Import and setup
        from src.publishers.wiley_publisher import WileyPublisher
        from src.publishers import AuthenticationConfig
        from src.secure_credential_manager import get_credential_manager
        
        print("✅ Wiley publisher imported")
        
        cm = get_credential_manager()
        username, password = cm.get_eth_credentials()
        
        if not (username and password):
            print("❌ No ETH credentials")
            return False
        
        print(f"✅ ETH credentials: {username[:3]}***")
        
        auth_config = AuthenticationConfig(
            username=username,
            password=password,
            institutional_login='eth'
        )
        
        wiley = WileyPublisher(auth_config)
        print("✅ Wiley initialized\n")
        
        successful = 0
        failed = 0
        
        for i, paper in enumerate(test_dois, 1):
            doi = paper["doi"]
            print(f"📄 Paper {i}/{len(test_dois)}: {paper['title']}")
            print(f"   DOI: {doi}")
            print(f"   Expected: {paper['expected_access']} access")
            
            safe_doi = doi.replace('/', '_').replace('.', '_')
            filename = f"wiley_{safe_doi}.pdf"
            save_path = pdf_dir / filename
            
            start_time = time.time()
            
            try:
                print(f"   🔄 Downloading...")
                result = await wiley.download_paper(doi, save_path)
                elapsed = time.time() - start_time
                
                if result.success and save_path.exists():
                    file_size = save_path.stat().st_size
                    
                    if file_size > 10000:  # At least 10KB
                        with open(save_path, 'rb') as f:
                            header = f.read(4)
                            if header == b'%PDF':
                                successful += 1
                                print(f"   ✅ SUCCESS: {file_size/1024:.1f} KB in {elapsed:.1f}s")
                            else:
                                failed += 1
                                print(f"   ❌ Not a valid PDF")
                                save_path.unlink()
                    else:
                        failed += 1
                        print(f"   ❌ File too small: {file_size} bytes")
                        save_path.unlink()
                else:
                    failed += 1
                    error = getattr(result, 'error_message', 'Unknown error')
                    print(f"   ❌ FAILED: {error}")
                    
            except Exception as e:
                failed += 1
                print(f"   ❌ EXCEPTION: {str(e)}")
                logger.error(f"Exception: {e}", exc_info=True)
            
            print()  # Blank line between papers
            
            # Pause between downloads
            if i < len(test_dois):
                await asyncio.sleep(5)
        
        # Summary
        print("=" * 80)
        print(f"📊 RESULTS:")
        print(f"   ✅ Successful: {successful}/{len(test_dois)}")
        print(f"   ❌ Failed: {failed}/{len(test_dois)}")
        print(f"   📈 Success rate: {(successful/len(test_dois)*100):.1f}%")
        
        if successful > 0:
            print(f"\n📁 Downloaded PDFs:")
            for pdf in pdf_dir.glob("*.pdf"):
                size_kb = pdf.stat().st_size / 1024
                print(f"   📄 {pdf.name} ({size_kb:.1f} KB)")
        
        return successful > 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        logger.error(f"Test failed: {e}", exc_info=True)
        return False

async def main():
    success = await test_wiley_focused()
    
    if success:
        print("\n🎉 WILEY WORKS!")
    else:
        print("\n❌ WILEY NEEDS FIXING")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)