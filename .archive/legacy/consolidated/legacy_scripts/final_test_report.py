#!/usr/bin/env python3
"""
Final comprehensive test report for the Math-PDF manager system
"""
import sys
import os
import traceback
from pathlib import Path
import importlib.util

# Add current directory to path
sys.path.insert(0, os.getcwd())

class TestResult:
    def __init__(self, name, success, message, details=None):
        self.name = name
        self.success = success
        self.message = message
        self.details = details or []

class SystemTester:
    def __init__(self):
        self.results = []
        self.issues = []
        self.fixes = []
    
    def add_result(self, name, success, message, details=None):
        result = TestResult(name, success, message, details)
        self.results.append(result)
        if not success:
            self.issues.append(result)
    
    def test_dependencies(self):
        """Test if all required dependencies are available."""
        critical_imports = [
            ('yaml', 'PyYAML'),
            ('pathlib', 'Built-in'),
            ('argparse', 'Built-in'),
            ('logging', 'Built-in'),
            ('json', 'Built-in'),
            ('unicodedata', 'Built-in'),
            ('typing', 'Built-in'),
            ('abc', 'Built-in'),
            ('functools', 'Built-in'),
            ('inspect', 'Built-in'),
            ('dataclasses', 'Built-in'),
            ('time', 'Built-in'),
        ]
        
        optional_imports = [
            ('cryptography', 'cryptography'),
            ('jinja2', 'jinja2'),
            ('tqdm', 'tqdm'),
        ]
        
        missing_critical = []
        missing_optional = []
        
        for module, package in critical_imports:
            try:
                __import__(module)
            except ImportError:
                missing_critical.append((module, package))
        
        for module, package in optional_imports:
            try:
                __import__(module)
            except ImportError:
                missing_optional.append((module, package))
        
        if missing_critical:
            self.add_result(
                "Critical Dependencies",
                False,
                f"Missing {len(missing_critical)} critical dependencies",
                [f"{module} ({package})" for module, package in missing_critical]
            )
            self.fixes.append(f"Install missing packages: pip install {' '.join(pkg for _, pkg in missing_critical)}")
        else:
            self.add_result("Critical Dependencies", True, "All critical dependencies available")
        
        if missing_optional:
            self.add_result(
                "Optional Dependencies",
                False,
                f"Missing {len(missing_optional)} optional dependencies",
                [f"{module} ({package})" for module, package in missing_optional]
            )
            self.fixes.append(f"Install optional packages: pip install {' '.join(pkg for _, pkg in missing_optional)}")
        else:
            self.add_result("Optional Dependencies", True, "All optional dependencies available")
    
    def test_file_structure(self):
        """Test if required files exist."""
        required_files = [
            'main.py',
            'main_processing.py',
            'config_loader.py',
            'service_registry.py',
            'constants.py',
            'core/dependency_injection/__init__.py',
            'core/dependency_injection/interfaces.py',
            'core/dependency_injection/container.py',
            'core/dependency_injection/implementations.py',
            'core/config/secure_config.py',
        ]
        
        missing_files = []
        for file in required_files:
            if not Path(file).exists():
                missing_files.append(file)
        
        if missing_files:
            self.add_result(
                "File Structure",
                False,
                f"Missing {len(missing_files)} required files",
                missing_files
            )
            self.fixes.append("Ensure all required files are present in the correct directories")
        else:
            self.add_result("File Structure", True, "All required files present")
    
    def test_imports(self):
        """Test if modules can be imported."""
        import_tests = [
            ("Core interfaces", "from core.dependency_injection.interfaces import ILoggingService"),
            ("Secure config", "from core.config.secure_config import SecureConfigManager"),
            ("DI container", "from core.dependency_injection.container import DIContainer"),
            ("Service registry", "from service_registry import get_service_registry"),
            ("Config loader", "from config_loader import ConfigurationData"),
            ("Constants", "from constants import DEFAULT_HTML_OUTPUT"),
            ("Main module", "from main import main"),
        ]
        
        failed_imports = []
        for name, import_stmt in import_tests:
            try:
                exec(import_stmt)
            except Exception as e:
                failed_imports.append((name, str(e)))
        
        if failed_imports:
            self.add_result(
                "Module Imports",
                False,
                f"Failed to import {len(failed_imports)} modules",
                [f"{name}: {error}" for name, error in failed_imports]
            )
            self.fixes.append("Fix import errors by checking module dependencies and circular imports")
        else:
            self.add_result("Module Imports", True, "All modules imported successfully")
    
    def test_help_flag(self):
        """Test the --help flag."""
        try:
            from main import main
            try:
                main(['--help'])
                self.add_result("Help Flag", False, "Help should have exited with SystemExit")
            except SystemExit as e:
                if e.code == 0:
                    self.add_result("Help Flag", True, "Help flag works correctly")
                else:
                    self.add_result("Help Flag", False, f"Help exited with code {e.code}")
            except Exception as e:
                self.add_result("Help Flag", False, f"Help failed: {e}")
        except Exception as e:
            self.add_result("Help Flag", False, f"Cannot import main: {e}")
    
    def test_dry_run(self):
        """Test dry run mode."""
        try:
            from main import main
            
            # Create test directory and file
            test_dir = Path("test_dry_run_temp")
            test_dir.mkdir(exist_ok=True)
            test_file = test_dir / "Test Author - Sample Paper.pdf"
            test_file.touch()
            
            try:
                main([str(test_dir), '--dry_run'])
                self.add_result("Dry Run", True, "Dry run completed successfully")
            except Exception as e:
                self.add_result("Dry Run", False, f"Dry run failed: {e}")
            finally:
                # Clean up
                test_file.unlink(missing_ok=True)
                test_dir.rmdir()
        except Exception as e:
            self.add_result("Dry Run", False, f"Cannot test dry run: {e}")
    
    def test_dependency_injection(self):
        """Test the dependency injection framework."""
        try:
            from core.dependency_injection import setup_default_services, get_container
            from service_registry import get_service_registry
            
            # Test service setup
            setup_default_services()
            container = get_container()
            registry = get_service_registry()
            registry.initialize()
            
            # Test service resolution
            logging_service = registry.logging_service
            logging_service.info("Test message")
            
            self.add_result("Dependency Injection", True, "DI framework working correctly")
        except Exception as e:
            self.add_result("Dependency Injection", False, f"DI framework failed: {e}")
    
    def run_all_tests(self):
        """Run all tests and generate report."""
        print("Math-PDF Manager System Test Report")
        print("=" * 60)
        
        tests = [
            ("Checking dependencies", self.test_dependencies),
            ("Checking file structure", self.test_file_structure),
            ("Testing imports", self.test_imports),
            ("Testing help flag", self.test_help_flag),
            ("Testing dry run", self.test_dry_run),
            ("Testing dependency injection", self.test_dependency_injection),
        ]
        
        for test_name, test_func in tests:
            print(f"\n{test_name}...")
            try:
                test_func()
            except Exception as e:
                self.add_result(test_name, False, f"Test crashed: {e}")
                traceback.print_exc()
    
    def generate_report(self):
        """Generate final test report."""
        print(f"\n{'='*60}")
        print("TEST RESULTS")
        print(f"{'='*60}")
        
        passed = sum(1 for r in self.results if r.success)
        failed = sum(1 for r in self.results if not r.success)
        
        for result in self.results:
            status = "✓" if result.success else "✗"
            print(f"{status} {result.name}: {result.message}")
            if result.details:
                for detail in result.details:
                    print(f"    - {detail}")
        
        print(f"\nSUMMARY: {passed} passed, {failed} failed")
        
        if self.issues:
            print(f"\n{'='*60}")
            print("ISSUES FOUND")
            print(f"{'='*60}")
            for issue in self.issues:
                print(f"• {issue.name}: {issue.message}")
                if issue.details:
                    for detail in issue.details:
                        print(f"  - {detail}")
        
        if self.fixes:
            print(f"\n{'='*60}")
            print("SUGGESTED FIXES")
            print(f"{'='*60}")
            for i, fix in enumerate(self.fixes, 1):
                print(f"{i}. {fix}")
        
        if failed == 0:
            print(f"\n{'='*60}")
            print("🎉 ALL TESTS PASSED!")
            print("The Math-PDF manager system is working correctly.")
            print("\nYou can now run:")
            print("  python main.py --help")
            print("  python main.py /path/to/directory --dry_run")
        else:
            print(f"\n{'='*60}")
            print(f"⚠️  SYSTEM NEEDS ATTENTION ({failed} issues)")
            print("Please address the issues above before using the system.")
        
        return failed == 0

def main():
    """Run the comprehensive test."""
    tester = SystemTester()
    tester.run_all_tests()
    success = tester.generate_report()
    return success

if __name__ == "__main__":
    sys.exit(0 if main() else 1)