#!/usr/bin/env python3
"""
ETH LIBRARY API WILEY DOWNLOADER
=================================

Uses ETH Library API access for 100% automated Wiley downloads.
No VPN needed, no browser automation, just clean API calls.

This is the professional, long-term solution.
"""

import asyncio
import aiohttp
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional
import requests
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).parent))


class ETHLibraryAPIClient:
    """ETH Library API client for accessing academic resources"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.library.ethz.ch/v1"  # Example URL
        self.session = None
        self.downloads_dir = Path("eth_api_downloads")
        self.downloads_dir.mkdir(exist_ok=True)
    
    async def initialize(self):
        """Initialize async session with API authentication"""
        
        self.session = aiohttp.ClientSession(
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Accept': 'application/json',
                'User-Agent': 'ETH-Library-API-Client/1.0'
            }
        )
        
        # Test API connection
        test_success = await self.test_api_connection()
        if test_success:
            print("✅ ETH Library API connection established")
            return True
        else:
            print("❌ ETH Library API connection failed")
            return False
    
    async def test_api_connection(self) -> bool:
        """Test if API key is valid and API is accessible"""
        
        try:
            async with self.session.get(f"{self.base_url}/status") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"API Status: {data.get('status', 'Unknown')}")
                    return True
                else:
                    print(f"API test failed with status: {response.status}")
                    return False
        except Exception as e:
            print(f"API connection error: {e}")
            return False
    
    async def search_paper_by_doi(self, doi: str) -> Optional[Dict]:
        """Search for a paper in ETH Library by DOI"""
        
        print(f"\n🔍 Searching ETH Library for DOI: {doi}")
        
        # ETH Library API endpoints (examples - adjust based on actual API)
        search_endpoints = [
            f"{self.base_url}/search?doi={quote(doi)}",
            f"{self.base_url}/resources?identifier={quote(doi)}",
            f"{self.base_url}/holdings?doi={quote(doi)}"
        ]
        
        for endpoint in search_endpoints:
            try:
                async with self.session.get(endpoint) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Parse response to find paper info
                        if data.get('results') or data.get('items'):
                            paper_info = self._parse_paper_info(data)
                            if paper_info:
                                print(f"✅ Found paper: {paper_info.get('title', 'Unknown')}")
                                return paper_info
                    
            except Exception as e:
                print(f"Search error for {endpoint}: {e}")
                continue
        
        print(f"❌ Paper not found in ETH Library")
        return None
    
    def _parse_paper_info(self, api_response: Dict) -> Optional[Dict]:
        """Parse API response to extract paper information"""
        
        # This depends on actual API response format
        # Example parsing logic:
        
        results = api_response.get('results', api_response.get('items', []))
        
        if results and isinstance(results, list) and len(results) > 0:
            paper = results[0]
            
            return {
                'title': paper.get('title', 'Unknown'),
                'doi': paper.get('doi', ''),
                'authors': paper.get('authors', []),
                'journal': paper.get('journal', ''),
                'year': paper.get('year', ''),
                'pdf_url': paper.get('pdf_url', ''),
                'access_url': paper.get('access_url', ''),
                'eth_id': paper.get('id', '')
            }
        
        return None
    
    async def get_pdf_access_url(self, paper_info: Dict) -> Optional[str]:
        """Get authenticated PDF access URL from ETH Library"""
        
        print("🔑 Getting authenticated PDF access...")
        
        # Method 1: Direct PDF URL from search results
        if paper_info.get('pdf_url'):
            return paper_info['pdf_url']
        
        # Method 2: Request PDF access token
        if paper_info.get('eth_id'):
            try:
                access_endpoint = f"{self.base_url}/access/{paper_info['eth_id']}/pdf"
                
                async with self.session.post(access_endpoint) as response:
                    if response.status == 200:
                        data = await response.json()
                        pdf_url = data.get('pdf_url', data.get('download_url'))
                        
                        if pdf_url:
                            print("✅ Got authenticated PDF URL")
                            return pdf_url
                    else:
                        print(f"❌ Access request failed: {response.status}")
                        
            except Exception as e:
                print(f"Access URL error: {e}")
        
        # Method 3: Use EZproxy URL construction
        if paper_info.get('access_url'):
            ezproxy_url = self._construct_ezproxy_url(paper_info['access_url'])
            return ezproxy_url
        
        return None
    
    def _construct_ezproxy_url(self, original_url: str) -> str:
        """Construct EZproxy URL for authenticated access"""
        
        # ETH EZproxy pattern
        if 'wiley.com' in original_url:
            # Transform: https://onlinelibrary.wiley.com/...
            # To: https://onlinelibrary-wiley-com.ezproxy.ethz.ch/...
            
            ezproxy_url = original_url.replace(
                'onlinelibrary.wiley.com',
                'onlinelibrary-wiley-com.ezproxy.ethz.ch'
            )
            
            return ezproxy_url
        
        return original_url
    
    async def download_pdf(self, pdf_url: str, doi: str, title: str = "") -> bool:
        """Download PDF from authenticated URL"""
        
        print(f"\n📥 Downloading: {title or doi}")
        
        try:
            async with self.session.get(pdf_url) as response:
                if response.status == 200:
                    content_type = response.headers.get('Content-Type', '')
                    
                    if 'pdf' in content_type.lower():
                        # Download PDF
                        pdf_content = await response.read()
                        
                        if len(pdf_content) > 1000:
                            # Save PDF
                            filename = f"eth_api_{doi.replace('/', '_').replace('.', '_')}.pdf"
                            save_path = self.downloads_dir / filename
                            
                            with open(save_path, 'wb') as f:
                                f.write(pdf_content)
                            
                            size_mb = len(pdf_content) / (1024 * 1024)
                            print(f"✅ SUCCESS: {save_path} ({size_mb:.2f} MB)")
                            return True
                        else:
                            print(f"❌ PDF too small: {len(pdf_content)} bytes")
                    else:
                        print(f"❌ Not a PDF response: {content_type}")
                else:
                    print(f"❌ Download failed with status: {response.status}")
                    
        except Exception as e:
            print(f"❌ Download error: {e}")
        
        return False
    
    async def download_paper_by_doi(self, doi: str) -> bool:
        """Complete workflow: search and download paper by DOI"""
        
        # Search for paper
        paper_info = await self.search_paper_by_doi(doi)
        
        if not paper_info:
            print(f"❌ Cannot download - paper not found in ETH Library")
            return False
        
        # Get PDF access URL
        pdf_url = await self.get_pdf_access_url(paper_info)
        
        if not pdf_url:
            print(f"❌ Cannot get PDF access URL")
            return False
        
        # Download PDF
        success = await self.download_pdf(
            pdf_url, 
            doi, 
            paper_info.get('title', '')
        )
        
        return success
    
    async def batch_download(self, papers: List[Dict]) -> Dict:
        """Download multiple papers via API"""
        
        print("🚀 ETH LIBRARY API BATCH DOWNLOAD")
        print("=" * 70)
        print("100% Automated - No VPN, No Browser, Just API!")
        print("=" * 70)
        
        results = {
            'successful': 0,
            'failed': 0,
            'papers': []
        }
        
        for i, paper in enumerate(papers, 1):
            print(f"\n{'='*20} PAPER {i}/{len(papers)} {'='*20}")
            
            doi = paper.get('doi', '')
            title = paper.get('title', '')
            
            if not doi:
                print("❌ No DOI provided")
                results['failed'] += 1
                continue
            
            success = await self.download_paper_by_doi(doi)
            
            if success:
                results['successful'] += 1
                print(f"✅ PAPER {i} SUCCESS")
            else:
                results['failed'] += 1
                print(f"❌ PAPER {i} FAILED")
            
            results['papers'].append({
                'doi': doi,
                'title': title,
                'success': success
            })
        
        return results
    
    async def close(self):
        """Close API session"""
        if self.session:
            await self.session.close()


class ETHAPIWileyDownloader:
    """Main downloader using ETH Library API"""
    
    def __init__(self):
        self.api_key = None
        self.client = None
    
    def load_api_key(self) -> bool:
        """Load API key from environment or file"""
        
        import os
        
        # Try environment variable first
        self.api_key = os.environ.get('ETH_LIBRARY_API_KEY')
        
        if not self.api_key:
            # Try file
            api_key_file = Path.home() / '.eth_library_api_key'
            if api_key_file.exists():
                self.api_key = api_key_file.read_text().strip()
        
        if not self.api_key:
            print("❌ No API key found")
            print("\n📝 To set up API access:")
            print("1. Request API key from ETH Library")
            print("2. Save it in one of these ways:")
            print("   - Environment: export ETH_LIBRARY_API_KEY='your-key'")
            print("   - File: echo 'your-key' > ~/.eth_library_api_key")
            return False
        
        print(f"✅ API key loaded: {self.api_key[:10]}...")
        return True
    
    async def run(self, papers: List[Dict]):
        """Run the API-based downloader"""
        
        if not self.load_api_key():
            print("\n💡 Request API key from:")
            print("   ETH Library: library@ethz.ch")
            print("   Subject: API access for academic paper downloads")
            return False
        
        # Initialize API client
        self.client = ETHLibraryAPIClient(self.api_key)
        
        if not await self.client.initialize():
            print("❌ Failed to initialize API client")
            return False
        
        # Download papers
        results = await self.client.batch_download(papers)
        
        # Show results
        print(f"\n{'='*30} FINAL RESULTS {'='*30}")
        print(f"Total papers: {len(papers)}")
        print(f"Successfully downloaded: {results['successful']}")
        print(f"Failed: {results['failed']}")
        success_rate = (results['successful'] / len(papers)) * 100 if papers else 0
        print(f"Success rate: {success_rate:.1f}%")
        
        if results['successful'] > 0:
            print(f"\n📁 Downloaded files in: {self.client.downloads_dir}")
            
            pdf_files = list(self.client.downloads_dir.glob("*.pdf"))
            for pdf_file in pdf_files:
                size_mb = pdf_file.stat().st_size / (1024 * 1024)
                print(f"   📄 {pdf_file.name} ({size_mb:.2f} MB)")
            
            print(f"\n🎉 API DOWNLOADER SUCCESS!")
            print(f"🤖 100% Automated")
            print(f"🔌 No VPN needed")
            print(f"🌐 No browser automation")
            print(f"📄 Clean API access")
        
        # Cleanup
        await self.client.close()
        
        return results['successful'] > 0


async def main():
    """Main function"""
    
    print("🎯 ETH LIBRARY API WILEY DOWNLOADER")
    print("=" * 80)
    print("Professional solution using official API access")
    print("=" * 80)
    
    downloader = ETHAPIWileyDownloader()
    
    # Test papers
    papers = [
        {
            'doi': '10.1002/anie.202004934',
            'title': 'Angewandte Chemie - Test Paper'
        },
        {
            'doi': '10.1111/1467-9523.00201',
            'title': 'Economica - Test Paper'
        },
        {
            'doi': '10.1002/adma.202001924',
            'title': 'Advanced Materials - Test Paper'
        }
    ]
    
    success = await downloader.run(papers)
    
    if success:
        print("\n🎉 ETH LIBRARY API ACCESS WORKS!")
        print("This is the best long-term solution")
    else:
        print("\n❌ API access needs configuration")
        print("Contact ETH Library for API credentials")


# Also create a simple example of how to use with CrossRef API
def crossref_example():
    """Example using CrossRef API (publicly available)"""
    
    print("\n📚 CROSSREF API EXAMPLE (Public API)")
    print("=" * 60)
    
    doi = "10.1002/anie.202004934"
    crossref_url = f"https://api.crossref.org/works/{doi}"
    
    try:
        response = requests.get(crossref_url)
        if response.status_code == 200:
            data = response.json()
            message = data.get('message', {})
            
            print(f"Title: {message.get('title', ['Unknown'])[0]}")
            print(f"Journal: {message.get('container-title', ['Unknown'])[0]}")
            print(f"Authors: {len(message.get('author', []))} authors")
            print(f"Published: {message.get('published-print', {}).get('date-parts', [[]])[0]}")
            
            # Check for open access
            if message.get('link'):
                for link in message['link']:
                    if link.get('content-type') == 'application/pdf':
                        print(f"PDF Link: {link.get('URL')}")
            
            print("\n💡 Note: CrossRef provides metadata, not always PDFs")
            print("   ETH Library API would provide actual PDF access")
    except Exception as e:
        print(f"CrossRef error: {e}")


if __name__ == "__main__":
    # Run async main
    asyncio.run(main())
    
    # Show CrossRef example
    crossref_example()