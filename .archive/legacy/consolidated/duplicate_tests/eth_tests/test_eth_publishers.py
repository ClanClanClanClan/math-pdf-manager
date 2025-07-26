#!/usr/bin/env python3
"""
Comprehensive ETH Publisher Authentication Testing
=================================================

Thoroughly tests ETH institutional access for each configured publisher.
"""

import os
import sys
import json
import logging
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from auth_manager import get_auth_manager
from secure_credential_manager import get_credential_manager
from scripts.downloader import acquire_paper_by_metadata, AcquisitionEngine
from paper_validator import validate_paper, ValidationStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)
logger = logging.getLogger("eth_publisher_test")

@dataclass
class TestPaper:
    """Test paper configuration for each publisher."""
    title: str
    doi: str
    expected_open_access: bool = False
    backup_title: Optional[str] = None
    backup_doi: Optional[str] = None

@dataclass
class PublisherTestResult:
    """Results from testing a publisher."""
    publisher: str
    auth_config_exists: bool = False
    session_created: bool = False
    download_attempted: bool = False
    download_successful: bool = False
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    validation_status: Optional[str] = None
    error_messages: List[str] = None
    strategy_used: Optional[str] = None
    response_time: Optional[float] = None
    
    def __post_init__(self):
        if self.error_messages is None:
            self.error_messages = []

# Test papers for each publisher
TEST_PAPERS = {
    "ieee": TestPaper(
        title="Deep Learning for Wireless Communications",
        doi="10.1109/ACCESS.2023.3240147",
        backup_title="Machine Learning in Signal Processing",
        backup_doi="10.1109/TSP.2023.1234567"
    ),
    
    "acm": TestPaper(
        title="Attention Is All You Need",
        doi="10.1145/3295750.3298922",
        backup_title="Graph Neural Networks Survey",
        backup_doi="10.1145/3397271.3401234"
    ),
    
    "springer": TestPaper(
        title="Machine Learning: A Probabilistic Perspective",
        doi="10.1007/s10994-023-06123-4",
        backup_title="Neural Network Architectures",
        backup_doi="10.1007/s11263-023-01234-5"
    ),
    
    "elsevier": TestPaper(
        title="Deep Learning for Computer Vision",
        doi="10.1016/j.neunet.2023.01.012",
        backup_title="Convolutional Neural Networks",
        backup_doi="10.1016/j.patcog.2023.02.045"
    ),
    
    "wiley": TestPaper(
        title="Statistical Learning Theory",
        doi="10.1002/widm.1234",
        backup_title="Bayesian Machine Learning",
        backup_doi="10.1002/stat.5678"
    )
}


class ETHPublisherTester:
    """Comprehensive tester for ETH publisher authentication."""
    
    def __init__(self):
        self.auth_manager = get_auth_manager()
        self.credential_manager = get_credential_manager()
        self.results: Dict[str, PublisherTestResult] = {}
        self.test_dir = None
        
        # Verify ETH credentials are available
        if not self.credential_manager.has_eth_credentials():
            raise ValueError("ETH credentials not found. Please set up credentials first.")
        
        # Create temporary test directory
        self.test_dir = tempfile.mkdtemp(prefix="eth_publisher_test_")
        logger.info(f"🗂️  Test downloads will be saved to: {self.test_dir}")
    
    def test_auth_config(self, publisher: str) -> Tuple[bool, List[str]]:
        """Test if authentication configuration exists and is valid."""
        errors = []
        service_name = f"eth_{publisher}"
        
        if service_name not in self.auth_manager.configs:
            errors.append(f"No auth config found for {service_name}")
            return False, errors
        
        config = self.auth_manager.configs[service_name]
        
        # Validate config
        if not config.username:
            errors.append("No username in config")
        
        if not config.base_url and not config.shibboleth_idp:
            errors.append("No base_url or shibboleth_idp in config")
        
        if config.auth_method.value != "shibboleth":
            errors.append(f"Expected shibboleth auth, got {config.auth_method.value}")
        
        return len(errors) == 0, errors
    
    def test_session_creation(self, publisher: str) -> Tuple[bool, List[str]]:
        """Test if authenticated session can be created."""
        errors = []
        service_name = f"eth_{publisher}"
        
        try:
            session = self.auth_manager.get_authenticated_session(service_name)
            if session is None:
                errors.append("Failed to create authenticated session")
                return False, errors
            
            # Test basic session properties
            if not hasattr(session, 'headers'):
                errors.append("Session missing headers attribute")
            
            if not hasattr(session, 'cookies'):
                errors.append("Session missing cookies attribute")
            
            return True, errors
            
        except Exception as e:
            errors.append(f"Session creation error: {e}")
            return False, errors
    
    def test_paper_download(self, publisher: str, test_paper: TestPaper, use_backup: bool = False) -> Tuple[bool, Dict]:
        """Test downloading a paper through the publisher."""
        service_name = f"eth_{publisher}"
        
        # Choose paper to test
        if use_backup and test_paper.backup_title and test_paper.backup_doi:
            title = test_paper.backup_title
            doi = test_paper.backup_doi
            logger.info(f"  📄 Using backup paper: {title}")
        else:
            title = test_paper.title
            doi = test_paper.doi
            logger.info(f"  📄 Testing paper: {title}")
        
        start_time = time.time()
        
        try:
            # Create acquisition engine directly to bypass metadata fetcher issues
            from scripts.downloader import AcquisitionEngine
            
            # Mock metadata for testing
            test_metadata = {
                'title': title,
                'DOI': doi,
                'source': 'test',
                'is_open_access': False,  # Force institutional access
                'best_oa_location': None,
                'oa_locations': []
            }
            
            # Create engine with auth service
            engine = AcquisitionEngine(auth_service=service_name)
            attempts = engine.acquire_paper(test_metadata, self.test_dir)
            
            # Find successful attempt
            successful_attempt = engine.get_successful_download(attempts)
            file_path = successful_attempt.file_path if successful_attempt else None
            
            response_time = time.time() - start_time
            
            result_data = {
                'file_path': file_path,
                'attempts': len(attempts),
                'response_time': response_time,
                'strategies_used': [attempt.strategy for attempt in attempts],
                'attempt_details': []
            }
            
            # Analyze attempts
            for attempt in attempts:
                attempt_detail = {
                    'strategy': attempt.strategy,
                    'result': attempt.result.value,
                    'url': attempt.url,
                    'error': attempt.error_message,
                    'file_size': attempt.response_size
                }
                result_data['attempt_details'].append(attempt_detail)
            
            # Check if download was successful
            if file_path and os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                result_data['file_size'] = file_size
                
                # Validate the downloaded file
                validation_result = validate_paper(file_path)
                result_data['validation_status'] = validation_result.status.value
                result_data['validation_issues'] = validation_result.issues
                result_data['quality_score'] = validation_result.quality_score
                
                logger.info(f"  ✅ Download successful: {file_size} bytes")
                logger.info(f"  📊 Validation: {validation_result.status.value}")
                
                return True, result_data
            else:
                logger.warning(f"  ❌ Download failed")
                return False, result_data
                
        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"  💥 Download error: {e}")
            
            return False, {
                'error': str(e),
                'response_time': response_time,
                'attempts': 0
            }
    
    def test_publisher(self, publisher: str) -> PublisherTestResult:
        """Comprehensive test of a single publisher."""
        logger.info(f"\n🏛️  Testing {publisher.upper()}")
        logger.info("=" * 50)
        
        result = PublisherTestResult(publisher=publisher)
        
        # Test 1: Check auth config
        logger.info("1️⃣  Checking authentication configuration...")
        config_valid, config_errors = self.test_auth_config(publisher)
        result.auth_config_exists = config_valid
        if not config_valid:
            result.error_messages.extend(config_errors)
            logger.error(f"  ❌ Config errors: {', '.join(config_errors)}")
            return result
        else:
            logger.info("  ✅ Authentication config valid")
        
        # Test 2: Create authenticated session
        logger.info("2️⃣  Creating authenticated session...")
        session_created, session_errors = self.test_session_creation(publisher)
        result.session_created = session_created
        if not session_created:
            result.error_messages.extend(session_errors)
            logger.error(f"  ❌ Session errors: {', '.join(session_errors)}")
            return result
        else:
            logger.info("  ✅ Authenticated session created")
        
        # Test 3: Download test paper
        logger.info("3️⃣  Testing paper download...")
        test_paper = TEST_PAPERS[publisher]
        
        # Try primary paper first
        download_success, download_data = self.test_paper_download(publisher, test_paper)
        result.download_attempted = True
        
        # If primary fails, try backup
        if not download_success and test_paper.backup_title:
            logger.info("  🔄 Primary paper failed, trying backup...")
            download_success, download_data = self.test_paper_download(publisher, test_paper, use_backup=True)
        
        # Store results
        result.download_successful = download_success
        result.file_path = download_data.get('file_path')
        result.file_size = download_data.get('file_size')
        result.validation_status = download_data.get('validation_status')
        result.response_time = download_data.get('response_time')
        
        if 'attempt_details' in download_data and download_data['attempt_details']:
            successful_attempt = next(
                (att for att in download_data['attempt_details'] if att['result'] == 'success'), 
                download_data['attempt_details'][0]
            )
            result.strategy_used = successful_attempt['strategy']
        
        if 'error' in download_data:
            result.error_messages.append(download_data['error'])
        
        # Summary
        if download_success:
            logger.info(f"  🎉 {publisher.upper()} test PASSED")
        else:
            logger.error(f"  💥 {publisher.upper()} test FAILED")
            if download_data.get('attempt_details'):
                for attempt in download_data['attempt_details']:
                    logger.error(f"    - {attempt['strategy']}: {attempt['result']} ({attempt.get('error', 'No error')})")
        
        return result
    
    def run_all_tests(self) -> Dict[str, PublisherTestResult]:
        """Run comprehensive tests for all publishers."""
        logger.info("🧪 ETH Publisher Authentication Testing")
        logger.info("=" * 60)
        
        # Check prerequisites
        logger.info("🔍 Checking prerequisites...")
        username, password = self.credential_manager.get_eth_credentials()
        logger.info(f"  ETH Username: {username}")
        logger.info(f"  ETH Password: {'***' if password else 'NOT SET'}")
        
        # Get configured publishers
        eth_publishers = [
            name.replace('eth_', '') 
            for name in self.auth_manager.configs.keys() 
            if name.startswith('eth_')
        ]
        
        logger.info(f"  Configured publishers: {', '.join(eth_publishers)}")
        
        if not eth_publishers:
            logger.error("❌ No ETH publishers configured!")
            return {}
        
        # Test each publisher
        for publisher in eth_publishers:
            if publisher in TEST_PAPERS:
                result = self.test_publisher(publisher)
                self.results[publisher] = result
            else:
                logger.warning(f"⚠️  No test paper configured for {publisher}")
        
        return self.results
    
    def generate_report(self) -> str:
        """Generate a comprehensive test report."""
        if not self.results:
            return "No test results available."
        
        # Calculate summary stats
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results.values() if r.download_successful)
        config_issues = sum(1 for r in self.results.values() if not r.auth_config_exists)
        session_issues = sum(1 for r in self.results.values() if not r.session_created)
        
        report = f"""
# ETH Publisher Authentication Test Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📊 Summary
- **Total Publishers Tested**: {total_tests}
- **Successful Downloads**: {passed_tests}/{total_tests} ({passed_tests/total_tests*100:.1f}%)
- **Configuration Issues**: {config_issues}
- **Session Creation Issues**: {session_issues}

## 📋 Detailed Results

"""
        
        for publisher, result in self.results.items():
            status_emoji = "✅" if result.download_successful else "❌"
            
            report += f"""
### {status_emoji} {publisher.upper()}

| Metric | Value |
|--------|-------|
| Auth Config | {'✅ Valid' if result.auth_config_exists else '❌ Invalid'} |
| Session Creation | {'✅ Success' if result.session_created else '❌ Failed'} |
| Download Attempted | {'✅ Yes' if result.download_attempted else '❌ No'} |
| Download Successful | {'✅ Yes' if result.download_successful else '❌ No'} |
| File Size | {f'{result.file_size} bytes' if result.file_size else 'N/A'} |
| Validation Status | {result.validation_status or 'N/A'} |
| Strategy Used | {result.strategy_used or 'N/A'} |
| Response Time | {f'{result.response_time:.2f}s' if result.response_time else 'N/A'} |

"""
            
            if result.error_messages:
                report += "**Errors:**\n"
                for error in result.error_messages:
                    report += f"- {error}\n"
                report += "\n"
        
        report += f"""
## 🗂️ Test Files
Downloaded files are stored in: `{self.test_dir}`

## 🔧 Troubleshooting

### Common Issues:
1. **Session Creation Failed**: Check ETH credentials and network connectivity
2. **Download Failed**: Paper may not be available through institutional access
3. **Validation Failed**: Downloaded file may be corrupted or not a valid PDF

### Next Steps:
- For failed publishers, check the specific error messages above
- Verify ETH credentials: `python secure_credential_manager.py list`
- Test individual downloads manually with specific DOIs
"""
        
        return report
    
    def save_detailed_results(self, output_file: str = None):
        """Save detailed test results to JSON file."""
        if output_file is None:
            output_file = f"eth_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Convert results to serializable format
        serializable_results = {}
        for publisher, result in self.results.items():
            serializable_results[publisher] = asdict(result)
        
        test_data = {
            'timestamp': datetime.now().isoformat(),
            'test_directory': self.test_dir,
            'eth_username': self.credential_manager.get_eth_credentials()[0],
            'results': serializable_results
        }
        
        with open(output_file, 'w') as f:
            json.dump(test_data, f, indent=2)
        
        logger.info(f"📄 Detailed results saved to: {output_file}")
        return output_file


def main():
    """Main test execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test ETH publisher authentication")
    parser.add_argument(
        "--publisher", 
        choices=['ieee', 'acm', 'springer', 'elsevier', 'wiley'],
        help="Test specific publisher only"
    )
    parser.add_argument(
        "--report", 
        action="store_true",
        help="Generate detailed report"
    )
    parser.add_argument(
        "--save-results", 
        action="store_true",
        help="Save detailed results to JSON"
    )
    
    args = parser.parse_args()
    
    try:
        tester = ETHPublisherTester()
        
        if args.publisher:
            # Test single publisher
            result = tester.test_publisher(args.publisher)
            tester.results[args.publisher] = result
        else:
            # Test all publishers
            tester.run_all_tests()
        
        # Generate report
        if args.report or not args.publisher:
            report = tester.generate_report()
            print("\n" + "="*60)
            print(report)
        
        # Save detailed results
        if args.save_results:
            tester.save_detailed_results()
        
        # Summary
        passed = sum(1 for r in tester.results.values() if r.download_successful)
        total = len(tester.results)
        
        print(f"\n🏁 Test Complete: {passed}/{total} publishers working")
        
        if passed == total:
            sys.exit(0)  # All tests passed
        else:
            sys.exit(1)  # Some tests failed
            
    except Exception as e:
        logger.error(f"💥 Test execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()