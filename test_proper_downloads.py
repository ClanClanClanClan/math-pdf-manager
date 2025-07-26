#!/usr/bin/env python3
"""
Test PROPER browser automation that actually downloads PDFs
"""

import asyncio
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

async def test_proper_ieee_download():
    """Test IEEE download with proper modal handling"""
    print("\n" + "="*60)
    print("Testing PROPER IEEE Download")
    print("="*60)
    
    try:
        from src.downloader.proper_browser_automation import IEEEBrowserDownloader
        from src.secure_credential_manager import SecureCredentialManager
        
        # Get credentials
        cred_manager = SecureCredentialManager()
        username = cred_manager.get_credential("eth_username")
        password = cred_manager.get_credential("eth_password")
        
        if not username or not password:
            print("✗ No ETH credentials found")
            return False
        
        print(f"✓ Using ETH credentials: {username[:3]}***")
        
        # Create downloader
        ieee = IEEEBrowserDownloader({
            'username': username,
            'password': password
        })
        
        # Test with known IEEE paper
        test_doi = "10.1109/JPROC.2018.2820126"
        print(f"Testing DOI: {test_doi}")
        
        # Download
        result = await ieee.download(test_doi)
        
        if result.success:
            print(f"✅ IEEE download successful!")
            print(f"   Size: {result.file_size / 1024 / 1024:.2f} MB")
            
            # Save PDF
            output_dir = Path("proper_downloads")
            output_dir.mkdir(exist_ok=True)
            
            pdf_path = output_dir / f"ieee_{test_doi.replace('/', '_')}.pdf"
            with open(pdf_path, 'wb') as f:
                f.write(result.pdf_data)
            
            print(f"   Saved to: {pdf_path}")
            
            # Verify it's a real PDF
            with open(pdf_path, 'rb') as f:
                header = f.read(4)
                if header == b'%PDF':
                    print("   ✓ Verified: Valid PDF file")
                    return True
                else:
                    print("   ✗ Error: Not a valid PDF")
                    return False
        else:
            print(f"✗ IEEE download failed: {result.error}")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        try:
            await ieee.cleanup()
        except:
            pass

async def test_proper_springer_download():
    """Test Springer download with authentication"""
    print("\n" + "="*60)
    print("Testing PROPER Springer Download")
    print("="*60)
    
    try:
        from src.downloader.proper_browser_automation import SpringerBrowserDownloader
        from src.secure_credential_manager import SecureCredentialManager
        
        # Get credentials
        cred_manager = SecureCredentialManager()
        username = cred_manager.get_credential("eth_username")
        password = cred_manager.get_credential("eth_password")
        
        print(f"✓ Using ETH credentials: {username[:3]}***")
        
        # Create downloader
        springer = SpringerBrowserDownloader({
            'username': username,
            'password': password
        })
        
        # Test with a paper that REQUIRES authentication (not open access)
        test_doi = "10.1007/s10994-013-5413-0"  # Closed access paper
        print(f"Testing DOI: {test_doi} (requires authentication)")
        
        # Download
        result = await springer.download(test_doi)
        
        if result.success:
            print(f"✅ Springer download successful!")
            print(f"   Size: {result.file_size / 1024 / 1024:.2f} MB")
            
            # Save PDF
            output_dir = Path("proper_downloads")
            output_dir.mkdir(exist_ok=True)
            
            pdf_path = output_dir / f"springer_{test_doi.replace('/', '_')}.pdf"
            with open(pdf_path, 'wb') as f:
                f.write(result.pdf_data)
            
            print(f"   Saved to: {pdf_path}")
            
            # Verify
            with open(pdf_path, 'rb') as f:
                header = f.read(4)
                if header == b'%PDF':
                    print("   ✓ Verified: Valid PDF file")
                    return True
        else:
            print(f"✗ Springer download failed: {result.error}")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            await springer.cleanup()
        except:
            pass

async def test_proper_wiley_download():
    """Test Wiley download with proper authentication"""
    print("\n" + "="*60)
    print("Testing PROPER Wiley Download")
    print("="*60)
    
    try:
        from src.downloader.proper_browser_automation import WileyBrowserDownloader
        from src.secure_credential_manager import SecureCredentialManager
        
        # Get credentials
        cred_manager = SecureCredentialManager()
        username = cred_manager.get_credential("eth_username")
        password = cred_manager.get_credential("eth_password")
        
        print(f"✓ Using ETH credentials: {username[:3]}***")
        
        # Create downloader
        wiley = WileyBrowserDownloader({
            'username': username,
            'password': password
        })
        
        # Test with Wiley paper
        test_doi = "10.1002/anie.201506954"
        print(f"Testing DOI: {test_doi}")
        
        # Download
        result = await wiley.download(test_doi)
        
        if result.success:
            print(f"✅ Wiley download successful!")
            print(f"   Size: {result.file_size / 1024 / 1024:.2f} MB")
            
            # Save PDF
            output_dir = Path("proper_downloads")
            output_dir.mkdir(exist_ok=True)
            
            pdf_path = output_dir / f"wiley_{test_doi.replace('/', '_')}.pdf"
            with open(pdf_path, 'wb') as f:
                f.write(result.pdf_data)
            
            print(f"   Saved to: {pdf_path}")
            return True
        else:
            print(f"✗ Wiley download failed: {result.error}")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            await wiley.cleanup()
        except:
            pass

async def main():
    """Run all proper download tests"""
    print("Testing PROPER Browser Automation")
    print("Following IEEE/SIAM working patterns")
    print("="*60)
    
    # Check requirements
    try:
        from playwright.async_api import async_playwright
        print("✓ Playwright available")
    except ImportError:
        print("✗ Install Playwright first:")
        print("  pip install playwright")
        print("  playwright install")
        return
    
    results = []
    
    # Test each publisher
    print("\nNote: This will open browser windows for authentication")
    print("      Each test may take 30-60 seconds")
    
    # IEEE
    ieee_success = await test_proper_ieee_download()
    results.append(('IEEE', ieee_success))
    
    # Small delay between tests
    await asyncio.sleep(5)
    
    # Springer
    springer_success = await test_proper_springer_download()
    results.append(('Springer', springer_success))
    
    await asyncio.sleep(5)
    
    # Wiley
    wiley_success = await test_proper_wiley_download()
    results.append(('Wiley', wiley_success))
    
    # Summary
    print("\n" + "="*60)
    print("PROPER DOWNLOAD TEST SUMMARY")
    print("="*60)
    
    successful = sum(1 for _, success in results if success)
    print(f"✓ Successful downloads: {successful}/{len(results)}")
    
    for publisher, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {publisher}")
    
    # Check downloaded files
    output_dir = Path("proper_downloads")
    if output_dir.exists():
        pdfs = list(output_dir.glob("*.pdf"))
        print(f"\nDownloaded PDFs: {len(pdfs)}")
        for pdf in pdfs:
            size_mb = pdf.stat().st_size / 1024 / 1024
            print(f"  - {pdf.name} ({size_mb:.2f} MB)")
    
    print("\nConclusion:")
    if successful == len(results):
        print("✅ All publishers can download real PDFs with proper authentication!")
    else:
        print("⚠️  Some publishers need additional work")
        print("    Check browser windows for manual intervention points")

if __name__ == "__main__":
    asyncio.run(main())