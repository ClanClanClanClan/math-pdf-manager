#!/usr/bin/env python3
"""
Credential Management System
Secure storage and management of institutional credentials and API keys.
"""

import asyncio
import json
import base64
import hashlib
import os
import getpass
from pathlib import Path
from typing import Dict, Optional, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import aiohttp
import logging

logger = logging.getLogger(__name__)

def get_secure_password(prompt: str = "Enter password: ") -> str:
    """Get password securely without echoing to terminal"""
    return getpass.getpass(prompt)

def create_secure_session(**kwargs) -> aiohttp.ClientSession:
    """Create an aiohttp session with SSL verification enabled"""
    import ssl
    import certifi
    
    # Create SSL context with certificate verification
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    ssl_context.check_hostname = True
    ssl_context.verify_mode = ssl.CERT_REQUIRED
    
    # Default connector with SSL
    connector = aiohttp.TCPConnector(
        ssl=ssl_context,
        limit=100,
        limit_per_host=30,
        ttl_dns_cache=300,
        enable_cleanup_closed=True
    )
    
    # Default timeout
    timeout = aiohttp.ClientTimeout(total=30, connect=10)
    
    # Merge with user kwargs
    session_kwargs = {
        'connector': connector,
        'timeout': timeout,
        'trust_env': True,  # Respect proxy environment variables
    }
    session_kwargs.update(kwargs)
    
    return aiohttp.ClientSession(**session_kwargs)

class CredentialManager:
    """Secure credential storage and management"""
    
    def __init__(self, credentials_file: str = "config/credentials.enc"):
        self.credentials_file = Path(credentials_file)
        self.credentials_file.parent.mkdir(exist_ok=True)
        self._fernet = None
        self._credentials = {}
        self._master_key = None
    
    def _get_encryption_key(self, password: str, salt: bytes) -> bytes:
        """Generate encryption key from password"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def initialize_encryption(self, master_password: str):
        """Initialize encryption with master password"""
        if self.credentials_file.exists():
            # Load existing credentials
            with open(self.credentials_file, 'rb') as f:
                data = f.read()
                salt = data[:16]  # First 16 bytes are salt
                encrypted_data = data[16:]
            
            key = self._get_encryption_key(master_password, salt)
            self._fernet = Fernet(key)
            
            try:
                decrypted = self._fernet.decrypt(encrypted_data)
                self._credentials = json.loads(decrypted.decode())
                logger.info("Credentials loaded successfully")
            except Exception as e:
                raise ValueError("Invalid master password or corrupted credentials file")
        
        else:
            # Create new credentials file
            salt = os.urandom(16)
            key = self._get_encryption_key(master_password, salt)
            self._fernet = Fernet(key)
            self._credentials = {}
            self._save_credentials(salt)
            logger.info("New credentials file created")
    
    def _save_credentials(self, salt: bytes = None):
        """Save encrypted credentials to file"""
        if not self._fernet:
            raise RuntimeError("Encryption not initialized")
        
        if salt is None:
            # Extract salt from existing file or generate new
            if self.credentials_file.exists():
                with open(self.credentials_file, 'rb') as f:
                    salt = f.read(16)
            else:
                salt = os.urandom(16)
        
        # Encrypt credentials
        encrypted_data = self._fernet.encrypt(json.dumps(self._credentials).encode())
        
        # Save salt + encrypted data
        with open(self.credentials_file, 'wb') as f:
            f.write(salt + encrypted_data)
    
    def set_publisher_credentials(self, publisher: str, credentials: Dict[str, str]):
        """Set credentials for a publisher"""
        if not self._fernet:
            raise RuntimeError("Encryption not initialized")
        
        self._credentials[publisher] = credentials
        self._save_credentials()
        logger.info(f"Credentials saved for {publisher}")
    
    def get_publisher_credentials(self, publisher: str) -> Optional[Dict[str, str]]:
        """Get credentials for a publisher"""
        return self._credentials.get(publisher)
    
    def list_publishers(self) -> list:
        """List all publishers with stored credentials"""
        return list(self._credentials.keys())
    
    def remove_publisher_credentials(self, publisher: str):
        """Remove credentials for a publisher"""
        if publisher in self._credentials:
            del self._credentials[publisher]
            self._save_credentials()
            logger.info(f"Credentials removed for {publisher}")

class SessionManager:
    """Manage authenticated sessions with publishers"""
    
    def __init__(self, credential_manager: CredentialManager):
        self.credential_manager = credential_manager
        self.sessions: Dict[str, aiohttp.ClientSession] = {}
        self.authenticated: Dict[str, bool] = {}
        
    async def get_authenticated_session(self, publisher: str) -> Optional[aiohttp.ClientSession]:
        """Get authenticated session for publisher"""
        
        if publisher in self.sessions and self.authenticated.get(publisher, False):
            return self.sessions[publisher]
        
        # Create new session with SSL verification and authenticate
        session = create_secure_session()
        self.sessions[publisher] = session
        
        success = await self._authenticate_publisher(publisher, session)
        self.authenticated[publisher] = success
        
        if success:
            return session
        else:
            await session.close()
            del self.sessions[publisher]
            return None
    
    async def _authenticate_publisher(self, publisher: str, session: aiohttp.ClientSession) -> bool:
        """Authenticate with specific publisher"""
        credentials = self.credential_manager.get_publisher_credentials(publisher)
        if not credentials:
            logger.warning(f"No credentials found for {publisher}")
            return False
        
        try:
            if publisher == 'springer':
                return await self._authenticate_springer(credentials, session)
            elif publisher == 'elsevier':
                return await self._authenticate_elsevier(credentials, session)
            elif publisher == 'wiley':
                return await self._authenticate_wiley(credentials, session)
            elif publisher == 'ieee':
                return await self._authenticate_ieee(credentials, session)
            else:
                logger.warning(f"No authentication method for {publisher}")
                return False
        
        except Exception as e:
            logger.error(f"Authentication failed for {publisher}: {e}")
            return False
    
    async def _authenticate_springer(self, credentials: Dict[str, str], session: aiohttp.ClientSession) -> bool:
        """Authenticate with Springer via institutional access"""
        
        # Method 1: Direct institutional login
        if 'institution_url' in credentials:
            return await self._institutional_login(credentials, session, 'springer')
        
        # Method 2: Shibboleth/SAML
        if 'shibboleth_url' in credentials:
            return await self._shibboleth_login(credentials, session, 'springer')
        
        # Method 3: Direct credentials (if available)
        if 'username' in credentials and 'password' in credentials:
            login_url = "https://link.springer.com/login"
            login_data = {
                'username': credentials['username'],
                'password': credentials['password']
            }
            
            async with session.post(login_url, data=login_data) as response:
                if response.status == 200:
                    # Check if login was successful by looking for user indicators
                    content = await response.text()
                    if 'logout' in content.lower() or 'welcome' in content.lower():
                        logger.info("Springer authentication successful")
                        return True
        
        return False
    
    async def _authenticate_elsevier(self, credentials: Dict[str, str], session: aiohttp.ClientSession) -> bool:
        """Authenticate with Elsevier/ScienceDirect"""
        
        # API key authentication
        if 'api_key' in credentials:
            # Test API key
            test_url = "https://api.elsevier.com/content/search/scopus"
            headers = {'X-ELS-APIKey': credentials['api_key']}
            params = {'query': 'test', 'count': 1}
            
            try:
                async with session.get(test_url, headers=headers, params=params) as response:
                    if response.status == 200:
                        logger.info("Elsevier API key valid")
                        return True
            except Exception as e:
                logger.error(f"Elsevier API test failed: {e}")
        
        # Institutional access
        if 'institution_url' in credentials:
            return await self._institutional_login(credentials, session, 'elsevier')
        
        return False
    
    async def _authenticate_wiley(self, credentials: Dict[str, str], session: aiohttp.ClientSession) -> bool:
        """Authenticate with Wiley"""
        if 'institution_url' in credentials:
            return await self._institutional_login(credentials, session, 'wiley')
        return False
    
    async def _authenticate_ieee(self, credentials: Dict[str, str], session: aiohttp.ClientSession) -> bool:
        """Authenticate with IEEE Xplore"""
        if 'institution_url' in credentials:
            return await self._institutional_login(credentials, session, 'ieee')
        return False
    
    async def _institutional_login(self, credentials: Dict[str, str], 
                                 session: aiohttp.ClientSession, 
                                 publisher: str) -> bool:
        """Generic institutional login flow"""
        
        institution_url = credentials.get('institution_url')
        username = credentials.get('username')
        password = credentials.get('password')
        
        if not all([institution_url, username, password]):
            logger.error(f"Missing institutional credentials for {publisher}")
            return False
        
        try:
            # Step 1: Access institutional login page
            async with session.get(institution_url) as response:
                if response.status != 200:
                    return False
                
                login_page = await response.text()
                
                # Extract login form details (this varies by institution)
                login_form_url, form_data = self._parse_login_form(login_page, username, password)
                
                if not login_form_url:
                    logger.error(f"Could not find login form for {publisher}")
                    return False
                
                # Step 2: Submit login form
                async with session.post(login_form_url, data=form_data) as login_response:
                    if login_response.status in [200, 302, 303]:
                        # Check for success indicators
                        content = await login_response.text()
                        if self._check_login_success(content, publisher):
                            logger.info(f"Institutional login successful for {publisher}")
                            return True
        
        except Exception as e:
            logger.error(f"Institutional login failed for {publisher}: {e}")
        
        return False
    
    async def _shibboleth_login(self, credentials: Dict[str, str], 
                              session: aiohttp.ClientSession, 
                              publisher: str) -> bool:
        """Handle Shibboleth/SAML authentication"""
        # This is complex and institution-specific
        # Would need customization for each institution's SAML setup
        logger.warning("Shibboleth authentication not fully implemented")
        return False
    
    def _parse_login_form(self, html: str, username: str, password: str) -> tuple:
        """Parse login form from HTML (simplified implementation)"""
        import re
        from html.parser import HTMLParser
        
        # Security: Use HTMLParser to avoid ReDoS vulnerabilities
        class LoginFormParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.form_action = None
                self.inputs = {}
                self.in_form = False
                self.current_input = {}
                
            def handle_starttag(self, tag, attrs):
                attrs_dict = dict(attrs)
                
                if tag == 'form':
                    self.in_form = True
                    self.form_action = attrs_dict.get('action', '')
                    
                elif tag == 'input' and self.in_form:
                    name = attrs_dict.get('name', '')
                    value = attrs_dict.get('value', '')
                    input_type = attrs_dict.get('type', 'text')
                    
                    if name:
                        self.inputs[name] = {
                            'value': value,
                            'type': input_type
                        }
            
            def handle_endtag(self, tag):
                if tag == 'form':
                    self.in_form = False
        
        parser = LoginFormParser()
        try:
            parser.feed(html)
        except Exception as e:
            logger.warning(f"Failed to parse login form: {e}")
            return None, {}
        
        if not parser.form_action:
            return None, {}
        
        # Build form data
        form_data = {}
        for input_name, input_info in parser.inputs.items():
            if 'user' in input_name.lower() or 'email' in input_name.lower():
                form_data[input_name] = username
            elif 'pass' in input_name.lower():
                form_data[input_name] = password
            else:
                # Use default value for hidden fields
                form_data[input_name] = input_info['value']
        
        return parser.form_action, form_data
    
    def _check_login_success(self, content: str, publisher: str) -> bool:
        """Check if login was successful based on response content"""
        success_indicators = [
            'logout', 'welcome', 'dashboard', 'profile', 
            'signed in', 'authenticated', 'account'
        ]
        
        failure_indicators = [
            'error', 'invalid', 'incorrect', 'failed', 
            'try again', 'login'
        ]
        
        content_lower = content.lower()
        
        # Count success vs failure indicators
        success_count = sum(1 for indicator in success_indicators if indicator in content_lower)
        failure_count = sum(1 for indicator in failure_indicators if indicator in content_lower)
        
        return success_count > failure_count
    
    async def close_all_sessions(self):
        """Close all active sessions"""
        for session in self.sessions.values():
            await session.close()
        self.sessions.clear()
        self.authenticated.clear()

# Configuration management
class DownloaderConfig:
    """Configuration management for the universal downloader"""
    
    def __init__(self, config_file: str = "config/downloader_config.json"):
        self.config_file = Path(config_file)
        self.config_file.parent.mkdir(exist_ok=True)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
        
        # Return default configuration
        return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "publisher_priorities": {
                "springer": 10,
                "elsevier": 11,
                "wiley": 12,
                "ieee": 13,
                "taylor_francis": 14,
                "sage": 15,
                "cambridge": 16,
                "oxford": 17,
                "acm": 18,
                "sci-hub": 20,
                "anna-archive": 21,
                "libgen": 22
            },
            "rate_limits": {
                "springer": 1.0,
                "elsevier": 2.0,
                "wiley": 1.5,
                "ieee": 1.0,
                "sci-hub": 3.0,
                "anna-archive": 2.0,
                "libgen": 2.5
            },
            "timeout_settings": {
                "connection_timeout": 30,
                "read_timeout": 60,
                "total_timeout": 120
            },
            "retry_settings": {
                "max_retries": 3,
                "backoff_factor": 1.5,
                "retry_statuses": [502, 503, 504, 429]
            },
            "download_preferences": [
                "institutional_access",
                "open_access",
                "alternative_sources"
            ],
            "user_agents": [
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ],
            "proxy_settings": {
                "use_proxy": False,
                "proxy_rotation": True,
                "proxy_list": []
            }
        }
    
    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info("Configuration saved")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def get(self, key: str, default=None):
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set configuration value"""
        self.config[key] = value
        self.save_config()

# Example usage and setup
async def setup_credentials():
    """Example setup for credentials"""
    
    # Initialize credential manager
    creds = CredentialManager()
    
    # Get master password securely
    import getpass
    master_password = getpass.getpass("Enter master password: ")
    creds.initialize_encryption(master_password)
    
    # Add publisher credentials (set via environment variables)
    springer_creds = {
        'institution_url': os.environ.get('SPRINGER_INSTITUTION_URL', ''),
        'username': os.environ.get('SPRINGER_USERNAME', ''),
        'password': os.environ.get('SPRINGER_PASSWORD', ''),
    }
    if not springer_creds['username']:
        raise RuntimeError("Set SPRINGER_USERNAME env var before running setup")
    creds.set_publisher_credentials('springer', springer_creds)

    elsevier_creds = {
        'api_key': os.environ.get('ELSEVIER_API_KEY', ''),
        'institution_url': os.environ.get('ELSEVIER_INSTITUTION_URL', ''),
    }
    if not elsevier_creds['api_key']:
        raise RuntimeError("Set ELSEVIER_API_KEY env var before running setup")
    creds.set_publisher_credentials('elsevier', elsevier_creds)
    
    # Test authentication
    session_manager = SessionManager(creds)
    
    springer_session = await session_manager.get_authenticated_session('springer')
    if springer_session:
        print("Springer authentication successful")
    else:
        print("Springer authentication failed")
    
    await session_manager.close_all_sessions()

if __name__ == "__main__":
    asyncio.run(setup_credentials())