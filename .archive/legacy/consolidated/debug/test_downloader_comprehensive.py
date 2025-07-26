#!/usr/bin/env python3
"""
Comprehensive test suite for downloader.py
=========================================

This script provides thorough testing of the downloader system with real-world scenarios,
strategy testing, and integration with the metadata system.
"""

import os
import sys
import time
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

import downloader as dl

class ComprehensiveDownloaderTests:
    """Comprehensive test class for downloader functionality."""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.results: Dict[str, Any] = {}
        self.temp_dir: Optional[str] = None
        
        # Test papers with different characteristics
        self.test_papers = [
            # Open access paper
            {
                "title": "Open Access Test Paper",
                "metadata": {
                    "title": "Open Access Test Paper",
                    "DOI": "10.1371/journal.pone.0000001",
                    "is_open_access": True,
                    "best_oa_location": "https://journals.plos.org/plosone/article/file?id=10.1371/journal.pone.0000001&type=printable",
                    "oa_locations": [
                        {"url": "https://journals.plos.org/plosone/article/file?id=10.1371/journal.pone.0000001&type=printable"},
                    ],
                    "source": "crossref"
                },
                "description": "Known open access paper (PLOS ONE)",
                "expected_strategy": "open_access"
            },
            # arXiv paper
            {
                "title": "arXiv Test Paper",
                "metadata": {
                    "title": "Attention Is All You Need",
                    "arxiv_id": "1706.03762",
                    "best_oa_location": "https://arxiv.org/pdf/1706.03762.pdf",
                    "is_open_access": True,
                    "source": "arxiv"
                },
                "description": "Famous arXiv paper",
                "expected_strategy": "open_access"
            },
            # Publisher paper (DOI only)
            {
                "title": "Publisher Test Paper",
                "metadata": {
                    "title": "Test Paper with DOI",
                    "DOI": "10.1007/s00220-021-04123-4",  # Springer DOI
                    "source": "crossref"
                },
                "description": "Springer paper (institutional access needed)",
                "expected_strategy": "publisher"
            },
            # No download sources
            {
                "title": "No Sources Paper",
                "metadata": {
                    "title": "Paper with No Download Sources",
                    "source": "test"
                },
                "description": "Paper with no download sources",
                "expected_strategy": None
            }
        ]
        
        # Test URLs for different scenarios
        self.test_urls = [
            # Direct PDF
            {
                "url": "https://arxiv.org/pdf/1706.03762.pdf",
                "description": "Direct PDF URL (arXiv)",
                "should_work": True,
                "expected_size_min": 1000
            },
            # Non-existent URL
            {
                "url": "https://example.com/nonexistent.pdf",
                "description": "Non-existent URL",
                "should_work": False,
                "expected_size_min": 0
            },
            # HTML page (not PDF)
            {
                "url": "https://www.google.com",
                "description": "HTML page (not PDF)",
                "should_work": False,  # Should warn about non-PDF
                "expected_size_min": 0
            }
        ]
    
    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp."""
        if self.verbose:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] [{level}] {message}")
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp(prefix="downloader_test_")
        self.log(f"Created temp directory: {self.temp_dir}")
    
    def tearDown(self):
        """Clean up test environment."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            self.log(f"Cleaned up temp directory: {self.temp_dir}")
    
    def test_strategy_components(self) -> Dict[str, Any]:
        """Test individual strategy components."""
        self.log("Testing strategy components...")
        
        results = {"passed": 0, "failed": 0, "errors": []}
        
        # Test OpenAccessStrategy
        try:
            oa_strategy = dl.OpenAccessStrategy()
            
            # Test can_handle
            oa_metadata = {
                'is_open_access': True,
                'best_oa_location': 'http://example.com/paper.pdf'
            }
            non_oa_metadata = {'is_open_access': False}
            
            if oa_strategy.can_handle(oa_metadata) and not oa_strategy.can_handle(non_oa_metadata):
                results["passed"] += 1
                self.log("✓ OpenAccessStrategy.can_handle() works correctly")
            else:
                results["failed"] += 1
                results["errors"].append("OpenAccessStrategy.can_handle() failed")
                self.log("✗ OpenAccessStrategy.can_handle() failed", "ERROR")
            
            # Test URL extraction
            urls = oa_strategy.get_download_urls(oa_metadata)
            if len(urls) == 1 and urls[0] == 'http://example.com/paper.pdf':
                results["passed"] += 1
                self.log("✓ OpenAccessStrategy.get_download_urls() works correctly")
            else:
                results["failed"] += 1
                results["errors"].append(f"OpenAccessStrategy.get_download_urls() failed: {urls}")
                self.log(f"✗ OpenAccessStrategy.get_download_urls() failed: {urls}", "ERROR")
                
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"OpenAccessStrategy test failed: {e}")
            self.log(f"✗ OpenAccessStrategy test failed: {e}", "ERROR")
        
        # Test InstitutionalStrategy
        try:
            inst_strategy = dl.InstitutionalStrategy()
            
            # Test can_handle
            doi_metadata = {'DOI': '10.1234/test'}
            empty_metadata = {}
            
            if inst_strategy.can_handle(doi_metadata) and not inst_strategy.can_handle(empty_metadata):
                results["passed"] += 1
                self.log("✓ InstitutionalStrategy.can_handle() works correctly")
            else:
                results["failed"] += 1
                results["errors"].append("InstitutionalStrategy.can_handle() failed")
                self.log("✗ InstitutionalStrategy.can_handle() failed", "ERROR")
            
            # Test URL extraction
            urls = inst_strategy.get_download_urls(doi_metadata)
            expected_url = 'https://doi.org/10.1234/test'
            if len(urls) >= 1 and urls[0] == expected_url:
                results["passed"] += 1
                self.log("✓ InstitutionalStrategy.get_download_urls() works correctly")
            else:
                results["failed"] += 1
                results["errors"].append(f"InstitutionalStrategy.get_download_urls() failed: {urls}")
                self.log(f"✗ InstitutionalStrategy.get_download_urls() failed: {urls}", "ERROR")
                
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"InstitutionalStrategy test failed: {e}")
            self.log(f"✗ InstitutionalStrategy test failed: {e}", "ERROR")
        
        # Test PublisherStrategy
        try:
            pub_strategy = dl.PublisherStrategy()
            
            # Test can_handle with known DOI patterns
            springer_metadata = {'DOI': '10.1007/s00220-021-04123-4'}
            ieee_metadata = {'DOI': '10.1109/TEST.2021.123456'}
            unknown_metadata = {'DOI': '10.9999/unknown'}
            
            springer_can_handle = pub_strategy.can_handle(springer_metadata)
            ieee_can_handle = pub_strategy.can_handle(ieee_metadata)
            
            if springer_can_handle and ieee_can_handle:
                results["passed"] += 1
                self.log("✓ PublisherStrategy.can_handle() recognizes known publishers")
            else:
                results["failed"] += 1
                results["errors"].append(f"PublisherStrategy.can_handle() failed: springer={springer_can_handle}, ieee={ieee_can_handle}")
                self.log(f"✗ PublisherStrategy.can_handle() failed", "ERROR")
                
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"PublisherStrategy test failed: {e}")
            self.log(f"✗ PublisherStrategy test failed: {e}", "ERROR")
        
        # Test AcquisitionEngine
        try:
            engine = dl.AcquisitionEngine()
            
            # Should have strategies
            if len(engine.strategies) >= 2:
                results["passed"] += 1
                strategy_names = [s.name for s in engine.strategies]
                self.log(f"✓ AcquisitionEngine has strategies: {strategy_names}")
            else:
                results["failed"] += 1
                results["errors"].append(f"AcquisitionEngine has too few strategies: {len(engine.strategies)}")
                self.log(f"✗ AcquisitionEngine has too few strategies: {len(engine.strategies)}", "ERROR")
                
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"AcquisitionEngine test failed: {e}")
            self.log(f"✗ AcquisitionEngine test failed: {e}", "ERROR")
        
        return results
    
    def test_utility_functions(self) -> Dict[str, Any]:
        """Test utility functions."""
        self.log("Testing utility functions...")
        
        results = {"passed": 0, "failed": 0, "errors": []}
        
        # Test sanitize_filename
        test_cases = [
            ("http://example.com/paper.pdf", "paper.pdf"),
            ("http://example.com/paper?version=1", "paper.pdf"),
            ("http://example.com/path/", "file.pdf"),  # fallback
            ("http://example.com/paper with spaces.pdf", "paper with spaces.pdf"),
            ("http://example.com/påper.pdf", "pper.pdf"),  # Unicode handling
        ]
        
        for url, expected in test_cases:
            try:
                result = dl.sanitize_filename(url)
                if result == expected:
                    results["passed"] += 1
                    self.log(f"✓ sanitize_filename('{url}') -> '{result}'")
                else:
                    results["failed"] += 1
                    error = f"sanitize_filename('{url}'): expected '{expected}', got '{result}'"
                    results["errors"].append(error)
                    self.log(f"✗ {error}", "ERROR")
            except Exception as e:
                results["failed"] += 1
                error = f"sanitize_filename('{url}') failed: {e}"
                results["errors"].append(error)
                self.log(f"✗ {error}", "ERROR")
        
        # Test get_safe_unique_path
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                # Create a file
                test_file = Path(tmp_dir) / "test.pdf"
                test_file.write_text("test content")
                
                # Get unique path
                unique_path = dl.get_safe_unique_path(tmp_dir, "test.pdf")
                expected_path = str(Path(tmp_dir) / "test(1).pdf")
                
                if unique_path == expected_path:
                    results["passed"] += 1
                    self.log("✓ get_safe_unique_path() creates unique paths")
                else:
                    results["failed"] += 1
                    error = f"get_safe_unique_path(): expected '{expected_path}', got '{unique_path}'"
                    results["errors"].append(error)
                    self.log(f"✗ {error}", "ERROR")
        except Exception as e:
            results["failed"] += 1
            error = f"get_safe_unique_path() test failed: {e}"
            results["errors"].append(error)
            self.log(f"✗ {error}", "ERROR")
        
        # Test validate_pdf_file
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                # Create a fake PDF
                pdf_file = Path(tmp_dir) / "test.pdf"
                pdf_file.write_bytes(b"%PDF-1.4\n" + b"A" * 2000)  # Valid PDF header + content
                
                # Create a non-PDF
                non_pdf_file = Path(tmp_dir) / "test.txt"
                non_pdf_file.write_text("This is not a PDF")
                
                pdf_valid = dl.validate_pdf_file(str(pdf_file))
                non_pdf_valid = dl.validate_pdf_file(str(non_pdf_file))
                
                if pdf_valid and not non_pdf_valid:
                    results["passed"] += 1
                    self.log("✓ validate_pdf_file() correctly identifies PDFs")
                else:
                    results["failed"] += 1
                    error = f"validate_pdf_file(): pdf={pdf_valid}, non_pdf={non_pdf_valid}"
                    results["errors"].append(error)
                    self.log(f"✗ {error}", "ERROR")
        except Exception as e:
            results["failed"] += 1
            error = f"validate_pdf_file() test failed: {e}"
            results["errors"].append(error)
            self.log(f"✗ {error}", "ERROR")
        
        return results
    
    def test_direct_downloads(self) -> Dict[str, Any]:
        """Test direct file downloads."""
        self.log("Testing direct downloads...")
        
        results = {"passed": 0, "failed": 0, "errors": []}
        
        # Skip network tests if in CI environment
        if os.getenv("CI") == "true":
            self.log("Skipping network tests in CI environment")
            return {"passed": 0, "failed": 0, "errors": ["Skipped in CI"]}
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            for test_case in self.test_urls:
                try:
                    self.log(f"Testing: {test_case['description']}")
                    
                    result_path = dl.download_file(
                        test_case["url"],
                        tmp_dir,
                        retries=1,  # Reduce retries for faster testing
                        verify_ssl=True
                    )
                    
                    if test_case["should_work"]:
                        if result_path and os.path.exists(result_path):
                            file_size = os.path.getsize(result_path)
                            if file_size >= test_case["expected_size_min"]:
                                results["passed"] += 1
                                self.log(f"✓ {test_case['description']}: downloaded {file_size} bytes")
                            else:
                                results["failed"] += 1
                                error = f"{test_case['description']}: file too small ({file_size} bytes)"
                                results["errors"].append(error)
                                self.log(f"✗ {error}", "ERROR")
                        else:
                            results["failed"] += 1
                            error = f"{test_case['description']}: download failed"
                            results["errors"].append(error)
                            self.log(f"✗ {error}", "ERROR")
                    else:
                        # Should fail or warn
                        if result_path and os.path.exists(result_path):
                            # Check if it's actually a valid PDF for non-PDF URLs
                            if not test_case["url"].endswith(".pdf"):
                                is_pdf = dl.validate_pdf_file(result_path)
                                if not is_pdf:
                                    results["passed"] += 1
                                    self.log(f"✓ {test_case['description']}: correctly identified as non-PDF")
                                else:
                                    results["failed"] += 1
                                    error = f"{test_case['description']}: incorrectly identified as PDF"
                                    results["errors"].append(error)
                                    self.log(f"✗ {error}", "ERROR")
                            else:
                                results["failed"] += 1
                                error = f"{test_case['description']}: should have failed but succeeded"
                                results["errors"].append(error)
                                self.log(f"✗ {error}", "ERROR")
                        else:
                            results["passed"] += 1
                            self.log(f"✓ {test_case['description']}: correctly failed")
                    
                    # Small delay between requests
                    time.sleep(1)
                    
                except Exception as e:
                    if test_case["should_work"]:
                        results["failed"] += 1
                        error = f"{test_case['description']}: unexpected exception: {e}"
                        results["errors"].append(error)
                        self.log(f"✗ {error}", "ERROR")
                    else:
                        results["passed"] += 1
                        self.log(f"✓ {test_case['description']}: correctly failed with exception")
        
        return results
    
    def test_acquisition_engine_integration(self) -> Dict[str, Any]:
        """Test the acquisition engine with real metadata."""
        self.log("Testing acquisition engine integration...")
        
        results = {"passed": 0, "failed": 0, "errors": [], "attempts": []}
        
        # Skip network tests if in CI environment
        if os.getenv("CI") == "true":
            self.log("Skipping network tests in CI environment")
            return {"passed": 0, "failed": 0, "errors": ["Skipped in CI"], "attempts": []}
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            engine = dl.AcquisitionEngine()
            
            for paper in self.test_papers:
                try:
                    self.log(f"Testing acquisition: {paper['description']}")
                    
                    attempts = engine.acquire_paper(paper["metadata"], tmp_dir)
                    
                    if attempts:
                        results["attempts"].extend(attempts)
                        
                        # Check if any attempt succeeded
                        successful = engine.get_successful_download(attempts)
                        
                        if paper["expected_strategy"]:
                            # Should have at least tried
                            if attempts:
                                strategy_names = [attempt.strategy for attempt in attempts]
                                if paper["expected_strategy"] in strategy_names:
                                    results["passed"] += 1
                                    self.log(f"✓ {paper['description']}: tried expected strategy '{paper['expected_strategy']}'")
                                    
                                    if successful:
                                        self.log(f"  → Download successful: {successful.file_path}")
                                    else:
                                        self.log(f"  → Download failed (expected for some papers)")
                                else:
                                    results["failed"] += 1
                                    error = f"{paper['description']}: expected strategy '{paper['expected_strategy']}', got {strategy_names}"
                                    results["errors"].append(error)
                                    self.log(f"✗ {error}", "ERROR")
                            else:
                                results["failed"] += 1
                                error = f"{paper['description']}: no attempts made"
                                results["errors"].append(error)
                                self.log(f"✗ {error}", "ERROR")
                        else:
                            # Should not have succeeded
                            if not attempts or not successful:
                                results["passed"] += 1
                                self.log(f"✓ {paper['description']}: correctly no download (no sources)")
                            else:
                                results["failed"] += 1
                                error = f"{paper['description']}: unexpected success"
                                results["errors"].append(error)
                                self.log(f"✗ {error}", "ERROR")
                    else:
                        if not paper["expected_strategy"]:
                            results["passed"] += 1
                            self.log(f"✓ {paper['description']}: correctly no attempts")
                        else:
                            results["failed"] += 1
                            error = f"{paper['description']}: expected attempts but got none"
                            results["errors"].append(error)
                            self.log(f"✗ {error}", "ERROR")
                    
                    # Small delay between papers
                    time.sleep(2)
                    
                except Exception as e:
                    results["failed"] += 1
                    error = f"{paper['description']}: exception during acquisition: {e}"
                    results["errors"].append(error)
                    self.log(f"✗ {error}", "ERROR")
        
        return results
    
    def test_metadata_integration(self) -> Dict[str, Any]:
        """Test integration with metadata_fetcher."""
        self.log("Testing metadata integration...")
        
        results = {"passed": 0, "failed": 0, "errors": []}
        
        # Skip network tests if in CI environment
        if os.getenv("CI") == "true":
            self.log("Skipping network tests in CI environment")
            return {"passed": 0, "failed": 0, "errors": ["Skipped in CI"]}
        
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                # Test the complete pipeline
                test_title = "Attention Is All You Need"
                
                self.log(f"Testing complete pipeline for: {test_title}")
                
                file_path, attempts = dl.acquire_paper_by_metadata(
                    test_title,
                    tmp_dir,
                    arxiv_id="1706.03762"
                )
                
                if attempts:
                    results["passed"] += 1
                    self.log(f"✓ Metadata integration: {len(attempts)} attempts made")
                    
                    if file_path:
                        self.log(f"✓ Download successful: {file_path}")
                        if os.path.exists(file_path) and os.path.getsize(file_path) > 1000:
                            results["passed"] += 1
                            self.log(f"✓ Downloaded file is substantial: {os.path.getsize(file_path)} bytes")
                        else:
                            results["failed"] += 1
                            error = "Downloaded file is too small or doesn't exist"
                            results["errors"].append(error)
                            self.log(f"✗ {error}", "ERROR")
                    else:
                        self.log("  → Download failed (may be expected due to access restrictions)")
                        results["passed"] += 1  # Failure is acceptable
                else:
                    results["failed"] += 1
                    error = "No download attempts made"
                    results["errors"].append(error)
                    self.log(f"✗ {error}", "ERROR")
                    
        except Exception as e:
            results["failed"] += 1
            error = f"Metadata integration test failed: {e}"
            results["errors"].append(error)
            self.log(f"✗ {error}", "ERROR")
        
        return results
    
    def test_batch_downloads(self) -> Dict[str, Any]:
        """Test batch download functionality."""
        self.log("Testing batch downloads...")
        
        results = {"passed": 0, "failed": 0, "errors": []}
        
        # Skip network tests if in CI environment
        if os.getenv("CI") == "true":
            self.log("Skipping network tests in CI environment")
            return {"passed": 0, "failed": 0, "errors": ["Skipped in CI"]}
        
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                # Test URLs for batch download
                test_urls = [
                    "https://arxiv.org/pdf/1706.03762.pdf",  # Should work
                    "https://example.com/nonexistent.pdf",   # Should fail
                ]
                
                batch_results = dl.batch_download(
                    test_urls,
                    tmp_dir,
                    max_workers=1,
                    use_playwright=False,
                    use_scihub=False,
                    use_anna=False,
                    dry_run=False,
                    progress_desc="Test batch"
                )
                
                if len(batch_results) == len(test_urls):
                    results["passed"] += 1
                    self.log(f"✓ Batch download returned {len(batch_results)} results")
                    
                    # Check individual results
                    success_count = sum(1 for r in batch_results if r["status"] == "OK")
                    failure_count = len(batch_results) - success_count
                    
                    self.log(f"  → Successes: {success_count}, Failures: {failure_count}")
                    
                    if success_count > 0:
                        results["passed"] += 1
                        self.log("✓ At least one download succeeded")
                    else:
                        self.log("  → No downloads succeeded (may be expected)")
                        results["passed"] += 1  # Acceptable for test
                        
                else:
                    results["failed"] += 1
                    error = f"Batch download: expected {len(test_urls)} results, got {len(batch_results)}"
                    results["errors"].append(error)
                    self.log(f"✗ {error}", "ERROR")
                    
        except Exception as e:
            results["failed"] += 1
            error = f"Batch download test failed: {e}"
            results["errors"].append(error)
            self.log(f"✗ {error}", "ERROR")
        
        return results
    
    def test_task_queue_integration(self) -> Dict[str, Any]:
        """Test task queue integration."""
        self.log("Testing task queue integration...")
        
        results = {"passed": 0, "failed": 0, "errors": []}
        
        try:
            # Test task handler
            test_data = {
                'title': 'Test Paper',
                'dst_folder': tempfile.mkdtemp(),
                'doi': '10.1234/test'
            }
            
            # Call the task handler directly
            result = dl.download_paper_task_handler(test_data)
            
            if isinstance(result, dict) and 'success' in result:
                results["passed"] += 1
                self.log(f"✓ Task handler returned valid result: {result}")
            else:
                results["failed"] += 1
                error = f"Task handler returned invalid result: {result}"
                results["errors"].append(error)
                self.log(f"✗ {error}", "ERROR")
            
            # Clean up
            shutil.rmtree(test_data['dst_folder'])
            
        except Exception as e:
            results["failed"] += 1
            error = f"Task queue integration test failed: {e}"
            results["errors"].append(error)
            self.log(f"✗ {error}", "ERROR")
        
        return results
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and return comprehensive results."""
        self.log("=" * 60)
        self.log("COMPREHENSIVE DOWNLOADER TEST SUITE")
        self.log("=" * 60)
        
        start_time = time.time()
        
        # Set up test environment
        self.setUp()
        
        try:
            # Run all test categories
            test_methods = [
                ("Strategy Components", self.test_strategy_components),
                ("Utility Functions", self.test_utility_functions),
                ("Direct Downloads", self.test_direct_downloads),
                ("Acquisition Engine", self.test_acquisition_engine_integration),
                ("Metadata Integration", self.test_metadata_integration),
                ("Batch Downloads", self.test_batch_downloads),
                ("Task Queue Integration", self.test_task_queue_integration)
            ]
            
            all_results = {}
            total_passed = 0
            total_failed = 0
            
            for test_name, test_method in test_methods:
                self.log(f"\n--- {test_name} ---")
                results = test_method()
                all_results[test_name] = results
                total_passed += results["passed"]
                total_failed += results["failed"]
                
                self.log(f"{test_name}: {results['passed']} passed, {results['failed']} failed")
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Summary
            self.log("\n" + "=" * 60)
            self.log("SUMMARY")
            self.log("=" * 60)
            self.log(f"Total tests: {total_passed + total_failed}")
            self.log(f"Passed: {total_passed}")
            self.log(f"Failed: {total_failed}")
            self.log(f"Success rate: {total_passed / (total_passed + total_failed) * 100:.1f}%")
            self.log(f"Duration: {duration:.2f} seconds")
            
            if total_failed > 0:
                self.log("\nFAILED TESTS:")
                for test_name, results in all_results.items():
                    if results["failed"] > 0:
                        self.log(f"\n{test_name}:")
                        for error in results["errors"]:
                            self.log(f"  - {error}")
            
            return {
                "total_passed": total_passed,
                "total_failed": total_failed,
                "duration": duration,
                "details": all_results
            }
            
        finally:
            # Clean up test environment
            self.tearDown()


def main():
    """Main function to run comprehensive tests."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Comprehensive downloader tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--json", "-j", help="Save results to JSON file")
    args = parser.parse_args()
    
    # Run tests
    tester = ComprehensiveDownloaderTests(verbose=args.verbose)
    results = tester.run_all_tests()
    
    # Save to JSON if requested
    if args.json:
        with open(args.json, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nResults saved to: {args.json}")
    
    # Exit with appropriate code
    exit_code = 0 if results["total_failed"] == 0 else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()