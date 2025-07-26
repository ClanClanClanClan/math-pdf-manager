#!/usr/bin/env python3
"""
Test Configuration Migration
Verify that the new config system works with the old interface.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_config_migration():
    """Test the configuration migration."""
    print("🧪 Testing Configuration Migration")
    print("=" * 50)
    
    try:
        # Test 1: Load using new config manager directly
        print("\n1. Testing new ConfigManager:")
        from core.config_manager import get_config
        new_config = get_config()
        print(f"✓ Loaded config with {len(new_config.capitalization_whitelist)} mathematician names")
        print(f"✓ Base folder: {new_config.base_maths_folder}")
        
        # Test 2: Load using migration wrapper
        print("\n2. Testing migration wrapper:")
        from core.config.config_migration import ConfigurationData
        
        # Create mock args
        class MockArgs:
            exceptions_file = None
            debug = False
        
        args = MockArgs()
        script_dir = Path(__file__).parent
        
        # Load via old interface
        config_data = ConfigurationData()
        config_data.load_all(args, script_dir)
        
        print(f"✓ Config dict has {len(config_data.config)} keys")
        print(f"✓ Capitalization whitelist: {len(config_data.capitalization_whitelist)} items")
        print(f"✓ Known words: {len(config_data.known_words)} items")
        
        # Test 3: Verify compatibility
        print("\n3. Testing compatibility:")
        
        # Old interface methods
        base_folder = config_data.get('base_maths_folder')
        print(f"✓ get() method works: {base_folder}")
        
        # Check that lists are populated
        if config_data.capitalization_whitelist:
            sample = list(config_data.capitalization_whitelist)[:3]
            print(f"✓ Sample from whitelist: {sample}")
        
        print("\n✅ Configuration migration successful!")
        assert True, "Configuration migration successful"
        
    except Exception as e:
        print(f"\n❌ Configuration migration failed: {e}")
        import traceback
        traceback.print_exc()
        assert False, f"Configuration migration failed: {e}"


def test_process_files_compatibility():
    """Test that process_files still works with new config."""
    print("\n\n🧪 Testing process_files Compatibility")
    print("=" * 50)
    
    try:
        # This imports the function that uses ConfigurationData
        from processing.main_processing import verify_configuration
        from core.config.config_migration import ConfigurationData
        
        # Create mock config data
        config_data = ConfigurationData()
        
        # Mock args
        class MockArgs:
            exceptions_file = None
            debug = False
        
        args = MockArgs()
        config_data.load_all(args, Path.cwd())
        
        # Try to verify configuration (only needs config_data parameter)
        result = verify_configuration(config_data)
        print(f"✓ verify_configuration returned: {result}")
        print(f"✓ Result type: {type(result)}")
        
        print("\n✅ Process files compatibility confirmed!")
        assert True, "Process files compatibility confirmed"
        
    except Exception as e:
        print(f"\n❌ Process files compatibility failed: {e}")
        import traceback
        traceback.print_exc()
        assert False, f"Process files compatibility failed: {e}"


if __name__ == "__main__":
    success = test_config_migration()
    if success:
        test_process_files_compatibility()
    
    sys.exit(0 if success else 1)