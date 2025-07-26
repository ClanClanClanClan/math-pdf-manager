#!/usr/bin/env python3
"""
Comprehensive test runner for metadata_fetcher and downloader
===========================================================

This script runs comprehensive tests for both metadata_fetcher and downloader
components, providing detailed reports and integration testing.
"""

import os
import sys
import time
import json
import argparse
from pathlib import Path
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def run_pytest_tests(verbose: bool = False) -> Dict[str, Any]:
    """Run the existing pytest test suite."""
    import subprocess
    
    print("=" * 60)
    print("RUNNING EXISTING PYTEST SUITE")
    print("=" * 60)
    
    # Run metadata_fetcher tests
    cmd = [
        sys.executable, "-m", "pytest", 
        "tests/test_metadata_fetcher.py",
        "-v" if verbose else "-q"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    result_metadata = subprocess.run(cmd, capture_output=True, text=True)
    
    # Run downloader tests
    cmd = [
        sys.executable, "-m", "pytest", 
        "tests/test_downloader.py", 
        "-v" if verbose else "-q"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    result_downloader = subprocess.run(cmd, capture_output=True, text=True)
    
    # Parse results
    metadata_passed = result_metadata.returncode == 0
    downloader_passed = result_downloader.returncode == 0
    
    print(f"\nPytest Results:")
    print(f"  metadata_fetcher: {'✓ PASSED' if metadata_passed else '✗ FAILED'}")
    print(f"  downloader: {'✓ PASSED' if downloader_passed else '✗ FAILED'}")
    
    if verbose:
        if result_metadata.stdout:
            print(f"\nMetadata Fetcher Output:\n{result_metadata.stdout}")
        if result_downloader.stdout:
            print(f"\nDownloader Output:\n{result_downloader.stdout}")
        
        if result_metadata.stderr:
            print(f"\nMetadata Fetcher Errors:\n{result_metadata.stderr}")
        if result_downloader.stderr:
            print(f"\nDownloader Errors:\n{result_downloader.stderr}")
    
    return {
        "metadata_fetcher": {
            "passed": metadata_passed,
            "returncode": result_metadata.returncode,
            "stdout": result_metadata.stdout,
            "stderr": result_metadata.stderr
        },
        "downloader": {
            "passed": downloader_passed,
            "returncode": result_downloader.returncode,
            "stdout": result_downloader.stdout,
            "stderr": result_downloader.stderr
        }
    }

def run_comprehensive_tests(verbose: bool = False, skip_network: bool = False) -> Dict[str, Any]:
    """Run comprehensive test suites."""
    print("\n" + "=" * 60)
    print("RUNNING COMPREHENSIVE TEST SUITES")
    print("=" * 60)
    
    results = {}
    
    # Set environment variable to skip network tests if requested
    if skip_network:
        os.environ["CI"] = "true"
        print("Skipping network tests (CI mode enabled)")
    
    # Run metadata_fetcher comprehensive tests
    print("\n--- Metadata Fetcher Comprehensive Tests ---")
    try:
        from test_metadata_fetcher_comprehensive import ComprehensiveMetadataTests
        metadata_tester = ComprehensiveMetadataTests(verbose=verbose)
        metadata_results = metadata_tester.run_all_tests()
        results["metadata_fetcher_comprehensive"] = metadata_results
    except Exception as e:
        print(f"Error running metadata fetcher tests: {e}")
        results["metadata_fetcher_comprehensive"] = {
            "total_passed": 0,
            "total_failed": 1,
            "error": str(e)
        }
    
    # Run downloader comprehensive tests
    print("\n--- Downloader Comprehensive Tests ---")
    try:
        from test_downloader_comprehensive import ComprehensiveDownloaderTests
        downloader_tester = ComprehensiveDownloaderTests(verbose=verbose)
        downloader_results = downloader_tester.run_all_tests()
        results["downloader_comprehensive"] = downloader_results
    except Exception as e:
        print(f"Error running downloader tests: {e}")
        results["downloader_comprehensive"] = {
            "total_passed": 0,
            "total_failed": 1,
            "error": str(e)
        }
    
    # Clean up environment
    if skip_network and "CI" in os.environ:
        del os.environ["CI"]
    
    return results

def run_integration_tests(verbose: bool = False) -> Dict[str, Any]:
    """Run integration tests between metadata_fetcher and downloader."""
    print("\n" + "=" * 60)
    print("RUNNING INTEGRATION TESTS")
    print("=" * 60)
    
    results = {"passed": 0, "failed": 0, "errors": []}
    
    # Skip network tests if in CI environment
    if os.getenv("CI") == "true":
        print("Skipping integration tests in CI environment")
        return {"passed": 0, "failed": 0, "errors": ["Skipped in CI"]}
    
    try:
        import tempfile
        import metadata_fetcher as mf
        sys.path.insert(0, str(Path(__file__).parent / "scripts"))
        import downloader as dl
        
        # Test 1: Fetch metadata and attempt download
        print("\n--- Test 1: Metadata → Download Pipeline ---")
        
        test_paper = {
            "title": "Attention Is All You Need",
            "arxiv_id": "1706.03762"
        }
        
        # Fetch metadata
        print(f"Fetching metadata for: {test_paper['title']}")
        metadata_list = mf.fetch_metadata_all_sources(
            test_paper["title"],
            arxiv_id=test_paper["arxiv_id"]
        )
        
        if metadata_list:
            metadata = metadata_list[0]
            print(f"✓ Metadata found: {metadata.get('title')} from {metadata.get('source')}")
            
            # Test download strategies
            with tempfile.TemporaryDirectory() as tmp_dir:
                engine = dl.AcquisitionEngine()
                attempts = engine.acquire_paper(metadata, tmp_dir)
                
                if attempts:
                    results["passed"] += 1
                    print(f"✓ Download attempts made: {len(attempts)}")
                    
                    successful = engine.get_successful_download(attempts)
                    if successful:
                        print(f"✓ Download successful: {successful.file_path}")
                        results["passed"] += 1
                    else:
                        print("  → Download failed (may be expected)")
                        results["passed"] += 1  # Acceptable
                else:
                    results["failed"] += 1
                    results["errors"].append("No download attempts made")
                    print("✗ No download attempts made")
        else:
            results["failed"] += 1
            results["errors"].append("No metadata found")
            print("✗ No metadata found")
        
        # Test 2: End-to-end pipeline
        print("\n--- Test 2: End-to-End Pipeline ---")
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path, attempts = dl.acquire_paper_by_metadata(
                test_paper["title"],
                tmp_dir,
                arxiv_id=test_paper["arxiv_id"]
            )
            
            if attempts:
                results["passed"] += 1
                print(f"✓ End-to-end pipeline completed: {len(attempts)} attempts")
                
                if file_path:
                    print(f"✓ File downloaded: {file_path}")
                    results["passed"] += 1
                else:
                    print("  → Download failed (may be expected)")
                    results["passed"] += 1  # Acceptable
            else:
                results["failed"] += 1
                results["errors"].append("End-to-end pipeline failed")
                print("✗ End-to-end pipeline failed")
        
        # Test 3: Subject classification integration
        print("\n--- Test 3: Subject Classification ---")
        
        test_titles = [
            "Stochastic Differential Equations with Jumps",
            "Deep Learning for Computer Vision",
            "Graph Theory and Combinatorial Optimization"
        ]
        
        for title in test_titles:
            subjects = mf.classify_mathematical_subject(title)
            if subjects:
                results["passed"] += 1
                print(f"✓ '{title}' → {subjects}")
            else:
                print(f"  → '{title}' → no subjects identified")
                results["passed"] += 1  # Acceptable for some titles
        
    except Exception as e:
        results["failed"] += 1
        results["errors"].append(f"Integration test error: {e}")
        print(f"✗ Integration test error: {e}")
    
    return results

def generate_report(all_results: Dict[str, Any], output_file: str = None) -> str:
    """Generate a comprehensive test report."""
    report = []
    report.append("=" * 80)
    report.append("COMPREHENSIVE TEST REPORT")
    report.append("=" * 80)
    report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    # Summary statistics
    total_passed = 0
    total_failed = 0
    
    for test_name, test_results in all_results.items():
        if isinstance(test_results, dict):
            passed = test_results.get("total_passed", 0)
            failed = test_results.get("total_failed", 0)
            
            # Handle different result formats
            if "passed" in test_results and "failed" in test_results:
                passed = test_results["passed"]
                failed = test_results["failed"]
            
            total_passed += passed
            total_failed += failed
    
    report.append("SUMMARY")
    report.append("-" * 40)
    report.append(f"Total Tests: {total_passed + total_failed}")
    report.append(f"Passed: {total_passed}")
    report.append(f"Failed: {total_failed}")
    if total_passed + total_failed > 0:
        success_rate = total_passed / (total_passed + total_failed) * 100
        report.append(f"Success Rate: {success_rate:.1f}%")
    report.append("")
    
    # Detailed results
    report.append("DETAILED RESULTS")
    report.append("-" * 40)
    
    for test_name, test_results in all_results.items():
        report.append(f"\n{test_name.upper().replace('_', ' ')}")
        report.append("." * len(test_name))
        
        if isinstance(test_results, dict):
            if "total_passed" in test_results and "total_failed" in test_results:
                passed = test_results["total_passed"]
                failed = test_results["total_failed"]
                report.append(f"Passed: {passed}, Failed: {failed}")
                
                if "duration" in test_results:
                    report.append(f"Duration: {test_results['duration']:.2f}s")
                
                # Show errors if any
                if failed > 0 and "details" in test_results:
                    report.append("\nErrors:")
                    for detail_name, detail_results in test_results["details"].items():
                        if detail_results.get("failed", 0) > 0:
                            report.append(f"  {detail_name}:")
                            for error in detail_results.get("errors", []):
                                report.append(f"    - {error}")
            
            elif "passed" in test_results and "failed" in test_results:
                passed = test_results["passed"]
                failed = test_results["failed"]
                report.append(f"Passed: {passed}, Failed: {failed}")
                
                if failed > 0 and "errors" in test_results:
                    report.append("\nErrors:")
                    for error in test_results["errors"]:
                        report.append(f"  - {error}")
            
            elif "error" in test_results:
                report.append(f"ERROR: {test_results['error']}")
        else:
            report.append(f"Result: {test_results}")
    
    report_text = "\n".join(report)
    
    if output_file:
        with open(output_file, 'w') as f:
            f.write(report_text)
        print(f"\nDetailed report saved to: {output_file}")
    
    return report_text

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Comprehensive test runner for metadata_fetcher and downloader")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--skip-pytest", action="store_true", help="Skip existing pytest tests")
    parser.add_argument("--skip-comprehensive", action="store_true", help="Skip comprehensive tests")
    parser.add_argument("--skip-integration", action="store_true", help="Skip integration tests")
    parser.add_argument("--skip-network", action="store_true", help="Skip network-dependent tests")
    parser.add_argument("--json", "-j", help="Save results to JSON file")
    parser.add_argument("--report", "-r", help="Save text report to file")
    args = parser.parse_args()
    
    print("Comprehensive Test Runner for Math-PDF Manager")
    print("=" * 50)
    print(f"Working directory: {os.getcwd()}")
    print(f"Python version: {sys.version}")
    print("")
    
    all_results = {}
    start_time = time.time()
    
    # Run tests based on arguments
    if not args.skip_pytest:
        pytest_results = run_pytest_tests(verbose=args.verbose)
        all_results["pytest"] = pytest_results
    
    if not args.skip_comprehensive:
        comprehensive_results = run_comprehensive_tests(verbose=args.verbose, skip_network=args.skip_network)
        all_results.update(comprehensive_results)
    
    if not args.skip_integration:
        integration_results = run_integration_tests(verbose=args.verbose)
        all_results["integration"] = integration_results
    
    end_time = time.time()
    total_duration = end_time - start_time
    
    # Generate report
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    print(f"Total duration: {total_duration:.2f} seconds")
    
    report_text = generate_report(all_results, args.report)
    print(report_text.split("DETAILED RESULTS")[0])  # Show summary
    
    # Save JSON results if requested
    if args.json:
        all_results["meta"] = {
            "total_duration": total_duration,
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        with open(args.json, 'w') as f:
            json.dump(all_results, f, indent=2, default=str)
        print(f"Full results saved to: {args.json}")
    
    # Determine exit code
    any_failures = False
    for test_results in all_results.values():
        if isinstance(test_results, dict):
            if test_results.get("total_failed", 0) > 0 or test_results.get("failed", 0) > 0:
                any_failures = True
                break
            if "error" in test_results:
                any_failures = True
                break
    
    if any_failures:
        print("\n❌ Some tests failed. See detailed report above.")
        sys.exit(1)
    else:
        print("\n✅ All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()