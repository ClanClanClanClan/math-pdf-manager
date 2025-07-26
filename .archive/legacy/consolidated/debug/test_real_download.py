#!/usr/bin/env python3
"""
Real Download Test for ETH Authentication
=========================================

Tests actual paper downloads through ETH institutional access.
Uses real DOIs and handles authentication flows properly.
"""

import os
import tempfile
import logging
import time
from pathlib import Path

from scripts.downloader import InstitutionalStrategy, DownloadAttempt, DownloadResult
from auth_manager import get_auth_manager
from paper_validator import validate_paper

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("real_download_test")

# Real DOIs that should be accessible through institutional access
REAL_TEST_DOIS = {
    "ieee": [
        "10.1109/JPROC.2018.2820126",  # Deep Learning IEEE Proceedings
        "10.1109/ACCESS.2020.2964261",  # Open Access IEEE paper
        "10.1109/TPAMI.2017.2699184"   # Pattern Analysis IEEE
    ],
    
    "springer": [
        "10.1007/s10994-006-6226-1",   # Machine Learning journal
        "10.1007/s11263-017-1018-5",  # Computer Vision
        "10.1007/s00454-017-9904-4"   # Computational Geometry
    ],
    
    "elsevier": [
        "10.1016/j.neunet.2015.02.042",  # Neural Networks
        "10.1016/j.artint.2019.103172",  # Artificial Intelligence
        "10.1016/j.patcog.2017.10.013"   # Pattern Recognition
    ],
    
    "acm": [
        "10.1145/3065386",             # Attention Is All You Need
        "10.1145/2939672.2939785",     # ResNet paper
        "10.1145/3097983.3098115"      # Transformer architecture
    ],
    
    "wiley": [
        "10.1002/widm.1245",           # Data Mining review
        "10.1002/spe.2490",           # Software practice
        "10.1002/asi.23011"           # Information Science
    ],
    
    # Mathematical and scientific publishers
    "siam": [
        "10.1137/S0036144502417715",   # SIAM Review
        "10.1137/120880574",          # SIAM Journal on Numerical Analysis
        "10.1137/17M1119846"          # SIAM Journal on Applied Mathematics
    ],
    
    "project_euclid": [
        "10.1214/17-AOS1659",         # Annals of Statistics
        "10.1214/18-AAP1456",         # Annals of Applied Probability
        "10.1214/aos/1176347963"      # Classical AOS paper
    ],
    
    "jstor": [
        "10.2307/2308946",            # Classical mathematics paper
        "10.2307/3072368",            # Statistical analysis
        "10.2307/2334029"             # Probability theory
    ],
    
    "nature": [
        "10.1038/nature24270",        # Machine learning nature
        "10.1038/s41586-019-1666-5",  # Quantum computing
        "10.1038/s41586-021-03819-2"  # AI breakthrough
    ],
    
    "science": [
        "10.1126/science.aau6249",    # AI Science paper
        "10.1126/science.abf4063",    # Quantum science
        "10.1126/science.1251387"     # Mathematical methods
    ],
    
    "taylor_francis": [
        "10.1080/01621459.2017.1285776",  # Journal of American Statistical Association
        "10.1080/00401706.2018.1524791",  # Technometrics
        "10.1080/02331934.2019.1578397"   # Optimization methods
    ],
    
    "cambridge": [
        "10.1017/S0963548318000342",   # Combinatorics, Probability and Computing
        "10.1017/S0305004119000355",   # Mathematical Proceedings
        "10.1017/S144678871800023X"    # Journal of Applied Probability
    ],
    
    "oxford": [
        "10.1093/biomet/asw073",       # Biometrika
        "10.1093/imamat/hxx043",       # IMA Journal of Applied Mathematics
        "10.1093/imanum/drx059"        # IMA Journal of Numerical Analysis
    ],
    
    "ams": [
        "10.1090/S0002-9947-2018-07425-9",  # Transactions of AMS
        "10.1090/S0002-9939-2019-14678-8",  # Proceedings of AMS
        "10.1090/bull/1658"                 # Bulletin of AMS
    ],
    
    "ims": [
        "10.1214/19-AOS1897",         # Annals of Statistics (via Project Euclid)
        "10.1214/20-AOP1456",         # Annals of Probability
        "10.1214/aos/1013203451"      # Historical AOS paper
    ]
}

def test_single_download(publisher: str, doi: str, timeout: int = 30):
    """Test downloading a single paper with timeout."""
    logger.info(f"  📄 Testing DOI: {doi}")
    
    service_name = f"eth_{publisher}"
    
    # Create test metadata
    test_metadata = {
        'title': f'Test Paper {doi}',
        'DOI': doi,
        'source': 'test',
        'is_open_access': False,  # Force institutional access
        'best_oa_location': None,
        'oa_locations': []
    }
    
    start_time = time.time()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            # Create institutional strategy
            strategy = InstitutionalStrategy(auth_service=service_name)
            
            # Test download
            logger.info(f"    🔄 Attempting download...")
            attempt = strategy.download(test_metadata, tmpdir)
            
            elapsed = time.time() - start_time
            
            if attempt.result == DownloadResult.SUCCESS and attempt.file_path:
                file_size = os.path.getsize(attempt.file_path)
                logger.info(f"    ✅ Success: {file_size} bytes in {elapsed:.1f}s")
                
                # Validate the file
                validation = validate_paper(attempt.file_path)
                logger.info(f"    📊 Validation: {validation.status.value}")
                
                if validation.quality_score:
                    logger.info(f"    🏆 Quality: {validation.quality_score:.2f}")
                
                return True, {
                    'file_size': file_size,
                    'elapsed': elapsed,
                    'validation': validation.status.value,
                    'quality': validation.quality_score
                }
            
            elif attempt.result == DownloadResult.BLOCKED:
                logger.warning(f"    🚫 Blocked: {attempt.error_message}")
                return False, {'error': 'blocked', 'message': attempt.error_message}
            
            elif attempt.result == DownloadResult.NOT_FOUND:
                logger.warning(f"    🔍 Not found: {attempt.error_message}")
                return False, {'error': 'not_found', 'message': attempt.error_message}
            
            else:
                logger.error(f"    ❌ Failed: {attempt.result.value} - {attempt.error_message}")
                return False, {'error': attempt.result.value, 'message': attempt.error_message}
                
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"    💥 Exception: {e}")
            return False, {'error': 'exception', 'message': str(e), 'elapsed': elapsed}

def test_publisher_downloads(publisher: str, max_tests: int = 2):
    """Test downloads for a specific publisher."""
    logger.info(f"\n🏛️  Testing {publisher.upper()} Downloads")
    logger.info("=" * 50)
    
    if publisher not in REAL_TEST_DOIS:
        logger.error(f"  ❌ No test DOIs configured for {publisher}")
        return False, []
    
    # Check auth config exists
    auth_manager = get_auth_manager()
    service_name = f"eth_{publisher}"
    
    if service_name not in auth_manager.configs:
        logger.error(f"  ❌ No auth config for {service_name}")
        return False, []
    
    # Test downloads
    dois = REAL_TEST_DOIS[publisher][:max_tests]  # Limit number of tests
    results = []
    
    for i, doi in enumerate(dois, 1):
        logger.info(f"  📝 Test {i}/{len(dois)}")
        success, details = test_single_download(publisher, doi)
        results.append({
            'doi': doi,
            'success': success,
            'details': details
        })
        
        # Small delay between requests to be polite
        if i < len(dois):
            time.sleep(2)
    
    # Summary for this publisher
    successful = sum(1 for r in results if r['success'])
    total = len(results)
    
    logger.info(f"\n  📊 {publisher.upper()} Summary: {successful}/{total} successful")
    
    return successful > 0, results

def run_comprehensive_download_test():
    """Test real downloads for all publishers."""
    logger.info("🧪 Real ETH Download Test Suite")
    logger.info("=" * 60)
    
    logger.info("⚠️  This test attempts real downloads through ETH authentication.")
    logger.info("⚠️  Results depend on ETH access and paper availability.")
    logger.info("⚠️  Some failures are expected due to access restrictions.\n")
    
    # Test each publisher
    all_results = {}
    successful_publishers = 0
    
    publishers = ['ieee', 'springer', 'elsevier', 'acm', 'wiley', 'siam', 'project_euclid', 'jstor', 'nature', 'science', 'taylor_francis', 'cambridge', 'oxford', 'ams', 'ims']
    
    for publisher in publishers:
        try:
            success, results = test_publisher_downloads(publisher, max_tests=2)
            all_results[publisher] = {
                'success': success,
                'results': results
            }
            
            if success:
                successful_publishers += 1
                
        except Exception as e:
            logger.error(f"💥 {publisher.upper()} test failed: {e}")
            all_results[publisher] = {
                'success': False,
                'error': str(e)
            }
    
    # Final summary
    logger.info(f"\n🏁 Final Results")
    logger.info("=" * 40)
    logger.info(f"Publishers with successful downloads: {successful_publishers}/{len(publishers)}")
    
    for publisher, data in all_results.items():
        if data['success']:
            successful_dois = sum(1 for r in data['results'] if r['success'])
            total_dois = len(data['results'])
            logger.info(f"  ✅ {publisher}: {successful_dois}/{total_dois} DOIs downloaded")
        elif 'error' in data:
            logger.info(f"  💥 {publisher}: Test error - {data['error']}")
        else:
            failed_dois = len(data.get('results', []))
            logger.info(f"  ❌ {publisher}: 0/{failed_dois} DOIs downloaded")
    
    # Recommendations
    logger.info(f"\n💡 Analysis:")
    if successful_publishers == 0:
        logger.info("  🔧 No publishers working - check ETH credentials and network")
        logger.info("  🔧 Try: python simple_eth_test.py first")
    elif successful_publishers < len(publishers):
        logger.info("  ⚠️  Some publishers not working - this is normal")
        logger.info("  ⚠️  Papers may not be available through institutional access")
        logger.info("  ⚠️  Some publishers may require additional authentication steps")
    else:
        logger.info("  🎉 All publishers working! ETH authentication is fully functional")
    
    return successful_publishers, all_results

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Test specific publisher
        publisher = sys.argv[1].lower()
        if publisher in REAL_TEST_DOIS:
            success, results = test_publisher_downloads(publisher)
            sys.exit(0 if success else 1)
        else:
            logger.error(f"Unknown publisher: {publisher}")
            logger.error(f"Available: {', '.join(REAL_TEST_DOIS.keys())}")
            sys.exit(1)
    else:
        # Test all publishers
        successful_count, results = run_comprehensive_download_test()
        
        if successful_count > 0:
            logger.info("\n✅ ETH authentication is working for at least some publishers!")
        else:
            logger.error("\n❌ No publishers working - check setup")
        
        sys.exit(0 if successful_count > 0 else 1)