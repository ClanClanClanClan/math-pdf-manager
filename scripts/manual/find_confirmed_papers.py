#!/usr/bin/env python3
"""
FIND 10 CONFIRMED ACCESSIBLE WILEY PAPERS
=========================================

Strategy:
1. Use CrossRef API to find REAL, VERIFIED Wiley DOIs from major journals
2. Check each one exists and is accessible 
3. Select 10 confirmed working papers across 10 different journals
4. Then test each 10 times for reliability
"""

import requests
import json
import time
from pathlib import Path
from typing import List, Dict, Optional

API_KEY = "dkg5eEYuOjlv69V1gw1PuxwK0njBM7N457RWItGZHpihEqCc"

class ConfirmedPaperFinder:
    """Find confirmed accessible Wiley papers using CrossRef"""
    
    def __init__(self):
        self.api_key = API_KEY
        self.tdm_base_url = "https://api.wiley.com/onlinelibrary/tdm/v1/articles/"
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ETH-Academic-Research/3.0',
            'Accept': 'application/pdf,application/xml,application/json',
            'X-API-Key': self.api_key,
            'Authorization': f'Bearer {self.api_key}',
            'Wiley-TDM-Client-Token': self.api_key,
        })
        
        print("🔍 FINDING CONFIRMED ACCESSIBLE WILEY PAPERS")
        print("=" * 60)
        print("✅ Using CrossRef to find REAL DOIs")
        print("✅ Testing accessibility before confirmation")
        print("=" * 60)
    
    def get_real_dois_from_crossref(self, journal_issn: str, journal_name: str, max_papers: int = 20) -> List[Dict]:
        """Get real DOIs from CrossRef for a specific journal"""
        
        print(f"\n🔄 Searching CrossRef for {journal_name}...")
        
        try:
            url = "https://api.crossref.org/works"
            params = {
                'filter': f'issn:{journal_issn},from-pub-date:2020,until-pub-date:2023',
                'rows': max_papers,
                'sort': 'relevance',
                'order': 'desc'
            }
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('message', {}).get('items', [])
                
                papers = []
                for item in items:
                    doi = item.get('DOI', '')
                    title = item.get('title', [''])[0] if item.get('title') else ''
                    
                    if doi.startswith('10.1002/') and len(title) > 10:
                        papers.append({
                            'doi': doi,
                            'title': title[:80] + '...' if len(title) > 80 else title,
                            'journal': journal_name
                        })
                
                print(f"  Found {len(papers)} potential papers")
                return papers
            else:
                print(f"  ❌ CrossRef error: {response.status_code}")
                return []
        
        except Exception as e:
            print(f"  ❌ Error: {str(e)[:50]}")
            return []
    
    def test_paper_accessibility(self, paper: Dict) -> bool:
        """Test if a paper is accessible via TDM API"""
        
        doi = paper['doi']
        
        try:
            url = f"{self.tdm_base_url}{doi}"
            response = self.session.get(url, timeout=20)
            
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                if 'pdf' in content_type.lower() and len(response.content) > 1000:
                    size_mb = len(response.content) / (1024 * 1024)
                    print(f"    ✅ {doi} - ACCESSIBLE ({size_mb:.2f} MB)")
                    return True
            
            print(f"    ❌ {doi} - Status {response.status_code}")
            return False
            
        except Exception as e:
            print(f"    ❌ {doi} - Error: {str(e)[:30]}")
            return False
    
    def find_confirmed_papers(self) -> List[Dict]:
        """Find 10 confirmed accessible papers across different journals"""
        
        # Major Wiley journals with their ISSNs
        target_journals = [
            {'issn': '1433-7851', 'name': 'Angewandte Chemie International Edition'},
            {'issn': '0935-9648', 'name': 'Advanced Materials'},
            {'issn': '1616-301X', 'name': 'Advanced Functional Materials'},
            {'issn': '1613-6810', 'name': 'Small'},
            {'issn': '1614-6832', 'name': 'Advanced Energy Materials'},
            {'issn': '2198-3844', 'name': 'Advanced Science'},
            {'issn': '1864-5631', 'name': 'ChemSusChem'},
            {'issn': '1867-3880', 'name': 'Advanced Materials Interfaces'},
            {'issn': '1863-8880', 'name': 'ChemPhysChem'},
            {'issn': '1439-7633', 'name': 'ChemBioChem'},
            {'issn': '1434-193X', 'name': 'European Journal of Organic Chemistry'},
            {'issn': '1521-3773', 'name': 'Angewandte Chemie'},
            {'issn': '2195-1071', 'name': 'ChemistryOpen'},
            {'issn': '2196-0216', 'name': 'Advanced Optical Materials'}
        ]
        
        confirmed_papers = []
        
        for journal_info in target_journals:
            if len(confirmed_papers) >= 10:
                break
                
            print(f"\n{'='*10} {journal_info['name']} {'='*10}")
            
            # Get potential papers from CrossRef
            potential_papers = self.get_real_dois_from_crossref(
                journal_info['issn'], 
                journal_info['name'],
                max_papers=15
            )
            
            if not potential_papers:
                continue
            
            # Test each paper for accessibility
            print(f"  Testing {len(potential_papers)} papers for accessibility...")
            
            found_for_journal = False
            for paper in potential_papers:
                if self.test_paper_accessibility(paper):
                    confirmed_papers.append(paper)
                    print(f"  🎉 CONFIRMED: {paper['journal']}")
                    found_for_journal = True
                    break
                
                time.sleep(0.5)  # Rate limiting
            
            if not found_for_journal:
                print(f"  ❌ No accessible papers found in {journal_info['name']}")
            
            time.sleep(1)  # Rate limiting between journals
        
        return confirmed_papers
    
    def save_confirmed_papers(self, papers: List[Dict]):
        """Save confirmed papers to file"""
        
        output_file = Path("confirmed_accessible_papers.json")
        
        with open(output_file, 'w') as f:
            json.dump(papers, f, indent=2)
        
        print(f"\n💾 Confirmed papers saved to: {output_file}")

def main():
    """Main function to find confirmed papers"""
    
    print("🎯 FINDING 10 CONFIRMED ACCESSIBLE WILEY PAPERS")
    print("=" * 70)
    print("Finding REAL, VERIFIED, ACCESSIBLE papers before reliability test")
    print("=" * 70)
    
    finder = ConfirmedPaperFinder()
    
    confirmed_papers = finder.find_confirmed_papers()
    
    print(f"\n{'='*30} CONFIRMED PAPERS FOUND {'='*30}")
    print(f"Total confirmed accessible papers: {len(confirmed_papers)}")
    
    if confirmed_papers:
        print(f"\n📋 CONFIRMED ACCESSIBLE PAPERS:")
        for i, paper in enumerate(confirmed_papers, 1):
            print(f"{i:2d}. {paper['journal']}")
            print(f"    DOI: {paper['doi']}")
            print(f"    Title: {paper['title']}")
            print()
        
        finder.save_confirmed_papers(confirmed_papers)
        
        print(f"🎉 SUCCESS: Found {len(confirmed_papers)} confirmed accessible papers!")
        print(f"✅ Ready for 10x reliability testing")
        
        if len(confirmed_papers) >= 10:
            print(f"🏆 PERFECT: Found papers across {len(confirmed_papers)} different journals")
        else:
            print(f"⚠️ Found {len(confirmed_papers)} papers - may need to expand search")
    
    else:
        print(f"❌ NO CONFIRMED PAPERS FOUND")
        print(f"API may have access restrictions or rate limiting issues")
    
    print(f"\n🔍 SEARCH COMPLETE!")

if __name__ == "__main__":
    main()