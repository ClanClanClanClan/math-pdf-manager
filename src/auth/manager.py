"""
Authentication Manager

Main authentication management system.
Extracted from auth_manager.py for better modularity.
"""

import json
import logging
import requests
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from .models import AuthConfig, AuthMethod, SessionInfo
from .store import CredentialStore
from .methods import AUTH_HANDLERS

logger = logging.getLogger(__name__)

# Import secure credential manager
try:
    from secure_credential_manager import get_credential_manager
    SECURE_CREDS_AVAILABLE = True
except ImportError:
    SECURE_CREDS_AVAILABLE = False

# Browser automation imports
try:
    from playwright.sync_api import BrowserContext
    # Other imports available but not directly used - for future features
    import importlib.util
    _sync_playwright_spec = importlib.util.find_spec('playwright.sync_api')
    PLAYWRIGHT_AVAILABLE = _sync_playwright_spec is not None
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    BrowserContext = None


class AuthManager:
    """Main authentication manager."""

    def __init__(self):
        # Always create a CredentialStore for backward compatibility
        try:
            self.store = CredentialStore()
        except Exception as e:
            logger.warning(f"Failed to initialize credential store: {e}")
            self.store = None

        # Use secure credential manager if available
        if SECURE_CREDS_AVAILABLE:
            try:
                self.credential_manager = get_credential_manager()
            except Exception as e:
                logger.warning(f"Failed to initialize secure credential manager: {e}")
                self.credential_manager = None
        else:
            self.credential_manager = None

        self.configs: Dict[str, AuthConfig] = {}
        self.sessions: Dict[str, requests.Session] = {}
        self.session_info: Dict[str, SessionInfo] = {}
        self.browser_contexts: Dict[str, Any] = {}  # BrowserContext when available
        self._load_configs()

    def _load_configs(self):
        """Load authentication configurations."""
        if self.store:
            config_file = self.store.config_file
        else:
            config_file = Path.home() / ".academic_papers" / "auth" / "auth_config.json"
            config_file.parent.mkdir(parents=True, exist_ok=True)

        if config_file.exists():
            try:
                with open(config_file, "r") as f:
                    data = json.load(f)
                for service, config in data.items():
                    config["auth_method"] = AuthMethod(config["auth_method"])
                    self.configs[service] = AuthConfig(**config)
            except Exception as e:
                logger.error(f"Failed to load auth configs: {e}")

    def save_configs(self):
        """Save authentication configurations."""
        # Determine config file location
        if self.store:
            config_file = self.store.config_file
        else:
            config_file = Path.home() / ".academic_papers" / "auth" / "auth_config.json"
            config_file.parent.mkdir(parents=True, exist_ok=True)

        data = {}
        for service, config in self.configs.items():
            data[service] = config.to_dict()

        with open(config_file, "w") as f:
            json.dump(data, f, indent=2)

    def add_config(self, config: AuthConfig):
        """Add or update authentication configuration."""
        self.configs[config.service_name] = config

        # Store credentials securely if provided
        if config.password and config.username:
            if self.store:
                self.store.store_credential(
                    config.service_name, config.username, config.password
                )
            elif self.credential_manager:
                # For new system, credentials are handled separately
                # ETH credentials should already be stored via credential_manager
                pass
            # Don't save password in config file
            config.password = None

        self.save_configs()

    def get_credential(self, service: str, username: str) -> Optional[str]:
        """Get credential using new secure system or fallback to old system."""
        if self.credential_manager:
            # For ETH credentials, use the new system
            if service.startswith("eth") or "eth" in service.lower():
                _, password = self.credential_manager.get_eth_credentials()
                return password
            else:
                # For other services, try to get from credential manager
                return self.credential_manager.get_credential(f"{service}_password")
        elif self.store:
            # Fallback to old system
            return self.store.get_credential(service, username)
        else:
            return None

    def get_authenticated_session(self, service: str) -> Optional[requests.Session]:
        """Get an authenticated session for a service."""
        if service not in self.configs:
            logger.error(f"No configuration found for service: {service}")
            return None

        # Check if we have a valid cached session
        if service in self.sessions and service in self.session_info:
            session_info = self.session_info[service]
            if session_info.is_valid and not session_info.is_expired():
                logger.debug(f"Using cached session for {service}")
                return self.sessions[service]

        # Create new session
        config = self.configs[service]
        session = requests.Session()

        # Get password if needed
        if config.username and not config.password:
            config.password = self.get_credential(service, config.username)

        # Use appropriate authentication handler
        auth_method = config.auth_method.value
        if auth_method in AUTH_HANDLERS:
            handler = AUTH_HANDLERS[auth_method]
            if handler.authenticate(config, session):
                self.sessions[service] = session
                self.session_info[service] = SessionInfo(
                    service=service,
                    username=config.username,
                    expires_at=datetime.now() + timedelta(hours=1),  # Default 1 hour
                    is_valid=True
                )
                logger.info(f"Authentication successful for {service}")
                return session
            else:
                logger.error(f"Authentication failed for {service}")
                return None
        else:
            logger.error(f"Unsupported auth method: {auth_method}")
            return None

    def validate_session(self, service: str, test_url: Optional[str] = None) -> bool:
        """Validate if a session is still working."""
        if service not in self.sessions:
            return False

        session = self.sessions[service]
        config = self.configs.get(service)

        # Use test_url or base_url from config
        url = test_url or (config.base_url if config else None)
        if not url:
            logger.warning(f"No URL to test session for {service}")
            return True  # Assume valid if we can't test

        try:
            response = session.head(url, timeout=10)
            is_valid = response.status_code != 401
            
            # Update session info
            if service in self.session_info:
                self.session_info[service].is_valid = is_valid
                
            return is_valid
        except Exception as e:
            logger.warning(f"Session validation failed for {service}: {e}")
            if service in self.session_info:
                self.session_info[service].is_valid = False
            return False

    def download_with_auth(self, service: str, url: str, **kwargs) -> Optional[requests.Response]:
        """Download content using authenticated session."""
        session = self.get_authenticated_session(service)
        if not session:
            logger.error(f"Could not get authenticated session for {service}")
            return None

        try:
            response = session.get(url, **kwargs)
            response.raise_for_status()
            logger.info(f"Successfully downloaded from {url} using {service}")
            return response
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.warning(f"Session expired for {service}, trying to re-authenticate")
                # Clear cached session and try once more
                if service in self.sessions:
                    del self.sessions[service]
                if service in self.session_info:
                    del self.session_info[service]
                
                session = self.get_authenticated_session(service)
                if session:
                    try:
                        response = session.get(url, **kwargs)
                        response.raise_for_status()
                        return response
                    except Exception as e2:
                        logger.error(f"Re-authentication failed: {e2}")
            else:
                logger.error(f"HTTP error downloading from {url}: {e}")
        except Exception as e:
            logger.error(f"Error downloading from {url}: {e}")
        
        return None

    def download_with_auth_legacy(self, url: str, service: str, dst_path: str, **kwargs) -> bool:
        """Legacy download method with different signature."""
        response = self.download_with_auth(service, url, **kwargs)
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

    def get_service_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get all service configurations (without sensitive data)."""
        return {name: config.to_dict() for name, config in self.configs.items()}

    def remove_config(self, service: str) -> bool:
        """Remove a service configuration."""
        if service in self.configs:
            del self.configs[service]
            if service in self.sessions:
                del self.sessions[service]
            if service in self.session_info:
                del self.session_info[service]
            if service in self.browser_contexts:
                context = self.browser_contexts[service]
                if hasattr(context, 'close'):
                    try:
                        context.close()
                    except Exception as e:
                        logger.debug(f"Error closing browser context: {e}")
                del self.browser_contexts[service]
            self.save_configs()
            logger.info(f"Removed configuration for {service}")
            return True
        return False

    def clear_sessions(self):
        """Clear all cached sessions."""
        self.sessions.clear()
        self.session_info.clear()
        
        # Close browser contexts
        for context in self.browser_contexts.values():
            if hasattr(context, 'close'):
                try:
                    context.close()
                except Exception as e:
                    logger.debug(f"Error closing browser context: {e}")
        self.browser_contexts.clear()
        
        logger.info("Cleared all cached sessions")

    def get_session_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all sessions."""
        status = {}
        for service, session_info in self.session_info.items():
            status[service] = {
                'username': session_info.username,
                'is_valid': session_info.is_valid,
                'is_expired': session_info.is_expired(),
                'expires_at': session_info.expires_at.isoformat() if session_info.expires_at else None,
                'has_session': service in self.sessions
            }
        return status

    # Legacy method compatibility
    def _auth_api_key(self, session: requests.Session, config: AuthConfig) -> bool:
        """Legacy API key authentication method."""
        handler = AUTH_HANDLERS.get('api_key')
        if handler:
            return handler.authenticate(config, session)
        return False

    def _auth_basic(self, session: requests.Session, config: AuthConfig) -> bool:
        """Legacy basic authentication method."""
        handler = AUTH_HANDLERS.get('basic_auth')
        if handler:
            return handler.authenticate(config, session)
        return False

    def _auth_oauth(self, session: requests.Session, config: AuthConfig) -> bool:
        """Legacy OAuth authentication method."""
        handler = AUTH_HANDLERS.get('oauth')
        if handler:
            return handler.authenticate(config, session)
        return False

    def _auth_cookie(self, session: requests.Session, config: AuthConfig) -> bool:
        """Legacy cookie authentication method."""
        handler = AUTH_HANDLERS.get('cookie')
        if handler:
            return handler.authenticate(config, session)
        return False

    def _validate_session(self, session: requests.Session, service: str) -> bool:
        """Legacy session validation method."""
        config = self.configs.get(service)
        
        # Use base_url from config
        url = config.base_url if config else None
        if not url:
            logger.warning(f"No URL to test session for {service}")
            return True  # Assume valid if we can't test
        
        try:
            response = session.get(url, timeout=10)
            is_valid = response.status_code != 401
            
            # Check for login redirect by looking at final URL
            if response.url and 'login' in response.url.lower():
                is_valid = False
            
            return is_valid
        except Exception as e:
            logger.warning(f"Session validation failed for {service}: {e}")
            return False

