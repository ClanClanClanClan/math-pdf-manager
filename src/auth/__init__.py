"""
Authentication Module

Modular authentication system for academic paper downloads.
Extracted from auth_manager.py for better organization.

Components:
- models: Authentication data models and enums
- store: Secure credential storage
- manager: Main authentication management
- methods: Authentication method implementations
"""

# Core models and enums
from .models import (
    AuthMethod,
    AuthConfig,
    SessionInfo,
)

# Credential storage
from .store import CredentialStore

# Main authentication manager
from .manager import AuthManager

# Authentication methods
from .methods import (
    BasicAuthHandler,
    ApiKeyAuthHandler,
    OAuthHandler,
    ShibbolethHandler,
    EZProxyHandler,
    CookieAuthHandler,
)

__all__ = [
    # Models
    'AuthMethod',
    'AuthConfig', 
    'SessionInfo',
    
    # Storage
    'CredentialStore',
    
    # Manager
    'AuthManager',
    
    # Methods
    'BasicAuthHandler',
    'ApiKeyAuthHandler', 
    'OAuthHandler',
    'ShibbolethHandler',
    'EZProxyHandler',
    'CookieAuthHandler',
]