#!/usr/bin/env python3
"""
WILEY PUBLISHER REAL TEST
=========================

Focus on testing Wiley publisher with actual PDF downloads.
Let's verify it really works.
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

async def test_wiley_real():
    """Test Wiley publisher with real downloads"""
    
    print("🎯 WILEY PUBLISHER REAL TEST")
    print("=" * 80)
    print("Testing actual PDF downloads from Wiley")
    print("=" * 80)
    
    # Create test directory
    pdf_dir = Path("wiley_test_pdfs")
    if pdf_dir.exists():
        import shutil
        shutil.rmtree(pdf_dir)
    pdf_dir.mkdir()
    
    # Test DOIs
    wiley_dois = [
        "10.1002/anie.202004934",      # Angewandte Chemie
        "10.1111/1467-9523.00123",     # Another Wiley journal
        "10.1002/adma.201906754",      # Advanced Materials
        "10.1002/anie.202108605",      # Angew Chem recent
        "10.1002/adma.202004328"       # Adv Materials 2020
    ]
    
    try:
        # Import Wiley publisher
        from src.publishers.wiley_publisher import WileyPublisher
        from src.publishers import AuthenticationConfig
        from src.secure_credential_manager import get_credential_manager
        
        print("✅ Wiley publisher imported successfully")
        
        # Get credentials
        cm = get_credential_manager()
        username, password = cm.get_eth_credentials()
        
        if not (username and password):
            print("❌ No ETH credentials available")
            return False
        
        print(f"✅ ETH credentials loaded: {username[:3]}***")
        
        # Initialize publisher
        auth_config = AuthenticationConfig(
            username=username,
            password=password,
            institutional_login='eth'
        )
        
        wiley = WileyPublisher(auth_config)
        print("✅ Wiley publisher initialized")
        
        # Test DOI validation
        print("\n📋 Testing DOI validation:")
        for doi in wiley_dois:
            can_handle = wiley.can_handle_doi(doi)
            print(f"   {'✅' if can_handle else '❌'} Can handle DOI: {doi} - {can_handle}")
        
        # Test URL handling
        print("\n📋 Testing URL handling:")
        test_urls = [
            "https://onlinelibrary.wiley.com/doi/10.1002/anie.202004934",
            "https://onlinelibrary.wiley.com/doi/10.1111/1467-9523.00123"
        ]
        for url in test_urls:
            can_handle = wiley.can_handle_url(url)
            print(f"   {'✅' if can_handle else '❌'} Can handle URL: {url}")
        
        # Test actual downloads
        print("\n🔄 Testing actual PDF downloads:")
        print("-" * 60)
        
        successful_downloads = 0
        failed_downloads = 0
        
        for i, doi in enumerate(wiley_dois, 1):
            print(f"\n📄 Paper {i}/{len(wiley_dois)}: {doi}")
            
            safe_doi = doi.replace('/', '_').replace('.', '_')
            filename = f"wiley_{safe_doi}.pdf"
            save_path = pdf_dir / filename
            
            start_time = time.time()
            
            try:
                print(f"   🔄 Attempting download...")
                result = await wiley.download_paper(doi, save_path)
                elapsed = time.time() - start_time
                
                if result.success:
                    # Check if file exists and is valid
                    if save_path.exists():
                        file_size = save_path.stat().st_size
                        
                        if file_size > 1000:  # At least 1KB
                            # Verify it's a PDF
                            with open(save_path, 'rb') as f:
                                header = f.read(4)
                                if header == b'%PDF':
                                    successful_downloads += 1
                                    print(f"   ✅ SUCCESS: Downloaded {file_size/1024:.1f} KB in {elapsed:.1f}s")
                                else:
                                    failed_downloads += 1
                                    print(f"   ❌ FAILED: File is not a valid PDF")
                                    save_path.unlink()
                        else:
                            failed_downloads += 1
                            print(f"   ❌ FAILED: File too small ({file_size} bytes)")
                            save_path.unlink()
                    else:
                        failed_downloads += 1
                        print(f"   ❌ FAILED: File not created")
                else:
                    failed_downloads += 1
                    error_msg = getattr(result, 'error_message', 'Unknown error')
                    print(f"   ❌ FAILED: {error_msg}")
                    
            except Exception as e:
                failed_downloads += 1
                print(f"   ❌ EXCEPTION: {str(e)}")
                logger.error(f"Download exception: {e}", exc_info=True)
            
            # Small pause between downloads
            if i < len(wiley_dois):
                print("   ⏸️  Waiting 5 seconds before next download...")
                await asyncio.sleep(5)
        
        # Final summary
        print("\n" + "=" * 80)
        print("📊 WILEY TEST RESULTS:")
        print("=" * 80)
        total_attempts = successful_downloads + failed_downloads
        success_rate = (successful_downloads / total_attempts * 100) if total_attempts > 0 else 0
        
        print(f"✅ Successful downloads: {successful_downloads}")
        print(f"❌ Failed downloads: {failed_downloads}")
        print(f"📈 Success rate: {success_rate:.1f}%")
        
        # List downloaded files
        if successful_downloads > 0:
            print(f"\n📁 Downloaded PDFs in {pdf_dir}:")
            for pdf_file in pdf_dir.glob("*.pdf"):
                size_kb = pdf_file.stat().st_size / 1024
                print(f"   📄 {pdf_file.name} ({size_kb:.1f} KB)")
        
        return successful_downloads > 0
        
    except Exception as e:
        print(f"\n❌ Test setup failed: {str(e)}")
        logger.error(f"Test setup exception: {e}", exc_info=True)
        return False

async def main():
    """Run the Wiley test"""
    success = await test_wiley_real()
    
    if success:
        print("\n🎉 WILEY TEST SUCCESSFUL!")
        print("Wiley publisher is working and downloading real PDFs")
    else:
        print("\n❌ WILEY TEST FAILED!")
        print("Wiley publisher needs debugging")
        
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)