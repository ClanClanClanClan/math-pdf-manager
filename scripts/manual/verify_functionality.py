#!/usr/bin/env python3
"""
FUNCTIONALITY VERIFICATION SCRIPT
=================================

Comprehensive checks to ensure all functionality is preserved after reorganization.
Run this BEFORE and AFTER reorganization to ensure nothing is broken.
"""

import subprocess
import sys
import importlib
import os
from pathlib import Path
import json
from datetime import datetime

class FunctionalityVerifier:
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'checks': {},
            'summary': {'passed': 0, 'failed': 0, 'warnings': 0}
        }
        
    def check_imports(self):
        """Check if critical imports work"""
        print("\n🔍 Checking Critical Imports...")
        
        critical_imports = [
            # Core imports
            ("Core config", "from src.core import config_manager"),
            ("DI container", "from src.core.dependency_injection import get_container"),
            ("Validators", "from src.validators import optimized_filename_validator"),
            
            # Publishers
            ("IEEE publisher", "from src.publishers import ieee_publisher"),
            ("SIAM publisher", "from src.publishers import siam_publisher"),
            
            # Downloader
            ("Browser downloader", "from src.downloader import browser_publisher_downloaders"),
            
            # VPN (these will need updating after reorg)
            ("VPN credentials", "try: from secure_vpn_credentials import get_vpn_password\nexcept: from scripts.vpn.secure_vpn_credentials import get_vpn_password"),
        ]
        
        for name, import_statement in critical_imports:
            try:
                exec(import_statement)
                self.results['checks'][f'import_{name}'] = 'PASS'
                print(f"  ✅ {name}")
            except Exception as e:
                self.results['checks'][f'import_{name}'] = f'FAIL: {str(e)}'
                print(f"  ❌ {name}: {e}")
                
    def check_files_exist(self):
        """Check if critical files exist"""
        print("\n📁 Checking Critical Files...")
        
        critical_files = [
            # Configuration
            "config/config.yaml",
            "config/requirements.txt",
            
            # Data files
            "data/known_authors_1.txt",
            "data/languages/french.yaml",
            
            # Core source files
            "src/__init__.py",
            "src/core/__init__.py",
            "src/publishers/ieee_publisher.py",
            "src/publishers/siam_publisher.py",
            "src/validators/optimized_filename_validator.py",
            
            # Test files
            "tests/conftest.py",
        ]
        
        for file_path in critical_files:
            full_path = Path(file_path)
            if full_path.exists():
                self.results['checks'][f'file_{file_path}'] = 'PASS'
                print(f"  ✅ {file_path}")
            else:
                # Check alternate locations after reorg
                alt_paths = [
                    Path(f"scripts/vpn/{file_path}"),
                    Path(f"scripts/publishers/{file_path}"),
                    Path(f"experiments/{file_path}")
                ]
                
                found = False
                for alt_path in alt_paths:
                    if alt_path.exists():
                        self.results['checks'][f'file_{file_path}'] = f'MOVED: {alt_path}'
                        print(f"  ⚠️ {file_path} → {alt_path}")
                        found = True
                        break
                        
                if not found:
                    self.results['checks'][f'file_{file_path}'] = 'FAIL: Not found'
                    print(f"  ❌ {file_path}")
                    
    def check_tests(self):
        """Run a subset of critical tests"""
        print("\n🧪 Running Critical Tests...")
        
        test_commands = [
            ("Core tests", ["python", "-m", "pytest", "tests/core/test_exceptions.py", "-v"]),
            ("Validator tests", ["python", "-m", "pytest", "tests/core/test_comprehensive_validation.py", "-v"]),
        ]
        
        for test_name, command in test_commands:
            try:
                result = subprocess.run(command, capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    self.results['checks'][f'test_{test_name}'] = 'PASS'
                    print(f"  ✅ {test_name}")
                else:
                    self.results['checks'][f'test_{test_name}'] = f'FAIL: {result.stderr[:100]}'
                    print(f"  ❌ {test_name}")
            except subprocess.TimeoutExpired:
                self.results['checks'][f'test_{test_name}'] = 'FAIL: Timeout'
                print(f"  ❌ {test_name}: Timeout")
            except Exception as e:
                self.results['checks'][f'test_{test_name}'] = f'FAIL: {str(e)}'
                print(f"  ❌ {test_name}: {e}")
                
    def check_executables(self):
        """Check if key scripts are executable"""
        print("\n🔧 Checking Script Executability...")
        
        # These paths will change after reorg
        executable_scripts = [
            ("VPN Connect", "bulletproof_vpn_connect.py", "scripts/vpn/bulletproof_vpn_connect.py"),
            ("IEEE Downloader", "src/publishers/ieee_publisher.py", None),
            ("SIAM Downloader", "src/publishers/siam_publisher.py", None),
        ]
        
        for name, current_path, new_path in executable_scripts:
            paths_to_check = [current_path]
            if new_path:
                paths_to_check.append(new_path)
                
            found = False
            for path in paths_to_check:
                if Path(path).exists():
                    try:
                        # Try to compile the Python file
                        with open(path, 'r') as f:
                            compile(f.read(), path, 'exec')
                        self.results['checks'][f'executable_{name}'] = 'PASS'
                        print(f"  ✅ {name}")
                        found = True
                        break
                    except SyntaxError as e:
                        self.results['checks'][f'executable_{name}'] = f'FAIL: Syntax error'
                        print(f"  ❌ {name}: Syntax error")
                        found = True
                        break
                        
            if not found:
                self.results['checks'][f'executable_{name}'] = 'FAIL: Not found'
                print(f"  ❌ {name}: Not found")
                
    def check_dependencies(self):
        """Check if required packages are installed"""
        print("\n📦 Checking Dependencies...")
        
        required_packages = [
            "playwright",
            "pytest", 
            "pyyaml",
            "cryptography",
            "requests",
            "tqdm",
            "pymupdf",
            "pdfplumber",
        ]
        
        for package in required_packages:
            try:
                importlib.import_module(package.replace("-", "_"))
                self.results['checks'][f'dep_{package}'] = 'PASS'
                print(f"  ✅ {package}")
            except ImportError:
                self.results['checks'][f'dep_{package}'] = 'FAIL: Not installed'
                print(f"  ❌ {package}")
                
    def check_data_integrity(self):
        """Check integrity of data files"""
        print("\n🔐 Checking Data Integrity...")
        
        # Check known authors file
        authors_file = Path("data/known_authors_1.txt")
        if authors_file.exists():
            lines = authors_file.read_text().strip().split('\n')
            author_count = len(lines)
            if author_count > 600:
                self.results['checks']['data_authors'] = f'PASS: {author_count} authors'
                print(f"  ✅ Known authors: {author_count} entries")
            else:
                self.results['checks']['data_authors'] = f'WARN: Only {author_count} authors'
                print(f"  ⚠️ Known authors: Only {author_count} entries")
        else:
            self.results['checks']['data_authors'] = 'FAIL: File not found'
            print(f"  ❌ Known authors file not found")
            
    def check_config_files(self):
        """Check configuration files"""
        print("\n⚙️ Checking Configuration...")
        
        config_file = Path("config/config.yaml")
        if config_file.exists():
            try:
                import yaml
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f)
                    
                # Check for critical config sections
                critical_sections = ['metadata_sources', 'extractors', 'grobid_server']
                missing = [s for s in critical_sections if s not in config]
                
                if not missing:
                    self.results['checks']['config_structure'] = 'PASS'
                    print(f"  ✅ Config structure valid")
                else:
                    self.results['checks']['config_structure'] = f'WARN: Missing {missing}'
                    print(f"  ⚠️ Config missing sections: {missing}")
                    
            except Exception as e:
                self.results['checks']['config_structure'] = f'FAIL: {str(e)}'
                print(f"  ❌ Config error: {e}")
        else:
            self.results['checks']['config_structure'] = 'FAIL: Not found'
            print(f"  ❌ Config file not found")
            
    def generate_summary(self):
        """Generate summary of results"""
        for check, result in self.results['checks'].items():
            if result == 'PASS':
                self.results['summary']['passed'] += 1
            elif result.startswith('FAIL'):
                self.results['summary']['failed'] += 1
            else:
                self.results['summary']['warnings'] += 1
                
    def save_results(self):
        """Save results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"functionality_check_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
            
        print(f"\n💾 Results saved to: {results_file}")
        
    def run_all_checks(self):
        """Run all functionality checks"""
        print("🔍 FUNCTIONALITY VERIFICATION")
        print("=" * 50)
        
        self.check_imports()
        self.check_files_exist()
        self.check_tests()
        self.check_executables()
        self.check_dependencies()
        self.check_data_integrity()
        self.check_config_files()
        
        self.generate_summary()
        
        print("\n" + "=" * 50)
        print("📊 SUMMARY")
        print(f"✅ Passed: {self.results['summary']['passed']}")
        print(f"⚠️ Warnings: {self.results['summary']['warnings']}")
        print(f"❌ Failed: {self.results['summary']['failed']}")
        
        self.save_results()
        
        # Return success if no failures
        return self.results['summary']['failed'] == 0

def compare_results(before_file, after_file):
    """Compare results before and after reorganization"""
    print("\n📊 COMPARING BEFORE/AFTER RESULTS")
    print("=" * 50)
    
    with open(before_file, 'r') as f:
        before = json.load(f)
        
    with open(after_file, 'r') as f:
        after = json.load(f)
        
    # Compare each check
    for check in before['checks']:
        before_result = before['checks'].get(check, 'N/A')
        after_result = after['checks'].get(check, 'N/A')
        
        if before_result != after_result:
            if after_result.startswith('MOVED:'):
                print(f"📦 {check}: {before_result} → {after_result}")
            elif before_result == 'PASS' and after_result.startswith('FAIL'):
                print(f"❌ {check}: BROKEN! Was {before_result}, now {after_result}")
            else:
                print(f"⚠️ {check}: {before_result} → {after_result}")
                
    print("\nSummary Comparison:")
    print(f"Before - Passed: {before['summary']['passed']}, Failed: {before['summary']['failed']}")
    print(f"After  - Passed: {after['summary']['passed']}, Failed: {after['summary']['failed']}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Verify functionality before/after reorganization')
    parser.add_argument('--compare', nargs=2, metavar=('BEFORE', 'AFTER'), 
                       help='Compare two result files')
    
    args = parser.parse_args()
    
    if args.compare:
        compare_results(args.compare[0], args.compare[1])
    else:
        verifier = FunctionalityVerifier()
        success = verifier.run_all_checks()
        
        if success:
            print("\n✅ All critical functionality verified!")
        else:
            print("\n⚠️ Some functionality issues detected!")
            print("Review the results file for details.")
            
        sys.exit(0 if success else 1)