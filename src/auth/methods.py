"""
Authentication Methods

Implementation of various authentication methods.
Extracted from auth_manager.py for better modularity.
"""

import logging
import requests
from abc import ABC, abstractmethod
from urllib.parse import urljoin, urlparse

from .models import AuthConfig

logger = logging.getLogger(__name__)

# Browser automation imports
try:
    from playwright.sync_api import sync_playwright, BrowserContext
    # Browser import available for future use
    import importlib.util
    _browser_spec = importlib.util.find_spec('playwright.sync_api')
    PLAYWRIGHT_AVAILABLE = _browser_spec is not None
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    BrowserContext = None
    logger.warning("Playwright not available - some auth methods may not work")


class AuthHandler(ABC):
    """Abstract base class for authentication handlers."""
    
    @abstractmethod
    def authenticate(self, config: AuthConfig, session: requests.Session) -> bool:
        """Authenticate using the provided configuration."""
        pass


class BasicAuthHandler(AuthHandler):
    """Handler for HTTP Basic Authentication."""
    
    def authenticate(self, config: AuthConfig, session: requests.Session) -> bool:
        """Set up basic authentication."""
        if not config.username or not config.password:
            logger.error("Basic auth requires username and password")
            return False
            
        session.auth = (config.username, config.password)
        
        # Test authentication if base_url is provided
        if config.base_url:
            try:
                response = session.get(config.base_url, timeout=10)
                if response.status_code == 401:
                    logger.error("Basic authentication failed")
                    return False
            except Exception as e:
                logger.warning(f"Could not test basic auth: {e}")
                
        logger.info(f"Basic authentication configured for {config.service_name}")
        return True


class ApiKeyAuthHandler(AuthHandler):
    """Handler for API Key authentication."""
    
    def authenticate(self, config: AuthConfig, session: requests.Session) -> bool:
        """Set up API key authentication."""
        if not config.api_key:
            logger.error("API key authentication requires api_key")
            return False
            
        # Add API key to headers
        if config.headers:
            session.headers.update(config.headers)
        else:
            # Default API key headers - support both formats for backward compatibility
            session.headers['Authorization'] = f'apikey {config.api_key}'
            session.headers['X-API-Key'] = config.api_key
            
        logger.info(f"API key authentication configured for {config.service_name}")
        return True


class OAuthHandler(AuthHandler):
    """Handler for OAuth authentication."""
    
    def authenticate(self, config: AuthConfig, session: requests.Session) -> bool:
        """Set up OAuth authentication."""
        if not all([config.oauth_client_id, config.oauth_client_secret, config.oauth_token_url]):
            logger.error("OAuth requires client_id, client_secret, and token_url")
            return False
            
        try:
            # Get OAuth token
            token_data = {
                'grant_type': 'client_credentials',
                'client_id': config.oauth_client_id,
                'client_secret': config.oauth_client_secret
            }
            
            response = session.post(config.oauth_token_url, data=token_data, timeout=30)
            response.raise_for_status()
            
            token_info = response.json()
            access_token = token_info.get('access_token')
            
            if not access_token:
                logger.error("No access token in OAuth response")
                return False
                
            session.headers['Authorization'] = f'Bearer {access_token}'
            logger.info(f"OAuth authentication successful for {config.service_name}")
            return True
            
        except Exception as e:
            logger.error(f"OAuth authentication failed: {e}")
            return False


class ShibbolethHandler(AuthHandler):
    """Handler for Shibboleth/SAML authentication."""
    
    def authenticate(self, config: AuthConfig, session: requests.Session) -> bool:
        """Set up Shibboleth authentication using browser automation."""
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("Shibboleth auth requires Playwright")
            return False
            
        if not config.shibboleth_idp or not config.username or not config.password:
            logger.error("Shibboleth requires IDP URL, username, and password")
            return False
            
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context()
                page = context.new_page()
                
                # Navigate to service
                page.goto(config.base_url or config.shibboleth_idp)
                
                # Wait for login form and fill credentials
                page.wait_for_selector('input[type="text"], input[name="username"]', timeout=10000)
                page.fill('input[type="text"], input[name="username"]', config.username)
                page.fill('input[type="password"], input[name="password"]', config.password)
                
                # Submit form
                page.click('input[type="submit"], button[type="submit"]')
                
                # Wait for redirect
                page.wait_for_load_state('networkidle', timeout=30000)
                
                # Extract cookies
                cookies = context.cookies()
                for cookie in cookies:
                    session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
                    
                browser.close()
                
                logger.info(f"Shibboleth authentication successful for {config.service_name}")
                return True
                
        except Exception as e:
            logger.error(f"Shibboleth authentication failed: {e}")
            return False


class EZProxyHandler(AuthHandler):
    """Handler for EZProxy authentication."""
    
    def authenticate(self, config: AuthConfig, session: requests.Session) -> bool:
        """Set up EZProxy authentication."""
        if not config.ezproxy_url or not config.username or not config.password:
            logger.error("EZProxy requires proxy URL, username, and password")
            return False
            
        try:
            # Login to EZProxy
            login_url = urljoin(config.ezproxy_url, '/login')
            login_data = {
                'user': config.username,
                'pass': config.password,
                'url': config.base_url or ''
            }
            
            response = session.post(login_url, data=login_data, timeout=30)
            response.raise_for_status()
            
            # Check if login was successful
            if 'invalid' in response.text.lower() or 'error' in response.text.lower():
                logger.error("EZProxy login failed")
                return False
                
            logger.info(f"EZProxy authentication successful for {config.service_name}")
            return True
            
        except Exception as e:
            logger.error(f"EZProxy authentication failed: {e}")
            return False


class CookieAuthHandler(AuthHandler):
    """Handler for cookie-based authentication."""
    
    def authenticate(self, config: AuthConfig, session: requests.Session) -> bool:
        """Set up cookie authentication."""
        if not config.cookies:
            logger.error("Cookie auth requires cookies")
            return False
            
        # Add cookies to session
        for name, value in config.cookies.items():
            if config.base_url:
                domain = urlparse(config.base_url).netloc
                session.cookies.set(name, value, domain=domain)
            else:
                # Without domain, just set the cookie
                session.cookies.set(name, value)
            
        # Add custom headers if provided
        if config.headers:
            session.headers.update(config.headers)
            
        logger.info(f"Cookie authentication configured for {config.service_name}")
        return True


# Registry of authentication handlers
AUTH_HANDLERS = {
    'basic_auth': BasicAuthHandler(),
    'api_key': ApiKeyAuthHandler(),
    'oauth': OAuthHandler(),
    'shibboleth': ShibbolethHandler(),
    'ezproxy': EZProxyHandler(),
    'cookie': CookieAuthHandler(),
}