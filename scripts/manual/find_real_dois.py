#!/usr/bin/env python3
"""
FIND REAL DOIs FROM ACTUAL JOURNALS
===================================

Using the journal ISSNs from the URLs you provided to find REAL papers.
Then test the TDM API with legitimate DOIs.
"""

import requests
import time
from pathlib import Path
from typing import List, Dict

API_KEY = "dkg5eEYuOjlv69V1gw1PuxwK0njBM7N457RWItGZHpihEqCc"

def extract_issn_from_url(url: str) -> str:
    """Extract ISSN from Wiley URL"""
    issn_part = url.split('/')[-1]
    # Convert 14679965 -> 1467-9965
    return f"{issn_part[:4]}-{issn_part[4:]}"

def get_real_dois_from_crossref(issn: str, journal_name: str = "Unknown") -> List[Dict]:
    """Get real DOIs from CrossRef for this ISSN"""
    
    print(f"🔍 Searching CrossRef for ISSN {issn} ({journal_name})")
    
    try:
        url = "https://api.crossref.org/works"
        params = {
            'filter': f'issn:{issn},from-pub-date:2020,until-pub-date:2024',
            'rows': 10,
            'sort': 'published',
            'order': 'desc'
        }
        
        response = requests.get(url, params=params, timeout=20)
        
        if response.status_code == 200:
            data = response.json()
            items = data.get('message', {}).get('items', [])
            
            papers = []
            for item in items:
                doi = item.get('DOI', '')
                title = item.get('title', ['Unknown'])[0] if item.get('title') else 'Unknown'
                published = item.get('published-print', {}).get('date-parts', [[0]])[0]
                year = published[0] if published else 'Unknown'
                
                if doi and title != 'Unknown':
                    papers.append({
                        'doi': doi,
                        'title': title[:100] + '...' if len(title) > 100 else title,
                        'year': year,
                        'journal': journal_name,
                        'issn': issn
                    })
            
            print(f"  ✅ Found {len(papers)} real papers")
            return papers
        else:
            print(f"  ❌ CrossRef error: {response.status_code}")
            return []
    
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return []

def test_real_doi(doi: str, journal: str) -> Dict:
    """Test a real DOI with the TDM API"""
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'ETH-Research/1.0',
        'Accept': 'application/pdf',
        'X-API-Key': API_KEY,
        'Authorization': f'Bearer {API_KEY}',
        'Wiley-TDM-Client-Token': API_KEY,
    })
    
    result = {
        'doi': doi,
        'journal': journal,
        'success': False,
        'status_code': 0,
        'size_mb': 0,
        'error': None
    }
    
    try:
        url = f"https://api.wiley.com/onlinelibrary/tdm/v1/articles/{doi}"
        response = session.get(url, timeout=15)
        
        result['status_code'] = response.status_code
        
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            
            if 'pdf' in content_type.lower() and len(response.content) > 1000:
                size_mb = len(response.content) / (1024 * 1024)
                result['size_mb'] = size_mb
                result['success'] = True
                
                # Save PDF
                downloads_dir = Path("real_dois_test")
                downloads_dir.mkdir(exist_ok=True)
                
                filename = f"real_{doi.replace('/', '_').replace('.', '_')}.pdf"
                save_path = downloads_dir / filename
                
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                
                print(f"    ✅ SUCCESS: {size_mb:.2f} MB")
            else:
                result['error'] = f"Not PDF: {content_type}"
                print(f"    ❌ Not PDF")
        
        elif response.status_code == 403:
            result['error'] = "HTTP 403 - Forbidden"
            print(f"    🚫 Forbidden")
        
        elif response.status_code == 404:
            result['error'] = "HTTP 404 - Not found in Wiley system"
            print(f"    ❌ Not in Wiley system")
        
        elif response.status_code == 500:
            result['error'] = "HTTP 500 - Server error"
            print(f"    🔧 Server error")
        
        else:
            result['error'] = f"HTTP {response.status_code}"
            print(f"    ❌ HTTP {response.status_code}")
    
    except Exception as e:
        result['error'] = str(e)[:50]
        print(f"    ❌ Error: {str(e)[:30]}")
    
    return result

def main():
    """Test REAL papers from the journals you specified"""
    
    # Your journal URLs with likely journal names
    journal_urls = [
        {
            'url': 'https://onlinelibrary.wiley.com/journal/14679965',
            'issn': '1467-9965',
            'likely_name': 'Mathematical Finance'
        },
        {
            'url': 'https://onlinelibrary.wiley.com/journal/14680262', 
            'issn': '1468-0262',
            'likely_name': 'Econometrica'
        },
        {
            'url': 'https://onlinelibrary.wiley.com/journal/15406261',
            'issn': '1540-6261', 
            'likely_name': 'Journal of Finance'
        }
    ]
    
    print("🎯 TESTING REAL PAPERS FROM YOUR ACTUAL JOURNALS")
    print("=" * 70)
    print("Using CrossRef to find legitimate published DOIs")
    print("=" * 70)
    
    all_results = []
    successful_downloads = 0
    total_papers_tested = 0
    
    for journal_info in journal_urls:
        issn = journal_info['issn']
        name = journal_info['likely_name']
        
        print(f"\n{'='*20} {name} {'='*20}")
        print(f"ISSN: {issn}")
        print(f"URL: {journal_info['url']}")
        
        # Get real DOIs from CrossRef
        real_papers = get_real_dois_from_crossref(issn, name)
        
        if not real_papers:
            print(f"❌ No papers found for {name}")
            continue
        
        # Test first 3 real papers from this journal
        for i, paper in enumerate(real_papers[:3], 1):
            print(f"\n  📄 Paper {i}: {paper['title']}")
            print(f"     DOI: {paper['doi']}")
            print(f"     Year: {paper['year']}")
            
            result = test_real_doi(paper['doi'], name)
            all_results.append(result)
            total_papers_tested += 1
            
            if result['success']:
                successful_downloads += 1
            
            # Small delay between tests
            time.sleep(3)
    
    # Final summary
    print(f"\n{'='*30} FINAL RESULTS {'='*30}")
    
    success_rate = (successful_downloads / total_papers_tested * 100) if total_papers_tested > 0 else 0
    
    print(f"Total papers tested: {total_papers_tested}")
    print(f"Successful downloads: {successful_downloads}")
    print(f"Success rate: {success_rate:.1f}%")
    
    if successful_downloads > 0:
        total_size = sum(r['size_mb'] for r in all_results if r['success'])
        print(f"Total size: {total_size:.2f} MB")
        print(f"✅ Your API key DOES work on these journals!")
        
        # Show working journals
        working_journals = set()
        for result in all_results:
            if result['success']:
                working_journals.add(result['journal'])
        
        print(f"\n🎉 WORKING JOURNALS:")
        for journal in working_journals:
            count = sum(1 for r in all_results if r['success'] and r['journal'] == journal)
            size = sum(r['size_mb'] for r in all_results if r['success'] and r['journal'] == journal)
            print(f"  ✅ {journal}: {count} papers ({size:.2f} MB)")
    
    else:
        print(f"❌ No successful downloads")
        
        # Show error breakdown
        error_counts = {}
        for result in all_results:
            error = result['error'] or 'Unknown'
            error_counts[error] = error_counts.get(error, 0) + 1
        
        print(f"\n📊 ERROR BREAKDOWN:")
        for error, count in error_counts.items():
            print(f"  {error}: {count} papers")
    
    print(f"\n🎯 REAL DOI TEST COMPLETE!")
    print(f"Using legitimate papers from CrossRef database")

if __name__ == "__main__":
    main()