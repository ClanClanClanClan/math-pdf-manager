#!/usr/bin/env python3
"""
FRESH PDF DOWNLOAD TEST
=======================

Starting from ZERO - no old PDFs. This will download fresh PDFs RIGHT NOW.
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

print("\n" + "="*70)
print("FRESH PDF DOWNLOAD TEST - Starting from ZERO")
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*70)
print("\nALL PDFs have been deleted. Starting fresh...\n")

def test_ieee():
    """Test IEEE - should use browser automation"""
    print("\n1. TESTING IEEE (Browser Automation)")
    print("-" * 50)
    
    try:
        from src.publishers.ieee_publisher import IEEEPublisher
        from src.publishers import AuthenticationConfig
        from src.secure_credential_manager import get_credential_manager
        
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
        
        # Create IEEE publisher
        ieee = IEEEPublisher(auth_config)
        
        # Test with a real DOI
        test_doi = "10.1109/5.726791"  # "Gradient-based learning" by LeCun
        print(f"Downloading: {test_doi}")
        
        output_path = Path("FRESH_DOWNLOADS") / f"ieee_{test_doi.replace('/', '_')}.pdf"
        output_path.parent.mkdir(exist_ok=True)
        
        result = ieee.download_paper(test_doi, output_path)
        
        if result.success and output_path.exists():
            file_size = output_path.stat().st_size
            print(f"✅ SUCCESS! Downloaded {file_size:,} bytes")
            
            # Verify it's a PDF
            with open(output_path, 'rb') as f:
                header = f.read(8)
                if header.startswith(b'%PDF'):
                    print(f"✅ Valid PDF: {output_path.name}")
                    return True
        else:
            print(f"❌ Failed: {result.error_message if hasattr(result, 'error_message') else 'Unknown error'}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return False

async def test_scihub():
    """Test Sci-Hub - direct download"""
    print("\n2. TESTING SCI-HUB (Direct Download)")
    print("-" * 50)
    
    try:
        from src.downloader.universal_downloader import SciHubDownloader
        
        sci_hub = SciHubDownloader()
        
        test_doi = "10.1126/science.1102896"  # Graphene paper
        print(f"Downloading: {test_doi}")
        
        result = await sci_hub.download(test_doi)
        
        if result.success:
            output_path = Path("FRESH_DOWNLOADS") / f"scihub_{test_doi.replace('/', '_')}.pdf"
            output_path.parent.mkdir(exist_ok=True)
            
            with open(output_path, 'wb') as f:
                f.write(result.pdf_data)
            
            print(f"✅ SUCCESS! Downloaded {result.file_size:,} bytes")
            print(f"✅ Valid PDF: {output_path.name}")
            
            # Cleanup
            if hasattr(sci_hub, 'session') and sci_hub.session:
                await sci_hub.session.close()
            
            return True
        else:
            print(f"❌ Failed: {result.error}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return False

def test_arxiv():
    """Test ArXiv - direct download"""
    print("\n3. TESTING ARXIV (Direct Download)")
    print("-" * 50)
    
    try:
        import requests
        
        arxiv_id = "1706.03762"  # Transformer paper
        print(f"Downloading: {arxiv_id}")
        
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        response = requests.get(pdf_url)
        
        if response.status_code == 200:
            output_path = Path("FRESH_DOWNLOADS") / f"arxiv_{arxiv_id.replace('/', '_')}.pdf"
            output_path.parent.mkdir(exist_ok=True)
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            print(f"✅ SUCCESS! Downloaded {len(response.content):,} bytes")
            print(f"✅ Valid PDF: {output_path.name}")
            return True
        else:
            print(f"❌ Failed: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return False

async def main():
    """Run all tests"""
    results = []
    
    # Test each publisher
    results.append(("IEEE", test_ieee()))
    results.append(("Sci-Hub", await test_scihub()))
    results.append(("ArXiv", test_arxiv()))
    
    # Show results
    print("\n" + "="*70)
    print("FRESH DOWNLOAD RESULTS")
    print("="*70)
    
    success_count = sum(1 for _, success in results if success)
    print(f"\nSuccess rate: {success_count}/{len(results)}")
    
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {name}")
    
    # List downloaded files
    output_dir = Path("FRESH_DOWNLOADS")
    if output_dir.exists():
        pdfs = list(output_dir.glob("*.pdf"))
        print(f"\nFresh PDFs downloaded: {len(pdfs)}")
        for pdf in pdfs:
            size_mb = pdf.stat().st_size / 1024 / 1024
            print(f"  - {pdf.name} ({size_mb:.2f} MB)")
            
            # Show first line of text
            try:
                import subprocess
                result = subprocess.run(['pdftotext', str(pdf), '-'], capture_output=True, text=True)
                if result.stdout:
                    first_line = result.stdout.strip().split('\n')[0][:80]
                    print(f"    Text: '{first_line}...'")
            except:
                pass
    
    print(f"\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    asyncio.run(main())