#!/usr/bin/env python3
"""
Comprehensive test suite for metadata_fetcher.py
==============================================

This script provides thorough testing of the metadata fetcher with real-world examples,
edge cases, and integration scenarios. It's designed to be run standalone or as part
of the pytest suite.
"""

import os
import sys
import time
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

import metadata_fetcher as mf

class ComprehensiveMetadataTests:
    """Comprehensive test class for metadata_fetcher functionality."""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.results: Dict[str, Any] = {}
        self.test_papers = [
            # Well-known arXiv papers with different characteristics
            {
                "title": "Attention Is All You Need",
                "arxiv_id": "1706.03762",
                "doi": None,
                "expected_subjects": ["discrete_mathematics"],
                "description": "Famous transformer paper"
            },
            {
                "title": "Backward Stochastic Differential Equations with jumps",
                "arxiv_id": "math/0702620",
                "doi": None,
                "expected_subjects": ["probability_statistics"],
                "description": "BSDE paper with old arXiv format"
            },
            {
                "title": "Deep Learning",
                "arxiv_id": None,
                "doi": "10.1038/nature14539",
                "expected_subjects": ["discrete_mathematics"],
                "description": "Famous Nature deep learning paper"
            },
            # Open access paper
            {
                "title": "PLOS ONE test paper",
                "arxiv_id": None,
                "doi": "10.1371/journal.pone.0000001",
                "expected_subjects": [],
                "description": "Known open access paper"
            },
            # Mathematical paper with complex title
            {
                "title": "Stochastic Differential Equations with Jumps and Applications to Mathematical Finance",
                "arxiv_id": None,
                "doi": None,
                "expected_subjects": ["probability_statistics"],
                "description": "Complex mathematical title"
            }
        ]
    
    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp."""
        if self.verbose:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] [{level}] {message}")
    
    def test_canonicalization(self) -> Dict[str, Any]:
        """Test Unicode canonicalization with various edge cases."""
        self.log("Testing canonicalization...")
        
        test_cases = [
            # Basic cases
            ("Simple Title", "simple title"),
            ("  Spaces  ", "spaces"),
            
            # Unicode normalization
            ("Café", "cafe"),  # é -> e
            ("Straße", "strasse"),  # ß -> ss
            ("Æther", "aether"),  # æ -> ae
            ("Œuvre", "oeuvre"),  # œ -> oe
            
            # Mathematical symbols and dashes
            ("BSDE—Theory", "bsde-theory"),  # em-dash
            ("BSDE–Theory", "bsde-theory"),  # en-dash
            ("BSDE−Theory", "bsde-theory"),  # minus sign
            ("BSDE‐Theory", "bsde-theory"),  # hyphen
            
            # LaTeX commands (if strip_latex is available)
            ("\\textbf{Bold} and \\mathbb{R}", "bold and r"),
            ("$x^2 + y^2 = z^2$", "x^2 + y^2 = z^2"),  # Math should be handled
            
            # Bidirectional text controls
            ("Text\u200bwith\u200czero\u200dwidth", "textwithzerowidth"),
            
            # Complex combined case
            ("Théorème de Pythagore: $a^2 + b^2 = c^2$", "theoreme de pythagore: a^2 + b^2 = c^2"),
        ]
        
        results = {"passed": 0, "failed": 0, "errors": []}
        
        for input_text, expected in test_cases:
            try:
                result = mf.canonicalize(input_text)
                if result == expected:
                    results["passed"] += 1
                    self.log(f"✓ '{input_text}' -> '{result}'")
                else:
                    results["failed"] += 1
                    error = f"'{input_text}' -> expected: '{expected}', got: '{result}'"
                    results["errors"].append(error)
                    self.log(f"✗ {error}", "ERROR")
            except Exception as e:
                results["failed"] += 1
                error = f"'{input_text}' -> Exception: {e}"
                results["errors"].append(error)
                self.log(f"✗ {error}", "ERROR")
        
        return results
    
    def test_author_processing(self) -> Dict[str, Any]:
        """Test author name processing and matching."""
        self.log("Testing author processing...")
        
        test_cases = [
            # Family/given extraction
            {
                "input": "Smith, John Adam",
                "expected_family": "Smith",
                "expected_given": "John Adam"
            },
            {
                "input": "van der Waals, Johannes Diderik",
                "expected_family": "van der Waals",
                "expected_given": "Johannes Diderik"
            },
            {
                "input": "Einstein",
                "expected_family": "Einstein",
                "expected_given": ""
            },
            # Unicode in names
            {
                "input": "Müller, François",
                "expected_family": "Müller",
                "expected_given": "François"
            }
        ]
        
        results = {"passed": 0, "failed": 0, "errors": []}
        
        for case in test_cases:
            try:
                family, given = mf.extract_family_given(case["input"])
                if family == case["expected_family"] and given == case["expected_given"]:
                    results["passed"] += 1
                    self.log(f"✓ '{case['input']}' -> family: '{family}', given: '{given}'")
                else:
                    results["failed"] += 1
                    error = f"'{case['input']}' -> expected: ({case['expected_family']}, {case['expected_given']}), got: ({family}, {given})"
                    results["errors"].append(error)
                    self.log(f"✗ {error}", "ERROR")
            except Exception as e:
                results["failed"] += 1
                error = f"'{case['input']}' -> Exception: {e}"
                results["errors"].append(error)
                self.log(f"✗ {error}", "ERROR")
        
        # Test author matching
        author_match_cases = [
            (["Smith, J.", "Doe, A."], ["John Smith", "A. Doe"], True),
            (["Smith, John"], ["Smith, J."], True),
            (["Einstein, A."], ["Newton, I."], False),
            (["García, J."], ["Garcia, J."], True),  # Unicode normalization
        ]
        
        for authors_a, authors_b, expected in author_match_cases:
            try:
                result = mf.authors_match(authors_a, authors_b)
                if result == expected:
                    results["passed"] += 1
                    self.log(f"✓ Authors match {authors_a} ≈ {authors_b}: {result}")
                else:
                    results["failed"] += 1
                    error = f"Authors {authors_a} ≈ {authors_b}: expected {expected}, got {result}"
                    results["errors"].append(error)
                    self.log(f"✗ {error}", "ERROR")
            except Exception as e:
                results["failed"] += 1
                error = f"Authors {authors_a} ≈ {authors_b} -> Exception: {e}"
                results["errors"].append(error)
                self.log(f"✗ {error}", "ERROR")
        
        return results
    
    def test_arxiv_version_detection(self) -> Dict[str, Any]:
        """Test arXiv ID parsing and version detection."""
        self.log("Testing arXiv version detection...")
        
        test_cases = [
            # New format
            {
                "arxiv_id": "2101.00001v3",
                "expected_base": "2101.00001",
                "expected_version": "v3",
                "expected_version_num": 3,
                "expected_format": "new"
            },
            {
                "arxiv_id": "2101.00001",
                "expected_base": "2101.00001",
                "expected_version": None,
                "expected_version_num": None,
                "expected_format": "new"
            },
            # Old format
            {
                "arxiv_id": "math.AG/0506123v2",
                "expected_base": "math.AG/0506123",
                "expected_version": "v2",
                "expected_version_num": 2,
                "expected_format": "old"
            },
            {
                "arxiv_id": "math/0702620",
                "expected_base": "math/0702620",
                "expected_version": None,
                "expected_version_num": None,
                "expected_format": "old"
            },
            # Edge cases
            {
                "arxiv_id": "",
                "expected_base": None,
                "expected_version": None,
                "expected_version_num": None,
                "expected_format": None
            }
        ]
        
        results = {"passed": 0, "failed": 0, "errors": []}
        
        for case in test_cases:
            try:
                info = mf.extract_arxiv_info(case["arxiv_id"])
                
                # Handle empty case
                if not case["arxiv_id"]:
                    if info == {}:
                        results["passed"] += 1
                        self.log(f"✓ Empty arXiv ID handled correctly")
                        continue
                    else:
                        results["failed"] += 1
                        error = f"Empty arXiv ID should return empty dict, got: {info}"
                        results["errors"].append(error)
                        self.log(f"✗ {error}", "ERROR")
                        continue
                
                # Check all expected fields
                checks = [
                    ("id", case["expected_base"]),
                    ("version", case["expected_version"]),
                    ("version_num", case["expected_version_num"]),
                    ("format", case["expected_format"])
                ]
                
                all_correct = True
                for field, expected in checks:
                    if info.get(field) != expected:
                        all_correct = False
                        error = f"arXiv '{case['arxiv_id']}' field '{field}': expected {expected}, got {info.get(field)}"
                        results["errors"].append(error)
                        self.log(f"✗ {error}", "ERROR")
                
                if all_correct:
                    results["passed"] += 1
                    self.log(f"✓ arXiv '{case['arxiv_id']}' parsed correctly: {info}")
                else:
                    results["failed"] += 1
                    
            except Exception as e:
                results["failed"] += 1
                error = f"arXiv '{case['arxiv_id']}' -> Exception: {e}"
                results["errors"].append(error)
                self.log(f"✗ {error}", "ERROR")
        
        return results
    
    def test_subject_classification(self) -> Dict[str, Any]:
        """Test mathematical subject classification."""
        self.log("Testing subject classification...")
        
        test_cases = [
            # Clear classifications
            {
                "title": "Stochastic Differential Equations and Applications",
                "abstract": "We study stochastic processes and Brownian motion in mathematical finance.",
                "expected_subjects": ["probability_statistics"]
            },
            {
                "title": "Group Theory and Lie Algebras",
                "abstract": "This paper studies algebraic structures including groups, rings, and fields.",
                "expected_subjects": ["algebra"]
            },
            {
                "title": "Partial Differential Equations in Fluid Mechanics",
                "abstract": "We analyze PDEs arising in fluid dynamics and continuum mechanics.",
                "expected_subjects": ["analysis", "mechanics"]
            },
            {
                "title": "Graph Theory and Combinatorial Optimization",
                "abstract": "We study graph algorithms and discrete optimization problems.",
                "expected_subjects": ["discrete_mathematics"]
            },
            # Ambiguous cases
            {
                "title": "Mathematical Methods in Economics",
                "abstract": "We apply optimization and probability theory to economic models.",
                "expected_subjects": ["optimization", "probability_statistics"]
            },
            # Non-mathematical
            {
                "title": "Cooking Techniques for Italian Cuisine",
                "abstract": "This paper describes various methods for preparing pasta and sauce.",
                "expected_subjects": []
            }
        ]
        
        results = {"passed": 0, "failed": 0, "errors": [], "classifications": []}
        
        for case in test_cases:
            try:
                subjects = mf.classify_mathematical_subject(case["title"], case["abstract"])
                
                # Check if any expected subjects are found
                if case["expected_subjects"]:
                    found_expected = any(subj in subjects for subj in case["expected_subjects"])
                    if found_expected:
                        results["passed"] += 1
                        self.log(f"✓ '{case['title']}' -> {subjects} (found expected)")
                    else:
                        results["failed"] += 1
                        error = f"'{case['title']}' -> expected one of {case['expected_subjects']}, got {subjects}"
                        results["errors"].append(error)
                        self.log(f"✗ {error}", "ERROR")
                else:
                    # No subjects expected
                    if not subjects:
                        results["passed"] += 1
                        self.log(f"✓ '{case['title']}' -> no subjects (as expected)")
                    else:
                        results["failed"] += 1
                        error = f"'{case['title']}' -> expected no subjects, got {subjects}"
                        results["errors"].append(error)
                        self.log(f"✗ {error}", "ERROR")
                
                results["classifications"].append({
                    "title": case["title"],
                    "subjects": subjects,
                    "expected": case["expected_subjects"]
                })
                
            except Exception as e:
                results["failed"] += 1
                error = f"'{case['title']}' -> Exception: {e}"
                results["errors"].append(error)
                self.log(f"✗ {error}", "ERROR")
        
        return results
    
    def test_real_world_metadata_fetching(self) -> Dict[str, Any]:
        """Test real-world metadata fetching with known papers."""
        self.log("Testing real-world metadata fetching...")
        
        results = {"passed": 0, "failed": 0, "errors": [], "metadata": []}
        
        # Skip network tests if in CI environment
        if os.getenv("CI") == "true":
            self.log("Skipping network tests in CI environment")
            return {"passed": 0, "failed": 0, "errors": ["Skipped in CI"], "metadata": []}
        
        for paper in self.test_papers:
            try:
                self.log(f"Fetching metadata for: {paper['description']}")
                
                # Fetch metadata using all sources
                metadata_list = mf.fetch_metadata_all_sources(
                    paper["title"],
                    doi=paper.get("doi"),
                    arxiv_id=paper.get("arxiv_id"),
                    verbose=True
                )
                
                if metadata_list:
                    metadata = metadata_list[0]  # Use best result
                    
                    # Basic validation
                    has_title = bool(metadata.get("title"))
                    has_source = bool(metadata.get("source"))
                    
                    # Check for expected subjects if specified
                    subjects_correct = True
                    if paper["expected_subjects"]:
                        found_subjects = metadata.get("mathematical_subjects", [])
                        subjects_correct = any(subj in found_subjects for subj in paper["expected_subjects"])
                    
                    if has_title and has_source and subjects_correct:
                        results["passed"] += 1
                        self.log(f"✓ {paper['description']}: title='{metadata.get('title')}', source={metadata.get('source')}")
                        
                        # Log interesting metadata
                        if metadata.get("is_open_access"):
                            self.log(f"  → Open access: {metadata.get('best_oa_location')}")
                        if metadata.get("mathematical_subjects"):
                            self.log(f"  → Subjects: {metadata.get('mathematical_subjects')}")
                        if metadata.get("has_arxiv_updates"):
                            self.log(f"  → arXiv updates available: v{metadata.get('current_arxiv_version')} -> v{metadata.get('latest_arxiv_version')}")
                    else:
                        results["failed"] += 1
                        error = f"{paper['description']}: missing required fields or incorrect subjects"
                        results["errors"].append(error)
                        self.log(f"✗ {error}", "ERROR")
                    
                    results["metadata"].append({
                        "paper": paper["description"],
                        "metadata": metadata
                    })
                else:
                    results["failed"] += 1
                    error = f"{paper['description']}: no metadata found"
                    results["errors"].append(error)
                    self.log(f"✗ {error}", "ERROR")
                
                # Small delay to be respectful to APIs
                time.sleep(1)
                
            except Exception as e:
                results["failed"] += 1
                error = f"{paper['description']} -> Exception: {e}"
                results["errors"].append(error)
                self.log(f"✗ {error}", "ERROR")
        
        return results
    
    def test_batch_processing(self) -> Dict[str, Any]:
        """Test batch metadata processing."""
        self.log("Testing batch processing...")
        
        # Create test queries
        test_queries = [
            ("Test Paper One", ["Smith, J.", "Doe, A."]),
            ("Test Paper Two", ["Einstein, A."]),
            ("Nonexistent Paper XYZ123", ["Nobody, N."])
        ]
        
        results = {"passed": 0, "failed": 0, "errors": []}
        
        try:
            # Skip network tests if in CI environment
            if os.getenv("CI") == "true":
                self.log("Skipping batch processing test in CI environment")
                return {"passed": 1, "failed": 0, "errors": []}
            
            batch_results = mf.batch_metadata_lookup(
                test_queries,
                max_workers=2,
                progress_bar=False
            )
            
            if isinstance(batch_results, dict) and len(batch_results) == len(test_queries):
                results["passed"] += 1
                self.log(f"✓ Batch processing returned {len(batch_results)} results")
                
                for title, metadata in batch_results.items():
                    self.log(f"  → '{title}': {len(metadata)} fields")
            else:
                results["failed"] += 1
                error = f"Batch processing: expected {len(test_queries)} results, got {len(batch_results) if batch_results else 0}"
                results["errors"].append(error)
                self.log(f"✗ {error}", "ERROR")
                
        except Exception as e:
            results["failed"] += 1
            error = f"Batch processing -> Exception: {e}"
            results["errors"].append(error)
            self.log(f"✗ {error}", "ERROR")
        
        return results
    
    def test_csv_export(self) -> Dict[str, Any]:
        """Test CSV metadata export functionality."""
        self.log("Testing CSV export...")
        
        results = {"passed": 0, "failed": 0, "errors": []}
        
        try:
            # Create test metadata
            test_metadata = {
                "paper1.pdf": {
                    "title": "Test Paper One",
                    "authors": ["Smith, J.", "Doe, A."],
                    "published": "2023-01-01",
                    "DOI": "10.1234/test1",
                    "source": "test",
                    "is_open_access": True,
                    "mathematical_subjects": ["probability_statistics"],
                    "msc_codes": ["60"],
                    "has_arxiv_updates": False
                },
                "paper2.pdf": {
                    "title": "Test Paper Two",
                    "authors": ["Einstein, A."],
                    "published": [[2023, 1, 1]],  # Legacy format
                    "source": "test"
                }
            }
            
            # Test CSV writing
            with tempfile.TemporaryDirectory() as tmp_dir:
                csv_path = Path(tmp_dir) / "test_metadata.csv"
                mf.write_csv_metadata(csv_path, test_metadata)
                
                if csv_path.exists():
                    content = csv_path.read_text("utf-8")
                    
                    # Check for required fields
                    required_headers = ["key", "title", "authors", "published", "DOI", "source"]
                    headers_present = all(header in content for header in required_headers)
                    
                    # Check for data rows
                    lines = content.strip().split('\n')
                    has_data = len(lines) >= 3  # header + 2 data rows
                    
                    if headers_present and has_data:
                        results["passed"] += 1
                        self.log(f"✓ CSV export successful: {len(lines)} lines")
                        self.log(f"  → Headers: {headers_present}")
                        self.log(f"  → Data rows: {len(lines) - 1}")
                    else:
                        results["failed"] += 1
                        error = f"CSV export: headers_present={headers_present}, lines={len(lines)}"
                        results["errors"].append(error)
                        self.log(f"✗ {error}", "ERROR")
                else:
                    results["failed"] += 1
                    error = "CSV file was not created"
                    results["errors"].append(error)
                    self.log(f"✗ {error}", "ERROR")
                    
        except Exception as e:
            results["failed"] += 1
            error = f"CSV export -> Exception: {e}"
            results["errors"].append(error)
            self.log(f"✗ {error}", "ERROR")
        
        return results
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and return comprehensive results."""
        self.log("=" * 60)
        self.log("COMPREHENSIVE METADATA_FETCHER TEST SUITE")
        self.log("=" * 60)
        
        start_time = time.time()
        
        # Run all test categories
        test_methods = [
            ("Canonicalization", self.test_canonicalization),
            ("Author Processing", self.test_author_processing),
            ("arXiv Version Detection", self.test_arxiv_version_detection),
            ("Subject Classification", self.test_subject_classification),
            ("Real-World Metadata", self.test_real_world_metadata_fetching),
            ("Batch Processing", self.test_batch_processing),
            ("CSV Export", self.test_csv_export)
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


def main():
    """Main function to run comprehensive tests."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Comprehensive metadata_fetcher tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--json", "-j", help="Save results to JSON file")
    args = parser.parse_args()
    
    # Run tests
    tester = ComprehensiveMetadataTests(verbose=args.verbose)
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