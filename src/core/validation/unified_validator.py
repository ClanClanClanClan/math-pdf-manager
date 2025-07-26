# This file now imports from the comprehensive validator
from .comprehensive_validator import ComprehensiveUnifiedValidationService

# Maintain backward compatibility
UnifiedValidationService = ComprehensiveUnifiedValidationService

__all__ = ['UnifiedValidationService', 'ComprehensiveUnifiedValidationService']
