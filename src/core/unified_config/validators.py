#!/usr/bin/env python3
"""
Unified Configuration System - Validator

Provides validation for configuration values based on schemas.
"""

import re
import ipaddress
from typing import Any, List
from urllib.parse import urlparse

from .interfaces import IConfigValidator, ConfigSchema


class ConfigValidator(IConfigValidator):
    """Configuration validator with comprehensive validation rules."""
    
    def __init__(self):
        self.errors: List[str] = []
    
    def validate(self, config_value, schema: ConfigSchema) -> bool:
        """Validate a configuration value against its schema."""
        self.errors.clear()
        
        key = config_value.key
        value = config_value.value
        
        # Type validation
        if not self._validate_type(value, schema.type):
            self.errors.append(f"{key}: Expected {schema.type.__name__}, got {type(value).__name__}")
            return False
        
        # Custom validation rules
        if schema.validation_rules:
            if not self._validate_rules(key, value, schema.validation_rules):
                return False
        
        return len(self.errors) == 0
    
    def get_validation_errors(self) -> List[str]:
        """Get validation errors from last validation."""
        return self.errors.copy()
    
    def _validate_type(self, value: Any, expected_type: type) -> bool:
        """Validate value type."""
        if expected_type == str:
            return isinstance(value, str)
        elif expected_type == int:
            return isinstance(value, int) or (isinstance(value, str) and value.isdigit())
        elif expected_type == float:
            return isinstance(value, (int, float)) or (isinstance(value, str) and self._is_number(value))
        elif expected_type == bool:
            return isinstance(value, bool) or value in ['true', 'false', '1', '0', 'yes', 'no']
        elif expected_type == list:
            return isinstance(value, list)
        elif expected_type == dict:
            return isinstance(value, dict)
        
        return True
    
    def _validate_rules(self, key: str, value: Any, rules: dict) -> bool:
        """Validate value against custom rules."""
        
        # String validation
        if isinstance(value, str):
            if 'min_length' in rules and len(value) < rules['min_length']:
                self.errors.append(f"{key}: String too short (min: {rules['min_length']})")
                return False
            
            if 'max_length' in rules and len(value) > rules['max_length']:
                self.errors.append(f"{key}: String too long (max: {rules['max_length']})")
                return False
            
            if 'pattern' in rules:
                pattern = re.compile(rules['pattern'])
                if not pattern.match(value):
                    self.errors.append(f"{key}: Does not match required pattern")
                    return False
            
            if 'format' in rules:
                if not self._validate_format(key, value, rules['format']):
                    return False
        
        # Numeric validation
        if isinstance(value, (int, float)):
            if 'min_value' in rules and value < rules['min_value']:
                self.errors.append(f"{key}: Value too small (min: {rules['min_value']})")
                return False
            
            if 'max_value' in rules and value > rules['max_value']:
                self.errors.append(f"{key}: Value too large (max: {rules['max_value']})")
                return False
        
        # List validation
        if isinstance(value, list):
            if 'min_items' in rules and len(value) < rules['min_items']:
                self.errors.append(f"{key}: Too few items (min: {rules['min_items']})")
                return False
            
            if 'max_items' in rules and len(value) > rules['max_items']:
                self.errors.append(f"{key}: Too many items (max: {rules['max_items']})")
                return False
        
        # Choice validation
        if 'choices' in rules and value not in rules['choices']:
            self.errors.append(f"{key}: Invalid choice. Must be one of: {rules['choices']}")
            return False
        
        return True
    
    def _validate_format(self, key: str, value: str, format_type: str) -> bool:
        """Validate string format."""
        
        if format_type == 'email':
            pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
            if not pattern.match(value):
                self.errors.append(f"{key}: Invalid email format")
                return False
        
        elif format_type == 'url':
            try:
                result = urlparse(value)
                if not all([result.scheme, result.netloc]):
                    raise ValueError()
            except (ValueError, AttributeError):
                self.errors.append(f"{key}: Invalid URL format")
                return False
        
        elif format_type == 'ip':
            try:
                ipaddress.ip_address(value)
            except ValueError:
                self.errors.append(f"{key}: Invalid IP address")
                return False
        
        elif format_type == 'path':
            from pathlib import Path
            try:
                Path(value)
            except (ValueError, TypeError, OSError):
                self.errors.append(f"{key}: Invalid path format")
                return False
        
        elif format_type == 'api_key':
            # Basic API key validation (alphanumeric, reasonable length)
            if not re.match(r'^[a-zA-Z0-9_-]{16,128}$', value):
                self.errors.append(f"{key}: Invalid API key format")
                return False
        
        return True
    
    def _is_number(self, value: str) -> bool:
        """Check if string represents a number."""
        try:
            float(value)
            return True
        except ValueError:
            return False
