"""
Utils package for Math-PDF Manager

This package contains utility modules for the Math-PDF Manager.
Note: This also re-exports functions from the original utils.py for compatibility.
"""
import sys
from pathlib import Path

# Add the parent directory to sys.path to import from utils.py
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Import functions from original utils.py
try:
    # Import the original utils module under a different name to avoid conflicts
    import importlib.util
    import sys
    
    # Temporarily modify sys.modules to avoid the __dict__ issue
    original_modules = sys.modules.copy()
    
    spec = importlib.util.spec_from_file_location("original_utils", parent_dir / "utils.py")
    original_utils = importlib.util.module_from_spec(spec)
    
    # Set the module in sys.modules before execution
    sys.modules["original_utils"] = original_utils
    spec.loader.exec_module(original_utils)
    
    # Re-export ALL functions from original utils.py
    # Get all the exported names from the original module
    if hasattr(original_utils, '__all__'):
        for name in original_utils.__all__:
            if hasattr(original_utils, name):
                globals()[name] = getattr(original_utils, name)
    else:
        # Fallback: export all non-private attributes
        for name in dir(original_utils):
            if not name.startswith('_'):
                globals()[name] = getattr(original_utils, name)
    
    _original_utils_available = True
except Exception as e:
    print(f"Utils import failed: {e}")
    _original_utils_available = False
    
    # Import directly using yaml for load_yaml_config
    import yaml
    def load_yaml_config(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}
    
    def canonicalize(text):
        return text.lower()
    def is_canonically_equivalent(a, b):
        return a == b

# Make security utilities available
try:
    from .security import PathValidator, SecureXMLParser
    _security_available = True
except ImportError:
    _security_available = False
    PathValidator = None
    SecureXMLParser = None

# Import utilities from validators package (modern approach)
try:
    from validators import ValidationResult, check_filename as validator_check_filename  # noqa: F401
    from src.validators.filename_checker import check_filename as fc_check_filename  # noqa: F401
    
    print("✅ Utils package: imported modern validator functions")
    
except Exception as e:
    print(f"⚠️ Utils package: modern import failed: {e}")

# Define what's available for import - include everything that doesn't start with _
__all__ = [name for name in globals().keys() if not name.startswith('_') and name not in ['Path', 'sys']]

if _security_available:
    __all__.extend(['PathValidator', 'SecureXMLParser'])