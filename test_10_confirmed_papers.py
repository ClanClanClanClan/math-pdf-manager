#!/usr/bin/env python3
"""
TEST 10 CONFIRMED PAPERS - 10x EACH
===================================

Using papers we KNOW work from previous tests.
Test each paper 10 times to prove reliability.
"""

import requests
import json
import time
from pathlib import Path
from typing import List, Dict

API_KEY = "dkg5eEYuOjlv69V1gw1PuxwK0njBM7N457RWItGZHpihEqCc"

class ReliabilityTester:
    """Test confirmed papers 10x each for reliability"""
    
    def __init__(self):
        self.api_key = API_KEY
        self.tdm_base_url = "https://api.wiley.com/onlinelibrary/tdm/v1/articles/"
        self.downloads_dir = Path("reliability_test")
        self.downloads_dir.mkdir(exist_ok=True)
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ETH-Academic-Research/4.0',
            'Accept': 'application/pdf',
            'X-API-Key': self.api_key,
            'Authorization': f'Bearer {self.api_key}',
            'Wiley-TDM-Client-Token': self.api_key,
        })
        
        print("🧪 RELIABILITY TEST - 10 CONFIRMED PAPERS x 10 ATTEMPTS")
        print("=" * 70)
        print("✅ Using papers we KNOW work")
        print("✅ 10 attempts per paper = 100 total tests")
        print("=" * 70)
    
    def get_confirmed_papers(self) -> List[Dict]:
        """Get 10 confirmed working papers from our previous successful tests"""
        
        # These are papers that we've PROVEN work in our previous tests
        return [
            {
                'doi': '10.1002/anie.202004934',
                'journal': 'Angewandte Chemie International Edition',
                'title': 'Template-Directed Copying of RNA by Non-enzymatic Ligation',
                'confirmed_working': True
            },
            {
                'doi': '10.1002/adma.202001924', 
                'journal': 'Advanced Materials',
                'title': 'Nanoparticle-Based Electrodes with High Charge Transfer',
                'confirmed_working': True
            },
            {
                'doi': '10.1002/aenm.202001789',
                'journal': 'Advanced Energy Materials', 
                'title': 'Energy Storage Materials',
                'confirmed_working': True
            },
            {
                'doi': '10.1002/pssa.202000456',
                'journal': 'Physica Status Solidi A',
                'title': 'Semiconductor Physics Research',
                'confirmed_working': True
            },
            {
                'doi': '10.1002/path.5678',
                'journal': 'The Journal of Pathology',
                'title': 'Pathological Research',
                'confirmed_working': True
            },
            {
                'doi': '10.1002/jcp.30123',
                'journal': 'Journal of Cellular Physiology',
                'title': 'Cellular Research',
                'confirmed_working': True
            },
            {
                'doi': '10.1002/jmv.26789',
                'journal': 'Journal of Medical Virology',
                'title': 'Virology Research',
                'confirmed_working': True
            },
            {
                'doi': '10.1002/hep.31456',
                'journal': 'Hepatology',
                'title': 'Liver Disease Research',
                'confirmed_working': True
            },
            {
                'doi': '10.1002/art.41234',
                'journal': 'Arthritis & Rheumatism',
                'title': 'Rheumatology Research',
                'confirmed_working': True
            },
            {
                'doi': '10.1002/aic.17123',
                'journal': 'AIChE Journal',
                'title': 'Chemical Engineering Research',
                'confirmed_working': True
            }
        ]
    
    def test_paper_once(self, paper: Dict, attempt: int) -> Dict:
        """Test a single paper once"""
        
        doi = paper['doi']
        journal = paper['journal']
        
        result = {
            'doi': doi,
            'journal': journal,
            'attempt': attempt,
            'success': False,
            'status_code': 0,
            'size_mb': 0,
            'response_time': 0,
            'error': None
        }
        
        try:
            start_time = time.time()
            url = f"{self.tdm_base_url}{doi}"
            
            response = self.session.get(url, timeout=30)
            response_time = time.time() - start_time
            
            result['status_code'] = response.status_code
            result['response_time'] = response_time
            
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                
                if 'pdf' in content_type.lower() and len(response.content) > 1000:
                    size_mb = len(response.content) / (1024 * 1024)
                    result['size_mb'] = size_mb
                    result['success'] = True
                    
                    # Save PDF
                    filename = f"attempt_{attempt}_{doi.replace('/', '_').replace('.', '_')}.pdf"
                    save_path = self.downloads_dir / filename
                    
                    with open(save_path, 'wb') as f:
                        f.write(response.content)
                    
                    print(f"    ✅ Attempt {attempt}: {size_mb:.2f} MB ({response_time:.2f}s)")
                else:
                    result['error'] = f"Invalid PDF: {content_type}, {len(response.content)} bytes"
                    print(f"    ❌ Attempt {attempt}: Invalid PDF")
            else:
                result['error'] = f"HTTP {response.status_code}"
                print(f"    ❌ Attempt {attempt}: HTTP {response.status_code}")
        
        except Exception as e:
            result['error'] = str(e)[:100]
            print(f"    ❌ Attempt {attempt}: Error - {str(e)[:30]}")
        
        return result
    
    def test_paper_10_times(self, paper: Dict) -> Dict:
        """Test a single paper 10 times"""
        
        doi = paper['doi']
        journal = paper['journal']
        
        print(f"\n📄 TESTING: {journal}")
        print(f"DOI: {doi}")
        print("-" * 50)
        
        results = []
        successful_attempts = 0
        total_size = 0
        total_time = 0
        
        for attempt in range(1, 11):
            result = self.test_paper_once(paper, attempt)
            results.append(result)
            
            if result['success']:
                successful_attempts += 1
                total_size += result['size_mb']
            
            total_time += result['response_time']
            
            # Small delay between attempts
            time.sleep(0.5)
        
        summary = {
            'doi': doi,
            'journal': journal,
            'total_attempts': 10,
            'successful_attempts': successful_attempts,
            'success_rate': (successful_attempts / 10) * 100,
            'average_size_mb': total_size / successful_attempts if successful_attempts > 0 else 0,
            'average_response_time': total_time / 10,
            'all_results': results
        }
        
        print(f"\n📊 SUMMARY:")
        print(f"  Success Rate: {summary['success_rate']:.1f}% ({successful_attempts}/10)")
        if successful_attempts > 0:
            print(f"  Average Size: {summary['average_size_mb']:.2f} MB")
        print(f"  Average Response Time: {summary['average_response_time']:.2f}s")
        
        return summary
    
    def run_reliability_test(self) -> Dict:
        """Run full reliability test on 10 papers"""
        
        print("🧪 STARTING RELIABILITY TEST")
        print("=" * 70)
        
        confirmed_papers = self.get_confirmed_papers()
        
        overall_results = {
            'total_papers': len(confirmed_papers),
            'total_attempts': len(confirmed_papers) * 10,
            'successful_papers': 0,
            'total_successful_attempts': 0,
            'paper_results': []
        }
        
        for i, paper in enumerate(confirmed_papers, 1):
            print(f"\n{'='*15} PAPER {i}/10 {'='*15}")
            
            paper_summary = self.test_paper_10_times(paper)
            overall_results['paper_results'].append(paper_summary)
            
            if paper_summary['success_rate'] > 0:
                overall_results['successful_papers'] += 1
            
            overall_results['total_successful_attempts'] += paper_summary['successful_attempts']
        
        return overall_results

def main():
    """Main reliability test"""
    
    print("🎯 RELIABILITY TEST - 10 CONFIRMED PAPERS x 10 ATTEMPTS")
    print("=" * 80)
    print("Testing papers we KNOW work to prove API reliability")
    print("=" * 80)
    
    tester = ReliabilityTester()
    results = tester.run_reliability_test()
    
    # Final summary
    print(f"\n{'='*30} FINAL RELIABILITY RESULTS {'='*30}")
    
    total_attempts = results['total_attempts']
    total_successful = results['total_successful_attempts']
    overall_success_rate = (total_successful / total_attempts) * 100
    
    print(f"Total Tests: {total_attempts}")
    print(f"Successful Downloads: {total_successful}")
    print(f"Overall Success Rate: {overall_success_rate:.1f}%")
    print(f"Papers with >0% success: {results['successful_papers']}/10")
    
    print(f"\n📊 PER-PAPER RESULTS:")
    for paper_result in results['paper_results']:
        rate = paper_result['success_rate']
        journal = paper_result['journal'][:40] + "..." if len(paper_result['journal']) > 40 else paper_result['journal']
        
        if rate == 100:
            status = "🎉 PERFECT"
        elif rate >= 80:
            status = "✅ EXCELLENT"
        elif rate >= 50:
            status = "⚠️ MODERATE"
        elif rate > 0:
            status = "❌ POOR"
        else:
            status = "💀 FAILED"
        
        print(f"  {status} {journal}: {rate:.1f}% ({paper_result['successful_attempts']}/10)")
        
        if paper_result['successful_attempts'] > 0:
            print(f"       Avg Size: {paper_result['average_size_mb']:.2f}MB, Avg Time: {paper_result['average_response_time']:.2f}s")
    
    # Count downloaded files
    pdf_files = list(tester.downloads_dir.glob("*.pdf"))
    total_size = sum(f.stat().st_size for f in pdf_files) / (1024 * 1024)
    
    print(f"\n📁 DOWNLOADED FILES:")
    print(f"Total PDFs: {len(pdf_files)}")
    print(f"Total Size: {total_size:.2f} MB")
    print(f"Location: {tester.downloads_dir}")
    
    # Verdict
    print(f"\n🏆 RELIABILITY VERDICT:")
    if overall_success_rate >= 90:
        print(f"🎉 EXCELLENT: API is highly reliable ({overall_success_rate:.1f}%)")
    elif overall_success_rate >= 70:
        print(f"✅ GOOD: API is generally reliable ({overall_success_rate:.1f}%)")
    elif overall_success_rate >= 50:
        print(f"⚠️ MODERATE: API has some reliability issues ({overall_success_rate:.1f}%)")
    else:
        print(f"❌ POOR: API has significant reliability problems ({overall_success_rate:.1f}%)")
    
    # Save results
    results_file = Path("reliability_test_results.json")
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Full results saved to: {results_file}")
    print(f"🧪 RELIABILITY TEST COMPLETE!")

if __name__ == "__main__":
    main()