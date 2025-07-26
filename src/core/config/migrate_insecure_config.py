#!/usr/bin/env python3
"""
Migration Script: Replace Insecure Configuration Patterns
Demonstrates how to replace insecure configuration patterns with secure alternatives.
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple

# Add current directory to path
current_dir = Path(__file__).parent.resolve()
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))
    
    # Import after path modification
    from core.config.secure_config import get_config_manager
else:
    from core.config.secure_config import get_config_manager

def demonstrate_insecure_patterns():
    """Show examples of insecure patterns that need to be replaced."""
    
    print("🔴 INSECURE PATTERNS TO REPLACE:")
    print("=" * 50)
    
    # Example 1: Hardcoded defaults with environment variables
    print("\n1. Hardcoded defaults with environment variables:")
    print("   ❌ INSECURE:")
    print('   api_key = os.environ.get("API_KEY", "default_key")')
    print('   password = os.environ.get("PASSWORD", "your_password")')
    print()
    print("   ✅ SECURE:")
    print('   api_key = get_required_config("api_key")')
    print('   password = get_secure_credential("password")')
    
    # Example 2: Direct hardcoded values
    print("\n2. Direct hardcoded values:")
    print("   ❌ INSECURE:")
    print('   API_KEY = "hardcoded_key_123"')
    print('   DATABASE_URL = "postgresql://user:pass@localhost/db"')
    print()
    print("   ✅ SECURE:")
    print('   API_KEY = get_required_config("api_key")')
    print('   DATABASE_URL = get_required_config("database_url")')
    
    # Example 3: Configuration without validation
    print("\n3. Configuration without validation:")
    print("   ❌ INSECURE:")
    print('   timeout = int(os.environ.get("TIMEOUT", "30"))')
    print('   debug = os.environ.get("DEBUG", "false").lower() == "true"')
    print()
    print("   ✅ SECURE:")
    print('   timeout = get_config("request_timeout", 30)')
    print('   debug = get_config("debug_mode", False)')

def demonstrate_secure_patterns():
    """Show examples of secure configuration patterns."""
    
    print("\n🟢 SECURE PATTERNS TO USE:")
    print("=" * 50)
    
    get_config_manager()
    
    # Example 1: Required configuration
    print("\n1. Required configuration (fails if not set):")
    print("   try:")
    print('       api_key = get_required_config("api_key")')
    print("   except ConfigurationError as e:")
    print("       logger.error(f'Configuration error: {e}')")
    print("       sys.exit(1)")
    
    # Example 2: Optional configuration with safe defaults
    print("\n2. Optional configuration with safe defaults:")
    print('   cache_size = get_config("cache_size", 1000)')
    print('   debug_mode = get_config("debug_mode", False)')
    print('   log_level = get_config("log_level", "INFO")')
    
    # Example 3: Secure credential handling
    print("\n3. Secure credential handling:")
    print('   eth_username = get_secure_credential("eth_username")')
    print('   eth_password = get_secure_credential("eth_password")')
    print('   if not eth_username or not eth_password:')
    print('       logger.error("ETH credentials not configured")')
    print('       return False')
    
    # Example 4: Configuration validation
    print("\n4. Configuration validation:")
    print('   errors = config_manager.validate_all()')
    print('   if errors:')
    print('       for error in errors:')
    print('           logger.error(f"Config error: {error}")')
    print('       sys.exit(1)')

def find_insecure_patterns() -> List[Tuple[str, str, str]]:
    """Find insecure configuration patterns in the codebase."""
    
    insecure_patterns = []
    
    # Patterns to look for
    patterns = [
        (r'os\.environ\.get\(["\']([^"\']+)["\'],\s*["\']([^"\']+)["\']', 
         'Environment variable with hardcoded default'),
        (r'os\.getenv\(["\']([^"\']+)["\'],\s*["\']([^"\']+)["\']', 
         'Environment variable with hardcoded default'),
        (r'([A-Z_]+)\s*=\s*["\']([^"\']{10,})["\']', 
         'Hardcoded credential or key'),
        (r'password\s*=\s*["\']([^"\']+)["\']', 
         'Hardcoded password'),
        (r'api_key\s*=\s*["\']([^"\']+)["\']', 
         'Hardcoded API key'),
        (r'secret\s*=\s*["\']([^"\']+)["\']', 
         'Hardcoded secret'),
    ]
    
    # Search through Python files
    for py_file in Path('.').glob('**/*.py'):
        if py_file.is_file() and not str(py_file).startswith('./_archive'):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for pattern, description in patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        insecure_patterns.append((
                            str(py_file),
                            match.group(0),
                            description
                        ))
            except Exception as e:
                print(f"Error reading {py_file}: {e}")
    
    return insecure_patterns

def create_migration_examples():
    """Create examples of how to migrate specific patterns."""
    
    print("\n🔄 MIGRATION EXAMPLES:")
    print("=" * 50)
    
    examples = [
        {
            'description': 'ETH Authentication',
            'before': '''
# INSECURE
eth_username = os.environ.get("ETH_USERNAME", "your_username")
eth_password = os.environ.get("ETH_PASSWORD", "your_password")
''',
            'after': '''
# SECURE
from core.config.secure_config import get_secure_credential

eth_username = get_secure_credential("eth_username")
eth_password = get_secure_credential("eth_password")

if not eth_username or not eth_password:
    logger.error("ETH credentials not configured")
    raise ConfigurationError("ETH credentials required")
'''
        },
        {
            'description': 'API Configuration',
            'before': '''
# INSECURE
API_KEY = os.environ.get("API_KEY", "default_api_key")
API_URL = "https://api.example.com"
TIMEOUT = int(os.environ.get("TIMEOUT", "30"))
''',
            'after': '''
# SECURE
from core.config.secure_config import get_required_config, get_config

API_KEY = get_required_config("api_key")
API_URL = get_config("api_url", "https://api.example.com")
TIMEOUT = get_config("request_timeout", 30)
'''
        },
        {
            'description': 'Database Configuration',
            'before': '''
# INSECURE
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://user:pass@localhost/db")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "default_password")
''',
            'after': '''
# SECURE
from core.config.secure_config import get_required_config

DATABASE_URL = get_required_config("database_url")
DB_PASSWORD = get_secure_credential("database_password")
'''
        }
    ]
    
    for example in examples:
        print(f"\n{example['description']}:")
        print(f"{'':>2}❌ BEFORE:{example['before']}")
        print(f"{'':>2}✅ AFTER:{example['after']}")

def test_secure_configuration():
    """Test the secure configuration system."""
    
    print("\n🧪 TESTING SECURE CONFIGURATION:")
    print("=" * 50)
    
    config_manager = get_config_manager()
    
    # Test 1: Configuration summary
    print("\n1. Configuration Summary:")
    summary = config_manager.get_config_summary()
    for key, info in list(summary.items())[:5]:  # Show first 5
        print(f"   {key}: {info['value']} (security: {info['security_level']})")
    
    # Test 2: Validation
    print("\n2. Configuration Validation:")
    errors = config_manager.validate_all()
    if errors:
        print("   ❌ Validation errors found:")
        for error in errors[:3]:  # Show first 3
            print(f"     - {error}")
    else:
        print("   ✅ No validation errors")
    
    # Test 3: Secure credential test
    print("\n3. Secure Credential Access:")
    test_credential = config_manager.get_secure_credential("eth_username")
    if test_credential:
        print(f"   ✅ Credential found: {test_credential[:3]}***")
    else:
        print("   ℹ️  No credential configured (expected for testing)")

def main():
    """Main function to demonstrate secure configuration migration."""
    
    print("🔐 SECURE CONFIGURATION MIGRATION GUIDE")
    print("=" * 60)
    
    demonstrate_insecure_patterns()
    demonstrate_secure_patterns()
    create_migration_examples()
    test_secure_configuration()
    
    print("\n📋 NEXT STEPS:")
    print("=" * 50)
    print("1. Replace insecure patterns with secure alternatives")
    print("2. Update configuration files to use secure definitions")
    print("3. Test configuration validation")
    print("4. Set up secure credential storage")
    print("5. Run security audit to verify improvements")
    
    print("\n🎯 PRIORITY FILES TO UPDATE:")
    print("=" * 50)
    
    # Show files that need updating
    priority_files = [
        "automated_eth_setup.py",
        "core/security/vulnerability_scanner.py", 
        "secure_credential_manager.py",
        "main.py",
        "auth_manager.py"
    ]
    
    for file in priority_files:
        if Path(file).exists():
            print(f"   ✅ {file}")
        else:
            print(f"   ❓ {file} (not found)")

if __name__ == "__main__":
    main()