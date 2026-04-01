#!/usr/bin/env python3
"""
Fix Anna's Archive URL Extraction
=================================

Fix the parsing logic to filter out non-content results and ensure proper URL extraction.
"""

import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def create_fixed_parse_method():
    """Create the fixed _parse_anna_search method"""
    
    code = '''
    def _parse_anna_search(self, html: str) -> List[SearchResult]:
        """Parse Anna's Archive search results - FIXED VERSION"""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # Find search result items - Anna's Archive uses div.mb-4 for results
        items = soup.find_all('div', class_='mb-4')
        
        for item in items[:20]:
            try:
                # Extract title
                title_elem = item.find('h3') or item.find('a', class_='title') or item.find('div', class_='font-bold')
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                
                # CRITICAL FIX: Filter out non-content results
                if (title.lower().startswith('search settings') or 
                    'settings' in title.lower() or 
                    title.strip() == '' or
                    len(title) < 10):
                    continue
                
                # Extract URL - look for links to actual content
                url = None
                link_elem = title_elem if title_elem.name == 'a' else title_elem.find('a')
                if not link_elem:
                    # Look for any link in the item that goes to md5 or content
                    link_elem = item.find('a', href=re.compile(r'/(md5|record)/'))
                
                if link_elem and link_elem.get('href'):
                    href = link_elem.get('href')
                    if href.startswith('/'):
                        url = urljoin(self.active_base_url, href)
                    else:
                        url = href
                
                # CRITICAL FIX: Only include results with valid URLs
                if not url:
                    continue
                    
                # Additional validation: URL should point to actual content
                if not any(pattern in url for pattern in ['/md5/', '/record/', '/book/']):
                    continue
                
                # Extract metadata
                metadata = {}
                
                # Look for file type
                type_elem = item.find(text=re.compile(r'PDF|EPUB|DJVU', re.IGNORECASE))
                if type_elem:
                    metadata['file_type'] = type_elem.strip()
                
                # Look for file size
                size_elem = item.find(text=re.compile(r'\\d+\\.?\\d*\\s*(MB|KB|GB)', re.IGNORECASE))
                if size_elem:
                    metadata['file_size'] = size_elem.strip()
                
                # Extract authors (if available)
                authors = []
                author_elem = item.find('div', text=re.compile(r'Author|by', re.IGNORECASE))
                if author_elem:
                    author_text = author_elem.get_text()
                    # Try to extract author names
                    author_match = re.search(r'(?:Author|by):?\\s*(.+)', author_text, re.IGNORECASE)
                    if author_match:
                        author_names = author_match.group(1)
                        authors = [a.strip() for a in re.split(r'[,;]|\\s+and\\s+', author_names) if a.strip()]
                
                # Only add results that have both title and URL
                if title and url:
                    results.append(SearchResult(
                        title=title,
                        authors=authors,
                        url=url,
                        source="anna-archive",
                        confidence=0.7,
                        metadata=metadata
                    ))
                
            except Exception as e:
                logger.debug(f"Failed to parse Anna's Archive result: {e}")
                continue
        
        # FINAL FIX: Remove duplicates and ensure all results have URLs
        filtered_results = []
        seen_urls = set()
        
        for result in results:
            if result.url and result.url not in seen_urls:
                seen_urls.add(result.url)
                filtered_results.append(result)
        
        return filtered_results
    '''
    
    return code

async def test_fixed_version():
    """Test the fixed Anna's Archive implementation"""
    
    print("🔧 TESTING FIXED ANNA'S ARCHIVE")
    print("=" * 50)
    
    # Apply the fix by monkey-patching the method
    from src.downloader.universal_downloader import AnnaArchiveDownloader, SearchResult, logger
    from urllib.parse import urljoin
    import re
    
    # Create the fixed method
    def _parse_anna_search_fixed(self, html: str):
        """Parse Anna's Archive search results - FIXED VERSION"""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # Find search result items - Anna's Archive uses div.mb-4 for results
        items = soup.find_all('div', class_='mb-4')
        
        for item in items[:20]:
            try:
                # Extract title
                title_elem = item.find('h3') or item.find('a', class_='title') or item.find('div', class_='font-bold')
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                
                # CRITICAL FIX: Filter out non-content results
                if (title.lower().startswith('search settings') or 
                    'settings' in title.lower() or 
                    title.strip() == '' or
                    len(title) < 10):
                    continue
                
                # Extract URL - look for links to actual content
                url = None
                link_elem = title_elem if title_elem.name == 'a' else title_elem.find('a')
                if not link_elem:
                    # Look for any link in the item that goes to md5 or content
                    link_elem = item.find('a', href=re.compile(r'/(md5|record)/'))
                
                if link_elem and link_elem.get('href'):
                    href = link_elem.get('href')
                    if href.startswith('/'):
                        url = urljoin(self.active_base_url, href)
                    else:
                        url = href
                
                # CRITICAL FIX: Only include results with valid URLs
                if not url:
                    continue
                    
                # Additional validation: URL should point to actual content
                if not any(pattern in url for pattern in ['/md5/', '/record/', '/book/']):
                    continue
                
                # Extract metadata
                metadata = {}
                
                # Look for file type
                type_elem = item.find(text=re.compile(r'PDF|EPUB|DJVU', re.IGNORECASE))
                if type_elem:
                    metadata['file_type'] = type_elem.strip()
                
                # Look for file size
                size_elem = item.find(text=re.compile(r'\\d+\\.?\\d*\\s*(MB|KB|GB)', re.IGNORECASE))
                if size_elem:
                    metadata['file_size'] = size_elem.strip()
                
                # Extract authors (if available)
                authors = []
                author_elem = item.find('div', text=re.compile(r'Author|by', re.IGNORECASE))
                if author_elem:
                    author_text = author_elem.get_text()
                    # Try to extract author names
                    author_match = re.search(r'(?:Author|by):?\\s*(.+)', author_text, re.IGNORECASE)
                    if author_match:
                        author_names = author_match.group(1)
                        authors = [a.strip() for a in re.split(r'[,;]|\\s+and\\s+', author_names) if a.strip()]
                
                # Only add results that have both title and URL
                if title and url:
                    results.append(SearchResult(
                        title=title,
                        authors=authors,
                        url=url,
                        source="anna-archive",
                        confidence=0.7,
                        metadata=metadata
                    ))
                
            except Exception as e:
                print(f"Failed to parse Anna's Archive result: {e}")
                continue
        
        # FINAL FIX: Remove duplicates and ensure all results have URLs
        filtered_results = []
        seen_urls = set()
        
        for result in results:
            if result.url and result.url not in seen_urls:
                seen_urls.add(result.url)
                filtered_results.append(result)
        
        return filtered_results
    
    # Apply the fix
    AnnaArchiveDownloader._parse_anna_search = _parse_anna_search_fixed
    
    # Test the fixed version
    anna = AnnaArchiveDownloader()
    
    print("🔍 Testing search with FIXED parsing...")
    results = await anna.search("machine learning")
    
    print(f"✅ Found {len(results)} results (should be 1, not 2)")
    
    for i, result in enumerate(results):
        print(f"\n   Result {i+1}:")
        print(f"     Title: {result.title[:60]}...")
        print(f"     URL: {result.url}")
        print(f"     Valid URL: {result.url is not None}")
    
    # Test download if we have results
    if results and results[0].url:
        print(f"\n📥 Testing download...")
        try:
            download_result = await anna.download(results[0])
            if download_result.success:
                print(f"   ✅ Download successful!")
                print(f"   Size: {download_result.file_size / 1024:.1f} KB")
                return True
            else:
                print(f"   ❌ Download failed: {download_result.error}")
        except Exception as e:
            print(f"   ❌ Download error: {e}")
    
    # Close session
    if anna.session:
        await anna.session.close()
    
    return len(results) > 0 and all(r.url for r in results)

async def main():
    success = await test_fixed_version()
    
    print("\n" + "=" * 50)
    print("🎯 ANNA'S ARCHIVE FIX RESULTS")
    print("=" * 50)
    
    if success:
        print("✅ Anna's Archive parsing FIXED!")
        print("📝 Key improvements:")
        print("   • Filters out 'Search settings...' entries")
        print("   • Only includes results with valid URLs")
        print("   • Validates URLs point to actual content")
        print("   • Removes duplicates")
        print("\n🚀 Ready to apply fix to production code")
    else:
        print("❌ Fix needs more work")
        print("🔍 Check the debug output above")

if __name__ == "__main__":
    asyncio.run(main())