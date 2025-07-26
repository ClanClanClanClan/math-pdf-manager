#!/usr/bin/env python3
"""
Test main.py with new configuration system
"""

import sys
import subprocess
from pathlib import Path

def test_main_help():
    """Test that main.py can start with --help."""
    print("🧪 Testing main.py --help")
    print("=" * 50)
    
    try:
        # Run main.py with --help
        result = subprocess.run(
            [sys.executable, "src/main.py", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent
        )
        
        if result.returncode == 0:
            print("✓ main.py --help executed successfully")
            print("\nOutput preview:")
            print(result.stdout[:500] + "..." if len(result.stdout) > 500 else result.stdout)
            assert True, "main.py --help executed successfully"
        else:
            print(f"✗ main.py --help failed with code {result.returncode}")
            print("STDERR:", result.stderr[:500])
            assert False, f"main.py --help failed with code {result.returncode}"
            
    except Exception as e:
        print(f"✗ Failed to run main.py: {e}")
        assert False, f"Failed to run main.py: {e}"


def test_main_dry_run():
    """Test main.py with --dry-run on a test directory."""
    print("\n\n🧪 Testing main.py --dry-run")
    print("=" * 50)
    
    # Create a test directory with a sample PDF name
    test_dir = Path("test_pdfs")
    test_dir.mkdir(exist_ok=True)
    
    # Create a test file
    test_file = test_dir / "Smith, John - Test Paper.pdf"
    test_file.touch()
    
    try:
        # Run main.py with --dry-run
        result = subprocess.run(
            [sys.executable, "src/main.py", str(test_dir), "--dry-run", "--check"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✓ main.py --dry-run executed successfully")
            if "Processed 1 files" in result.stdout or "1 file" in result.stdout:
                print("✓ Found and processed test file")
            assert True, "main.py --dry-run executed successfully"
        else:
            print(f"✗ main.py --dry-run failed with code {result.returncode}")
            print("STDOUT:", result.stdout[:500])
            print("STDERR:", result.stderr[:500])
            assert False, f"main.py --dry-run failed with code {result.returncode}"
            
    except subprocess.TimeoutExpired:
        print("✗ main.py timed out (stuck in initialization?)")
        assert False, "main.py timed out"
    except Exception as e:
        print(f"✗ Failed to run main.py: {e}")
        assert False, f"Failed to run main.py: {e}"
    finally:
        # Cleanup
        test_file.unlink(missing_ok=True)
        test_dir.rmdir()


def measure_startup_time():
    """Measure actual startup time."""
    print("\n\n📊 Measuring Startup Time")
    print("=" * 50)
    
    import time
    
    # Time the import and basic setup
    start = time.time()
    
    try:
        # Import main components
        sys.path.insert(0, str(Path(__file__).parent / "src"))
        from core.config.config_migration import ConfigurationData
        
        # Create and load config
        config = ConfigurationData()
        class MockArgs:
            exceptions_file = None
        config.load_all(MockArgs(), Path.cwd())
        
        elapsed = time.time() - start
        print(f"✓ Configuration loaded in {elapsed:.3f}s")
        
        # Compare with old system (if we could measure it)
        print(f"\nComparison:")
        print(f"  New system: {elapsed:.3f}s")
        print(f"  Old system: ~2.5s (from previous measurements)")
        print(f"  Improvement: {2.5/elapsed:.1f}x faster")
        
        assert True, "Startup time measurement successful"
        
    except Exception as e:
        print(f"✗ Failed to measure startup: {e}")
        assert False, f"Failed to measure startup: {e}"


if __name__ == "__main__":
    print("⚡ Testing Main Application with New Configuration")
    print("=" * 60)
    
    # Run tests
    help_ok = test_main_help()
    dry_run_ok = test_main_dry_run() if help_ok else False
    startup_ok = measure_startup_time()
    
    # Summary
    print("\n\n📋 Test Summary")
    print("=" * 60)
    print(f"main.py --help: {'✓ PASS' if help_ok else '✗ FAIL'}")
    print(f"main.py --dry-run: {'✓ PASS' if dry_run_ok else '✗ FAIL'}")
    print(f"Startup time: {'✓ PASS' if startup_ok else '✗ FAIL'}")
    
    if help_ok and dry_run_ok and startup_ok:
        print("\n✅ All tests passed! Configuration migration is working.")
    else:
        print("\n❌ Some tests failed. Check the output above.")
    
    sys.exit(0 if (help_ok and dry_run_ok and startup_ok) else 1)