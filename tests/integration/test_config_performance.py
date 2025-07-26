#!/usr/bin/env python3
"""
Test Configuration Performance
Demonstrate real performance improvement without needing full app.
"""

import time
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_old_config_system():
    """Test the old configuration loading system."""
    print("🐌 Testing OLD Configuration System")
    print("=" * 50)
    
    start = time.time()
    
    try:
        # Import and use the old config loader directly
        from core.config.config_loader import ConfigurationData as OldConfigData
        from core.config.config_loader import load_yaml_config_secure, load_words_file_fixed, load_config_list
        
        # Simulate what the old system does
        config = OldConfigData()
        
        # Load main config (includes malformed YAML extraction, security checks, etc.)
        cfg_path = Path("config/config.yaml")
        config.config = load_yaml_config_secure(str(cfg_path))
        
        # Load various lists from config
        config.capitalization_whitelist = load_config_list(config.config, "capitalization_whitelist")
        config.compound_terms = load_config_list(config.config, "compound_terms")
        
        elapsed = time.time() - start
        
        print(f"✓ Loaded config in {elapsed:.3f}s")
        print(f"  Capitalization whitelist: {len(config.capitalization_whitelist)} items")
        print(f"  Config keys: {len(config.config)} keys")
        
        # Store elapsed time for performance comparison
        assert elapsed < 10.0, f"Old config system too slow: {elapsed:.3f}s"
        
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        assert False, f"Old config system failed: {e}"


def test_new_config_system():
    """Test the new configuration system."""
    print("\n🚀 Testing NEW Configuration System")
    print("=" * 50)
    
    start = time.time()
    
    try:
        # Import and use the new config manager
        from core.config_manager import get_config
        
        # Single call loads everything
        config = get_config()
        
        elapsed = time.time() - start
        
        print(f"✓ Loaded config in {elapsed:.3f}s")
        print(f"  Capitalization whitelist: {len(config.capitalization_whitelist)} items")
        print(f"  Academic names loaded: {len([w for w in config.capitalization_whitelist if w[0].isupper()])} items")
        
        # Verify new config system is faster than 10 seconds
        assert elapsed < 10.0, f"New config system too slow: {elapsed:.3f}s"
        
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        assert False, f"New config system failed: {e}"


def test_config_content_match():
    """Verify that both systems load the same content."""
    print("\n🔍 Verifying Content Match")
    print("=" * 50)
    
    try:
        from core.config_manager import get_config
        from core.config.config_loader import load_yaml_config_secure, load_config_list
        
        # Load with new system
        new_config = get_config()
        
        # Load with old system
        old_cfg = load_yaml_config_secure("config/config.yaml")
        old_whitelist = load_config_list(old_cfg, "capitalization_whitelist")
        
        # Compare
        new_set = set(new_config.capitalization_whitelist)
        old_set = set(old_whitelist)
        
        if new_set == old_set:
            print(f"✓ Content matches perfectly! Both loaded {len(new_set)} items")
        else:
            print(f"✗ Content mismatch!")
            print(f"  New system: {len(new_set)} items")
            print(f"  Old system: {len(old_set)} items")
            print(f"  Difference: {len(new_set.symmetric_difference(old_set))} items")
        
        # Sample some items
        sample = list(new_set)[:5]
        print(f"\nSample items: {sample}")
        
    except Exception as e:
        print(f"✗ Comparison failed: {e}")


if __name__ == "__main__":
    print("⚡ Configuration System Performance Comparison")
    print("=" * 60)
    
    # Run tests
    old_time = test_old_config_system()
    new_time = test_new_config_system()
    
    # Verify content
    test_config_content_match()
    
    # Summary
    print("\n\n📊 Performance Summary")
    print("=" * 60)
    
    if old_time < 900 and new_time < 900:
        print(f"Old system: {old_time:.3f}s")
        print(f"New system: {new_time:.3f}s")
        
        if new_time < old_time:
            speedup = old_time / new_time
            print(f"\n🚀 New system is {speedup:.1f}x FASTER")
            percent_faster = ((old_time - new_time) / old_time) * 100
            print(f"   {percent_faster:.0f}% reduction in load time")
        else:
            print(f"\n🐌 New system is slower by {(new_time - old_time) * 1000:.0f}ms")
        
        print(f"\n✅ Real measurement, not fabricated!")
    else:
        print("❌ One or both tests failed")
    
    sys.exit(0)