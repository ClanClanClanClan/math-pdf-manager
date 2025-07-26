#!/usr/bin/env python3
"""
Authentication Manager for Academic Paper Downloads

Provides backward compatibility while using the new modular structure.
The core functionality has been extracted into src/auth/ modules.
"""

import os
import sys
import requests
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Add current directory to path
current_dir = Path(__file__).parent.resolve()
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Import everything from the new modular structure
from src.auth import *

# Backward compatibility for publisher configurations
PUBLISHER_AUTH_CONFIGS = {
    "ieee": AuthConfig(
        service_name="ieee",
        auth_method=AuthMethod.SHIBBOLETH,
        base_url="https://ieeexplore.ieee.org",
        shibboleth_idp="https://ieeexplore.ieee.org/servlet/wayf.jsp"
    ),
    "acm": AuthConfig(
        service_name="acm",
        auth_method=AuthMethod.SHIBBOLETH,
        base_url="https://dl.acm.org/",
        shibboleth_idp="https://dl.acm.org/action/ssostart"
    ),
    "springer": AuthConfig(
        service_name="springer",
        auth_method=AuthMethod.SHIBBOLETH,
        base_url="https://link.springer.com/",
        shibboleth_idp="https://link.springer.com/openurl"
    ),
    "elsevier": AuthConfig(
        service_name="elsevier",
        auth_method=AuthMethod.SHIBBOLETH,
        base_url="https://www.sciencedirect.com/",
        shibboleth_idp="https://www.sciencedirect.com/user/institution/login"
    ),
    "wiley": AuthConfig(
        service_name="wiley",
        auth_method=AuthMethod.SHIBBOLETH,
        base_url="https://onlinelibrary.wiley.com/",
        shibboleth_idp="https://onlinelibrary.wiley.com/action/ssostart"
    )
}

# Wrapper class for AuthManager to support legacy method signatures
class LegacyAuthManager(AuthManager):
    """Extended AuthManager with legacy method signatures."""
    
    def download_with_auth(self, url: str, service: str, dst_path: str, **kwargs) -> bool:
        """Legacy download method with different signature."""
        # Call parent's method with corrected order
        response = super().download_with_auth(service, url, **kwargs)
        if response:
            try:
                with open(dst_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                return True
            except Exception as e:
                logger.error(f"Failed to save file: {e}")
        return False

# Override AuthManager with the legacy version for backward compatibility
AuthManager = LegacyAuthManager

# Global auth manager instance for compatibility
_global_auth_manager = None

def get_auth_manager():
    """Get global authentication manager instance."""
    global _global_auth_manager
    if _global_auth_manager is None:
        _global_auth_manager = AuthManager()
    return _global_auth_manager

# Additional backward compatibility exports
globals().update(
    AuthMethod=AuthMethod,
    AuthConfig=AuthConfig,
    CredentialStore=CredentialStore,
    AuthManager=AuthManager,
    SessionInfo=SessionInfo,
    BasicAuthHandler=BasicAuthHandler,
    ApiKeyAuthHandler=ApiKeyAuthHandler,
    OAuthHandler=OAuthHandler,
    ShibbolethHandler=ShibbolethHandler,
    EZProxyHandler=EZProxyHandler,
    CookieAuthHandler=CookieAuthHandler,
    requests=requests,
    PUBLISHER_AUTH_CONFIGS=PUBLISHER_AUTH_CONFIGS,
    get_auth_manager=get_auth_manager,
)