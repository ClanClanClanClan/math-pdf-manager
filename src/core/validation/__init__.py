"""
Unified Validation System

All validation functionality consolidated into a single, coherent system.
This replaces multiple scattered validation modules throughout the project.

Usage:
    # New unified interface (recommended)
    from src.core.validation import UnifiedValidationService
    validator = UnifiedValidationService()
    
    # Legacy compatibility (deprecated but supported)
    from src.core.validation.compatibility import validate_cli_inputs
"""

from .unified_validator import UnifiedValidationService
from .interfaces import IValidationService

# Import compatibility layer for legacy code
from .compatibility import (
    # Legacy functions
    validate_cli_inputs,
    validate_template_dir,
    get_language,
    debug_print,
    enable_debug,
    disable_debug,
    is_debug_enabled,
    
    # Legacy classes  
    ValidationError,
    InputValidator,
    SecureFileHandler,
    UnifiedValidationService_Legacy
)

# Import comprehensive validator
try:
    from .comprehensive_validator import ComprehensiveUnifiedValidationService
except ImportError:
    # Fallback if comprehensive validator not available
    ComprehensiveUnifiedValidationService = UnifiedValidationService

__all__ = [
    # New unified system
    'UnifiedValidationService',
    'ComprehensiveUnifiedValidationService',
    'IValidationService',
    
    # Legacy compatibility (deprecated)
    'validate_cli_inputs',
    'validate_template_dir', 
    'get_language',
    'debug_print',
    'enable_debug',
    'disable_debug',
    'is_debug_enabled',
    'ValidationError',
    'InputValidator',
    'SecureFileHandler',
    'UnifiedValidationService_Legacy'
]