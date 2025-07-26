#!/usr/bin/env python3
"""
WORKING ETH LIBRARY API DOWNLOADER
==================================

Using the confirmed working endpoint: https://api.library.ethz.ch/research-collection/v1/search
This endpoint returns JSON and accepts our API key!
"""

import requests
import json
import asyncio
import aiohttp
from pathlib import Path
from urllib.parse import quote
from typing import Dict, List, Optional

# Your working ETH Library API credentials
API_KEY = "dkg5eEYuOjlv69V1gw1PuxwK0njBM7N457RWItGZHpihEqCc"
APP_ID = "8cbc0329-19ba-4dbc-af39-864fb0eb5e35"

class WorkingETHLibraryDownloader:
    """Working ETH Library API downloader using confirmed endpoints"""
    
    def __init__(self):
        self.api_key = API_KEY
        self.app_id = APP_ID
        
        # Confirmed working endpoint
        self.research_api = "https://api.library.ethz.ch/research-collection/v1/search"
        
        self.downloads_dir = Path("working_eth_downloads")
        self.downloads_dir.mkdir(exist_ok=True)
        
        # Common headers
        self.headers = {
            'User-Agent': 'ETH-PDF-Downloader/1.0',
            'Accept': 'application/json'
        }
    
    def search_research_collection(self, query: str) -> List[Dict]:
        """Search ETH Research Collection using working API"""
        
        print(f"🔍 Searching Research Collection for: {query}")
        
        # Test different search parameters
        search_params_list = [
            {'q': query, 'apikey': self.api_key},
            {'query': query, 'apikey': self.api_key},
            {'title': query, 'apikey': self.api_key},
            {'doi': query, 'apikey': self.api_key},
            {'identifier': query, 'apikey': self.api_key},
            {'search': query, 'apikey': self.api_key}
        ]
        
        for params in search_params_list:
            try:
                print(f"  Testing params: {list(params.keys())[:2]}")
                
                response = requests.get(
                    self.research_api,
                    params=params,
                    headers=self.headers,
                    timeout=15
                )
                
                print(f"  Status: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"  ✅ JSON response received!")
                        
                        # Print response structure
                        if isinstance(data, dict):
                            print(f"  Keys: {list(data.keys())}")
                            
                            # Look for results in various formats
                            results = self._extract_results(data)
                            
                            if results:
                                print(f"  📚 Found {len(results)} results")
                                return results
                            else:
                                print(f"  ℹ️ No results in this response structure")
                                # Print first few chars to understand structure
                                print(f"  Sample: {str(data)[:200]}...")
                        elif isinstance(data, list):
                            print(f"  📚 Found {len(data)} results (list format)")
                            return data
                        
                    except json.JSONDecodeError as e:
                        print(f"  ❌ JSON decode error: {e}")
                        print(f"  Raw response: {response.text[:200]}...")
                
            except Exception as e:
                print(f"  ❌ Request error: {e}")
        
        return []
    
    def _extract_results(self, data: Dict) -> List[Dict]:
        """Extract results from API response"""
        
        # Common result field names in APIs
        result_fields = ['results', 'items', 'records', 'docs', 'data', 'entries', 'response']
        
        for field in result_fields:
            if field in data:
                results = data[field]
                if isinstance(results, list):
                    return results
                elif isinstance(results, dict) and 'docs' in results:
                    return results['docs']
        
        # If response itself is a single item
        if 'title' in data or 'doi' in data:
            return [data]
        
        return []
    
    def analyze_paper_result(self, paper: Dict) -> Dict:
        """Analyze a paper result to extract useful information"""
        
        print(f"\n📄 Analyzing paper result...")
        
        # Extract common fields
        info = {
            'title': paper.get('title', paper.get('dc.title', 'Unknown')),
            'doi': paper.get('doi', paper.get('dc.identifier.doi', '')),
            'authors': paper.get('authors', paper.get('dc.creator', [])),
            'abstract': paper.get('abstract', paper.get('dc.description.abstract', '')),
            'year': paper.get('year', paper.get('dc.date.issued', '')),
            'pdf_urls': [],
            'access_urls': []
        }
        
        # Print basic info
        print(f"  Title: {info['title']}")
        print(f"  DOI: {info['doi']}")
        print(f"  Authors: {info['authors']}")
        
        # Look for PDF/access URLs in various fields
        url_fields = [
            'pdf_url', 'fulltext_url', 'download_url', 'access_url',
            'dc.identifier.uri', 'handle', 'url', 'link',
            'bitstreams', 'files', 'attachments'
        ]
        
        for field in url_fields:
            if field in paper:
                value = paper[field]
                if isinstance(value, str):
                    if 'pdf' in value.lower() or field in ['pdf_url', 'fulltext_url']:
                        info['pdf_urls'].append(value)
                    else:
                        info['access_urls'].append(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, str):
                            if 'pdf' in item.lower():
                                info['pdf_urls'].append(item)
                            else:
                                info['access_urls'].append(item)
                        elif isinstance(item, dict) and 'url' in item:
                            if 'pdf' in item.get('format', '').lower():
                                info['pdf_urls'].append(item['url'])
                            else:
                                info['access_urls'].append(item['url'])
        
        # Print found URLs
        if info['pdf_urls']:
            print(f"  📄 PDF URLs found: {len(info['pdf_urls'])}")
            for url in info['pdf_urls']:
                print(f"    {url}")
        
        if info['access_urls']:
            print(f"  🔗 Access URLs found: {len(info['access_urls'])}")
            for url in info['access_urls']:
                print(f"    {url}")
        
        return info
    
    async def download_pdf_from_url(self, pdf_url: str, doi: str, title: str = "") -> bool:
        """Download PDF from URL with API authentication"""
        
        print(f"\n📥 Downloading from: {pdf_url}")
        
        # Add API key if not present
        if 'apikey=' not in pdf_url:
            separator = '&' if '?' in pdf_url else '?'
            auth_url = f"{pdf_url}{separator}apikey={self.api_key}"
        else:
            auth_url = pdf_url
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(auth_url, headers=self.headers) as response:
                    
                    print(f"  Status: {response.status}")
                    print(f"  Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
                    
                    if response.status == 200:
                        content_type = response.headers.get('Content-Type', '')
                        
                        if 'pdf' in content_type.lower():
                            pdf_content = await response.read()
                            
                            if len(pdf_content) > 1000:
                                # Save PDF
                                safe_doi = doi.replace('/', '_').replace('.', '_')
                                filename = f"eth_research_{safe_doi}.pdf"
                                save_path = self.downloads_dir / filename
                                
                                with open(save_path, 'wb') as f:
                                    f.write(pdf_content)
                                
                                size_mb = len(pdf_content) / (1024 * 1024)
                                print(f"  ✅ SUCCESS: {save_path} ({size_mb:.2f} MB)")
                                return True
                            else:
                                print(f"  ❌ PDF too small: {len(pdf_content)} bytes")
                        else:
                            print(f"  ❌ Not PDF content: {content_type}")
                            
                            # If HTML, might be access page - try to extract real PDF URL
                            if 'html' in content_type.lower():
                                html_content = await response.text()
                                pdf_links = self._extract_pdf_links_from_html(html_content)
                                
                                if pdf_links:
                                    print(f"  🔍 Found PDF links in HTML: {len(pdf_links)}")
                                    for link in pdf_links[:2]:  # Try first 2
                                        print(f"    Trying: {link}")
                                        success = await self.download_pdf_from_url(link, doi, title)
                                        if success:
                                            return True
                    else:
                        print(f"  ❌ Access denied: {response.status}")
        
        except Exception as e:
            print(f"  ❌ Download error: {e}")
        
        return False
    
    def _extract_pdf_links_from_html(self, html: str) -> List[str]:
        """Extract PDF links from HTML content"""
        import re
        
        # Look for PDF links in HTML
        pdf_patterns = [
            r'href="([^"]*\.pdf[^"]*)"',
            r'href="([^"]*pdf[^"]*)"',
            r'src="([^"]*\.pdf[^"]*)"'
        ]
        
        pdf_links = []
        for pattern in pdf_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            pdf_links.extend(matches)
        
        # Clean and validate URLs
        valid_links = []
        for link in pdf_links:
            if link.startswith('http'):
                valid_links.append(link)
            elif link.startswith('/'):
                # Relative URL - add base domain
                valid_links.append(f"https://api.library.ethz.ch{link}")
        
        return list(set(valid_links))  # Remove duplicates
    
    async def download_paper_by_doi(self, doi: str, title: str = "") -> bool:
        """Complete workflow: search and download paper by DOI"""
        
        print(f"\n{'='*20} DOWNLOADING PAPER {'='*20}")
        print(f"DOI: {doi}")
        print(f"Title: {title}")
        print("-" * 60)
        
        # Search for paper
        results = self.search_research_collection(doi)
        
        if not results:
            print("❌ Paper not found in ETH Research Collection")
            return False
        
        # Analyze each result
        for i, result in enumerate(results):
            print(f"\n📋 Result {i+1}/{len(results)}:")
            
            paper_info = self.analyze_paper_result(result)
            
            # Try to download from PDF URLs
            if paper_info['pdf_urls']:
                for pdf_url in paper_info['pdf_urls']:
                    success = await self.download_pdf_from_url(pdf_url, doi, paper_info['title'])
                    if success:
                        return True
            
            # Try access URLs as fallback
            if paper_info['access_urls']:
                for access_url in paper_info['access_urls']:
                    success = await self.download_pdf_from_url(access_url, doi, paper_info['title'])
                    if success:
                        return True
        
        print("❌ Could not download PDF from any found URLs")
        return False
    
    async def batch_download(self, papers: List[Dict]) -> Dict:
        """Download multiple papers"""
        
        print("🚀 ETH LIBRARY API BATCH DOWNLOADER")
        print("=" * 70)
        print(f"Using confirmed working API endpoint")
        print(f"API Key: {self.api_key[:20]}...")
        print("=" * 70)
        
        results = {
            'successful': 0,
            'failed': 0,
            'papers': []
        }
        
        for i, paper in enumerate(papers, 1):
            print(f"\n{'='*15} PAPER {i}/{len(papers)} {'='*15}")
            
            doi = paper.get('doi', '')
            title = paper.get('title', '')
            
            if not doi:
                print("❌ No DOI provided")
                results['failed'] += 1
                continue
            
            success = await self.download_paper_by_doi(doi, title)
            
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

async def main():
    """Main function"""
    
    print("🎯 WORKING ETH LIBRARY API DOWNLOADER")
    print("=" * 80)
    print("Using confirmed working endpoint with your API key!")
    print("=" * 80)
    
    downloader = WorkingETHLibraryDownloader()
    
    # Test papers
    papers = [
        {
            'doi': '10.1002/anie.202004934',
            'title': 'Angewandte Chemie Paper'
        },
        {
            'doi': '10.1111/1467-9523.00201', 
            'title': 'Economica Paper'
        },
        {
            'doi': '10.1002/adma.202001924',
            'title': 'Advanced Materials Paper'
        }
    ]
    
    results = await downloader.batch_download(papers)
    
    # Final results
    print(f"\n{'='*30} FINAL RESULTS {'='*30}")
    print(f"Total papers: {len(papers)}")
    print(f"Successfully downloaded: {results['successful']}")
    print(f"Failed: {results['failed']}")
    success_rate = (results['successful'] / len(papers)) * 100 if papers else 0
    print(f"Success rate: {success_rate:.1f}%")
    
    if results['successful'] > 0:
        print(f"\n📁 Downloaded files:")
        pdf_files = list(downloader.downloads_dir.glob("*.pdf"))
        for pdf_file in pdf_files:
            size_mb = pdf_file.stat().st_size / (1024 * 1024)
            print(f"  📄 {pdf_file.name} ({size_mb:.2f} MB)")
        
        print(f"\n🎉 ETH LIBRARY API SUCCESS!")
        print(f"✅ API authentication working")
        print(f"✅ Research Collection API functional") 
        print(f"✅ PDF downloads successful")
        print(f"📂 Files saved in: {downloader.downloads_dir}")

if __name__ == "__main__":
    asyncio.run(main())