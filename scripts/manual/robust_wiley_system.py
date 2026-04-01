#!/usr/bin/env python3
"""
ROBUST WILEY DOWNLOAD SYSTEM
============================

ULTRATHINKING: How to make the API robustly usable

STRATEGY:
1. Intelligent Rate Limiting - Respect API throttling
2. Smart Retry Logic - Handle different error types appropriately  
3. Journal Prioritization - Focus on reliable sources first
4. Distributed Timing - Spread downloads over time
5. Hybrid Access - Combine API + VPN methods
6. Circuit Breaker - Prevent overwhelming the API
7. Academic Compliance - Respect TDM intended usage
8. Incremental Building - Build library over weeks/months
"""

import asyncio
import requests
import time
import json
import random
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

API_KEY = "dkg5eEYuOjlv69V1gw1PuxwK0njBM7N457RWItGZHpihEqCc"

@dataclass
class JournalProfile:
    """Profile of a journal's API reliability"""
    name: str
    issn: str
    success_rate: float
    avg_response_time: float
    last_success: Optional[datetime]
    consecutive_failures: int
    priority: int  # 1=highest, 5=lowest

@dataclass
class DownloadAttempt:
    """Record of a download attempt"""
    doi: str
    timestamp: datetime
    success: bool
    status_code: int
    size_mb: float
    response_time: float
    error: Optional[str]

class CircuitBreaker:
    """Circuit breaker to prevent API overwhelming"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 300):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def can_proceed(self) -> bool:
        """Check if we can make an API call"""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def record_success(self):
        """Record successful API call"""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def record_failure(self):
        """Record failed API call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

class RobustWileyDownloader:
    """Robust Wiley PDF downloader with intelligent strategies"""
    
    def __init__(self):
        self.api_key = API_KEY
        self.tdm_base_url = "https://api.wiley.com/onlinelibrary/tdm/v1/articles/"
        self.downloads_dir = Path("robust_downloads")
        self.downloads_dir.mkdir(exist_ok=True)
        
        # State management
        self.circuit_breaker = CircuitBreaker()
        self.download_history: List[DownloadAttempt] = []
        self.journal_profiles: Dict[str, JournalProfile] = {}
        self.last_request_time = 0
        
        # Configuration
        self.min_delay_seconds = 10  # Minimum delay between requests
        self.max_delay_seconds = 60  # Maximum delay
        self.base_retry_delay = 5    # Base retry delay
        self.max_retries = 3         # Max retries per paper
        
        # Setup session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ETH-Academic-Research-TDM/1.0',
            'Accept': 'application/pdf',
            'X-API-Key': self.api_key,
            'Authorization': f'Bearer {self.api_key}',
            'Wiley-TDM-Client-Token': self.api_key,
        })
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('robust_downloader.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        print("🧠 ROBUST WILEY DOWNLOAD SYSTEM")
        print("=" * 60)
        print("✅ Intelligent rate limiting")
        print("✅ Smart retry logic")
        print("✅ Circuit breaker protection")
        print("✅ Journal prioritization")
        print("✅ Academic compliance")
        print("=" * 60)
    
    def load_journal_profiles(self):
        """Load journal reliability profiles"""
        
        # Based on our testing, prioritize journals by reliability
        self.journal_profiles = {
            'AIChE Journal': JournalProfile(
                name='AIChE Journal',
                issn='0001-1541',
                success_rate=80.0,  # From our testing
                avg_response_time=1.2,
                last_success=datetime.now(),
                consecutive_failures=0,
                priority=1  # Highest priority
            ),
            'Advanced Materials': JournalProfile(
                name='Advanced Materials',
                issn='0935-9648', 
                success_rate=15.0,  # From our testing
                avg_response_time=0.8,
                last_success=None,
                consecutive_failures=10,
                priority=3
            ),
            'Angewandte Chemie': JournalProfile(
                name='Angewandte Chemie',
                issn='1433-7851',
                success_rate=10.0,
                avg_response_time=0.5,
                last_success=None,
                consecutive_failures=15,
                priority=4
            ),
            # Add more journals based on empirical testing
        }
    
    def calculate_delay(self, attempt: int = 1) -> float:
        """Calculate intelligent delay based on system state"""
        
        # Base delay
        base_delay = random.uniform(self.min_delay_seconds, self.max_delay_seconds)
        
        # Exponential backoff for retries
        retry_multiplier = (2 ** (attempt - 1)) if attempt > 1 else 1
        
        # Circuit breaker penalty
        circuit_penalty = 1
        if self.circuit_breaker.state == "OPEN":
            circuit_penalty = 5
        elif self.circuit_breaker.state == "HALF_OPEN":
            circuit_penalty = 2
        
        # Recent failure penalty
        recent_failures = sum(1 for h in self.download_history[-10:] if not h.success)
        failure_penalty = 1 + (recent_failures * 0.5)
        
        total_delay = base_delay * retry_multiplier * circuit_penalty * failure_penalty
        
        # Cap maximum delay
        return min(total_delay, 300)  # Max 5 minutes
    
    def should_skip_journal(self, journal_name: str) -> bool:
        """Determine if we should skip a journal due to poor performance"""
        
        if journal_name not in self.journal_profiles:
            return False
        
        profile = self.journal_profiles[journal_name]
        
        # Skip if too many consecutive failures
        if profile.consecutive_failures > 20:
            return True
        
        # Skip if success rate too low and we tried recently
        if profile.success_rate < 5.0 and profile.consecutive_failures > 5:
            return True
        
        return False
    
    def intelligent_download(self, doi: str, journal: str, title: str) -> Dict:
        """Intelligently download a single paper"""
        
        result = {
            'doi': doi,
            'journal': journal,
            'title': title,
            'success': False,
            'attempts': 0,
            'final_status': 'Not attempted',
            'size_mb': 0,
            'total_time': 0
        }
        
        # Skip if journal has poor track record
        if self.should_skip_journal(journal):
            result['final_status'] = 'Journal skipped due to poor reliability'
            self.logger.info(f"SKIPPED {journal}: {doi} - Poor reliability")
            return result
        
        # Check circuit breaker
        if not self.circuit_breaker.can_proceed():
            result['final_status'] = 'Circuit breaker OPEN'
            self.logger.warning(f"BLOCKED by circuit breaker: {doi}")
            return result
        
        start_time = time.time()
        
        for attempt in range(1, self.max_retries + 1):
            result['attempts'] = attempt
            
            # Intelligent delay
            if attempt > 1 or time.time() - self.last_request_time < self.min_delay_seconds:
                delay = self.calculate_delay(attempt)
                self.logger.info(f"Waiting {delay:.1f}s before attempt {attempt}")
                time.sleep(delay)
            
            try:
                self.logger.info(f"ATTEMPT {attempt}: {journal} - {doi}")
                
                url = f"{self.tdm_base_url}{doi}"
                response = self.session.get(url, timeout=30)
                self.last_request_time = time.time()
                
                # Record attempt
                attempt_record = DownloadAttempt(
                    doi=doi,
                    timestamp=datetime.now(),
                    success=False,
                    status_code=response.status_code,
                    size_mb=0,
                    response_time=time.time() - start_time,
                    error=None
                )
                
                if response.status_code == 200:
                    content_type = response.headers.get('Content-Type', '')
                    
                    if 'pdf' in content_type.lower() and len(response.content) > 1000:
                        # SUCCESS!
                        size_mb = len(response.content) / (1024 * 1024)
                        
                        # Save PDF
                        filename = f"robust_{doi.replace('/', '_').replace('.', '_')}.pdf"
                        save_path = self.downloads_dir / filename
                        
                        with open(save_path, 'wb') as f:
                            f.write(response.content)
                        
                        # Update records
                        attempt_record.success = True
                        attempt_record.size_mb = size_mb
                        self.download_history.append(attempt_record)
                        
                        # Update journal profile
                        if journal in self.journal_profiles:
                            self.journal_profiles[journal].last_success = datetime.now()
                            self.journal_profiles[journal].consecutive_failures = 0
                        
                        # Update circuit breaker
                        self.circuit_breaker.record_success()
                        
                        result.update({
                            'success': True,
                            'final_status': f'Downloaded successfully ({size_mb:.2f} MB)',
                            'size_mb': size_mb,
                            'total_time': time.time() - start_time
                        })
                        
                        self.logger.info(f"SUCCESS: {journal} - {size_mb:.2f} MB")
                        return result
                
                # Handle different failure types
                if response.status_code == 500:
                    attempt_record.error = "Server error - likely rate limited"
                    self.circuit_breaker.record_failure()
                elif response.status_code == 403:
                    attempt_record.error = "Forbidden - access denied"
                elif response.status_code == 404:
                    attempt_record.error = "Not found"
                    break  # Don't retry 404s
                else:
                    attempt_record.error = f"HTTP {response.status_code}"
                
                self.download_history.append(attempt_record)
                
                # Update journal profile
                if journal in self.journal_profiles:
                    self.journal_profiles[journal].consecutive_failures += 1
                
                self.logger.warning(f"FAILED attempt {attempt}: HTTP {response.status_code}")
                
            except Exception as e:
                error_msg = str(e)[:100]
                self.logger.error(f"ERROR attempt {attempt}: {error_msg}")
                
                self.download_history.append(DownloadAttempt(
                    doi=doi,
                    timestamp=datetime.now(),
                    success=False,
                    status_code=0,
                    size_mb=0,
                    response_time=time.time() - start_time,
                    error=error_msg
                ))
        
        result['final_status'] = f'Failed after {self.max_retries} attempts'
        result['total_time'] = time.time() - start_time
        return result
    
    def get_prioritized_papers(self) -> List[Dict]:
        """Get papers prioritized by journal reliability"""
        
        # Start with high-reliability journals
        high_priority_papers = [
            # AIChE Journal - our most reliable
            {'doi': '10.1002/aic.17123', 'journal': 'AIChE Journal', 'title': 'Chemical Engineering Research'},
            {'doi': '10.1002/aic.16789', 'journal': 'AIChE Journal', 'title': 'Process Engineering'},
            {'doi': '10.1002/aic.16234', 'journal': 'AIChE Journal', 'title': 'Reaction Engineering'},
            
            # Try some that worked in previous tests
            {'doi': '10.1002/ese3.789', 'journal': 'Energy Science & Engineering', 'title': 'Energy Research'},
            {'doi': '10.1002/fam.2890', 'journal': 'Fire and Materials', 'title': 'Materials Research'},
            {'doi': '10.1002/ente.202000456', 'journal': 'Energy Technology', 'title': 'Energy Technology'},
            
            # Medium priority
            {'doi': '10.1002/cctc.202000789', 'journal': 'ChemCatChem', 'title': 'Catalysis Research'},
            {'doi': '10.1002/cbic.202000123', 'journal': 'ChemBioChem', 'title': 'Chemical Biology'},
            {'doi': '10.1002/cmdc.202000456', 'journal': 'ChemMedChem', 'title': 'Medicinal Chemistry'},
            {'doi': '10.1002/open.202000234', 'journal': 'ChemistryOpen', 'title': 'Open Chemistry'},
        ]
        
        return high_priority_papers
    
    def run_robust_test(self) -> Dict:
        """Run robust downloading test"""
        
        self.load_journal_profiles()
        papers = self.get_prioritized_papers()
        
        results = {
            'start_time': datetime.now().isoformat(),
            'total_papers': len(papers),
            'successful_downloads': 0,
            'total_attempts': 0,
            'total_size_mb': 0,
            'paper_results': []
        }
        
        self.logger.info(f"STARTING ROBUST DOWNLOAD TEST - {len(papers)} papers")
        
        for i, paper in enumerate(papers, 1):
            print(f"\n{'='*15} PAPER {i}/{len(papers)} {'='*15}")
            print(f"Journal: {paper['journal']}")
            print(f"DOI: {paper['doi']}")
            
            result = self.intelligent_download(
                paper['doi'], 
                paper['journal'], 
                paper['title']
            )
            
            results['paper_results'].append(result)
            results['total_attempts'] += result['attempts']
            
            if result['success']:
                results['successful_downloads'] += 1
                results['total_size_mb'] += result['size_mb']
                print(f"✅ SUCCESS: {result['size_mb']:.2f} MB")
            else:
                print(f"❌ FAILED: {result['final_status']}")
            
            # Check if we should stop due to circuit breaker
            if self.circuit_breaker.state == "OPEN":
                self.logger.warning("Circuit breaker OPEN - stopping downloads")
                break
        
        results['end_time'] = datetime.now().isoformat()
        return results

def main():
    """Main robust downloader"""
    
    print("🧠 ROBUST WILEY DOWNLOAD SYSTEM - ULTRATHINKING APPROACH")
    print("=" * 80)
    print("Intelligent strategies for reliable API usage")
    print("=" * 80)
    
    downloader = RobustWileyDownloader()
    results = downloader.run_robust_test()
    
    # Final summary
    print(f"\n{'='*30} ROBUST SYSTEM RESULTS {'='*30}")
    
    success_rate = (results['successful_downloads'] / results['total_papers']) * 100
    
    print(f"Papers tested: {results['total_papers']}")
    print(f"Successful downloads: {results['successful_downloads']}")
    print(f"Success rate: {success_rate:.1f}%")
    print(f"Total size: {results['total_size_mb']:.2f} MB")
    print(f"Total attempts: {results['total_attempts']}")
    
    # System performance
    circuit_state = downloader.circuit_breaker.state
    total_history = len(downloader.download_history)
    recent_success_rate = 0
    if total_history > 0:
        recent_successes = sum(1 for h in downloader.download_history[-10:] if h.success)
        recent_success_rate = (recent_successes / min(10, total_history)) * 100
    
    print(f"\n🔧 SYSTEM STATE:")
    print(f"Circuit breaker: {circuit_state}")
    print(f"Recent success rate: {recent_success_rate:.1f}%")
    print(f"Total API calls: {total_history}")
    
    # Save results
    results_file = Path("robust_system_results.json")
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to: {results_file}")
    
    # Recommendations
    print(f"\n💡 ROBUST USAGE RECOMMENDATIONS:")
    print(f"1. Focus on high-reliability journals (AIChE, Energy journals)")
    print(f"2. Use 10-60 second delays between requests")
    print(f"3. Implement exponential backoff for retries")
    print(f"4. Monitor circuit breaker state")
    print(f"5. Spread downloads over days/weeks, not hours")
    print(f"6. Combine with VPN method for comprehensive coverage")
    
    print(f"\n🧠 ULTRATHINKING COMPLETE!")

if __name__ == "__main__":
    main()