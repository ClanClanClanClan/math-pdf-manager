"""
Authentication Models

Data models and enums for authentication system.
Extracted from auth_manager.py for better modularity.
"""

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime


class AuthMethod(Enum):
    """Supported authentication methods."""

    API_KEY = "api_key"
    BASIC_AUTH = "basic_auth"
    OAUTH = "oauth"
    SHIBBOLETH = "shibboleth"
    EZPROXY = "ezproxy"
    COOKIE = "cookie"
    CUSTOM = "custom"


@dataclass
class AuthConfig:
    """Authentication configuration for a service."""

    service_name: str
    auth_method: AuthMethod
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    oauth_client_id: Optional[str] = None
    oauth_client_secret: Optional[str] = None
    oauth_token_url: Optional[str] = None
    shibboleth_idp: Optional[str] = None
    ezproxy_url: Optional[str] = None
    custom_auth_handler: Optional[str] = None
    cookies: Optional[Dict[str, str]] = None
    headers: Optional[Dict[str, str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding sensitive data."""
        data = asdict(self)
        # Remove sensitive fields
        for field in ["password", "api_key", "oauth_client_secret", "cookies"]:
            if field in data:
                data[field] = "***" if data[field] else None
        data["auth_method"] = self.auth_method.value
        return data


@dataclass
class SessionInfo:
    """Information about an authenticated session."""
    
    service: str
    username: Optional[str] = None
    expires_at: Optional[datetime] = None
    is_valid: bool = True
    session_data: Optional[Dict[str, Any]] = None
    
    def is_expired(self) -> bool:
        """Check if session is expired."""
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at