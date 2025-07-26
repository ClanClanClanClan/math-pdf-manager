#!/usr/bin/env python3
"""
Automated ETH Authentication Setup
==================================

Fully automated setup for ETH institutional access using secure credential management.
No interactive prompts - credentials must be provided via environment variables or config.
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

from src.secure_credential_manager import get_credential_manager
from auth_manager import get_auth_manager, AuthConfig, AuthMethod
from core.config.secure_config import get_secure_credential, ConfigurationError

logger = logging.getLogger("automated_eth_setup")


@dataclass
class PublisherConfig:
    """Configuration for a publisher's ETH access."""
    name: str
    wayf_url: str
    eth_selector: Optional[str] = None
    login_form_selectors: Optional[Dict[str, str]] = None
    success_indicators: Optional[List[str]] = None


# ETH-specific publisher configurations
ETH_PUBLISHER_CONFIGS = {
    "ieee": PublisherConfig(
        name="ieee",
        wayf_url="https://ieeexplore.ieee.org/Xplore/guesthome.jsp",
        eth_selector='option[value*="ethz"], a:has-text("ETH Zurich"), a:has-text("Swiss Federal Institute")',
        login_form_selectors={
            "username": 'input[name="j_username"], input[name="username"], input[id="username"]',
            "password": 'input[name="j_password"], input[name="password"], input[id="password"]',
            "submit": 'input[type="submit"], button[type="submit"], button:has-text("Login")'
        },
        success_indicators=["logout", "sign out", "authenticated"]
    ),
    
    "acm": PublisherConfig(
        name="acm", 
        wayf_url="https://dl.acm.org/action/ssostart",
        eth_selector='option[value*="ethz"], a:has-text("ETH Zurich")',
        login_form_selectors={
            "username": 'input[name="j_username"], input[name="username"]',
            "password": 'input[name="j_password"], input[name="password"]', 
            "submit": 'input[type="submit"], button[type="submit"]'
        }
    ),
    
    "springer": PublisherConfig(
        name="springer",
        wayf_url="https://link.springer.com/signup-login",
        eth_selector='a:has-text("ETH Zurich"), option:has-text("ETH Zurich")',
        login_form_selectors={
            "username": 'input[name="username"], input[id="username"]',
            "password": 'input[name="password"], input[id="password"]',
            "submit": 'button[type="submit"], input[type="submit"]'
        }
    ),
    
    "elsevier": PublisherConfig(
        name="elsevier",
        wayf_url="https://www.sciencedirect.com/user/login",
        eth_selector='option:has-text("ETH"), a:has-text("institutional")',
    ),
    
    "wiley": PublisherConfig(
        name="wiley",
        wayf_url="https://onlinelibrary.wiley.com/action/ssostart", 
        eth_selector='option[value*="ethz"], a:has-text("ETH Zurich")',
    ),
    
    # Mathematical and scientific publishers
    "siam": PublisherConfig(
        name="siam",
        wayf_url="https://epubs.siam.org/action/ssostart",
        eth_selector='option[value*="ethz"], a:has-text("ETH Zurich"), option:has-text("Swiss Federal Institute")',
        login_form_selectors={
            "username": 'input[name="j_username"], input[name="username"]',
            "password": 'input[name="j_password"], input[name="password"]',
            "submit": 'input[type="submit"], button[type="submit"]'
        }
    ),
    
    "project_euclid": PublisherConfig(
        name="project_euclid",
        wayf_url="https://projecteuclid.org/shibboleth-login",
        eth_selector='option[value*="ethz"], a:has-text("ETH Zurich")',
        login_form_selectors={
            "username": 'input[name="j_username"], input[name="username"]',
            "password": 'input[name="j_password"], input[name="password"]',
            "submit": 'input[type="submit"], button[type="submit"]'
        }
    ),
    
    "jstor": PublisherConfig(
        name="jstor",
        wayf_url="https://www.jstor.org/action/ssostart",
        eth_selector='option[value*="ethz"], a:has-text("ETH Zurich")',
        login_form_selectors={
            "username": 'input[name="j_username"], input[name="username"]',
            "password": 'input[name="j_password"], input[name="password"]',
            "submit": 'input[type="submit"], button[type="submit"]'
        }
    ),
    
    "nature": PublisherConfig(
        name="nature",
        wayf_url="https://idp.nature.com/authorize/externalsso",
        eth_selector='option[value*="ethz"], a:has-text("ETH Zurich")',
        login_form_selectors={
            "username": 'input[name="username"], input[id="username"]',
            "password": 'input[name="password"], input[id="password"]',
            "submit": 'button[type="submit"], input[type="submit"]'
        }
    ),
    
    "science": PublisherConfig(
        name="science",
        wayf_url="https://www.science.org/action/ssostart",
        eth_selector='option[value*="ethz"], a:has-text("ETH Zurich")',
        login_form_selectors={
            "username": 'input[name="j_username"], input[name="username"]',
            "password": 'input[name="j_password"], input[name="password"]',
            "submit": 'input[type="submit"], button[type="submit"]'
        }
    ),
    
    "taylor_francis": PublisherConfig(
        name="taylor_francis",
        wayf_url="https://www.tandfonline.com/action/ssostart",
        eth_selector='option[value*="ethz"], a:has-text("ETH Zurich")',
        login_form_selectors={
            "username": 'input[name="j_username"], input[name="username"]',
            "password": 'input[name="j_password"], input[name="password"]',
            "submit": 'input[type="submit"], button[type="submit"]'
        }
    ),
    
    "cambridge": PublisherConfig(
        name="cambridge",
        wayf_url="https://www.cambridge.org/core/shibboleth-login",
        eth_selector='option[value*="ethz"], a:has-text("ETH Zurich")',
        login_form_selectors={
            "username": 'input[name="j_username"], input[name="username"]',
            "password": 'input[name="j_password"], input[name="password"]',
            "submit": 'input[type="submit"], button[type="submit"]'
        }
    ),
    
    "oxford": PublisherConfig(
        name="oxford",
        wayf_url="https://academic.oup.com/pages/saml-login",
        eth_selector='option[value*="ethz"], a:has-text("ETH Zurich")',
        login_form_selectors={
            "username": 'input[name="j_username"], input[name="username"]',
            "password": 'input[name="j_password"], input[name="password"]',
            "submit": 'input[type="submit"], button[type="submit"]'
        }
    ),
    
    "ams": PublisherConfig(
        name="ams",
        wayf_url="https://www.ams.org/mathscinet/search/publications.html",
        eth_selector='option[value*="ethz"], a:has-text("ETH Zurich")',
        login_form_selectors={
            "username": 'input[name="j_username"], input[name="username"]',
            "password": 'input[name="j_password"], input[name="password"]',
            "submit": 'input[type="submit"], button[type="submit"]'
        }
    ),
    
    "ims": PublisherConfig(
        name="ims",
        wayf_url="https://projecteuclid.org/journals/institute-of-mathematical-statistics-collections",
        eth_selector='option[value*="ethz"], a:has-text("ETH Zurich")',
        login_form_selectors={
            "username": 'input[name="j_username"], input[name="username"]',
            "password": 'input[name="j_password"], input[name="password"]',
            "submit": 'input[type="submit"], button[type="submit"]'
        }
    )
}


class AutomatedETHSetup:
    """Fully automated ETH authentication setup."""
    
    def __init__(self):
        self.credential_manager = get_credential_manager()
        self.auth_manager = get_auth_manager()
        
        # Check for ETH credentials
        self.eth_username, self.eth_password = self.credential_manager.get_eth_credentials()
        
        if not self.eth_username or not self.eth_password:
            self._setup_credentials_from_env()
    
    def _setup_credentials_from_env(self):
        """Setup credentials from environment variables."""
        logger.info("Setting up ETH credentials from environment variables...")
        
        # Get credentials using secure configuration
        try:
            env_username = get_secure_credential("eth_username")
            env_password = get_secure_credential("eth_password")
        except ConfigurationError as e:
            logger.error(f"Configuration error: {e}")
            env_username = None
            env_password = None
        
        if not env_username or not env_password:
            raise ValueError(
                "ETH credentials not found. Please configure securely:\n"
                "1. Use: python secure_credential_manager.py setup-env\n"
                "2. Set environment variables: ETH_USERNAME, ETH_PASSWORD\n"
                "3. Or use the secure credential manager to store credentials"
            )
        
        # Store credentials securely
        success = self.credential_manager.setup_credentials_from_dict({
            "eth_username": env_username,
            "eth_password": env_password
        })
        
        if not success:
            raise RuntimeError("Failed to store ETH credentials securely")
        
        # Update instance variables
        self.eth_username = env_username
        self.eth_password = env_password
        
        logger.info(f"✅ ETH credentials stored securely for user: {env_username}")
    
    def create_eth_auth_configs(self, publishers: List[str] = None) -> Dict[str, bool]:
        """Create authentication configurations for ETH access."""
        if publishers is None:
            publishers = list(ETH_PUBLISHER_CONFIGS.keys())
        
        results = {}
        
        for publisher in publishers:
            if publisher not in ETH_PUBLISHER_CONFIGS:
                logger.warning(f"Unknown publisher: {publisher}")
                results[publisher] = False
                continue
            
            try:
                pub_config = ETH_PUBLISHER_CONFIGS[publisher]
                
                # Create auth config
                auth_config = AuthConfig(
                    service_name=f"eth_{publisher}",
                    auth_method=AuthMethod.SHIBBOLETH,
                    base_url=pub_config.wayf_url,
                    shibboleth_idp="https://idp.ethz.ch/idp/profile/SAML2/Redirect/SSO",
                    username=self.eth_username,
                    # Don't store password in config - will be retrieved from secure storage
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }
                )
                
                # Add publisher-specific metadata
                if pub_config.eth_selector:
                    auth_config.custom_auth_handler = f"eth_selector:{pub_config.eth_selector}"
                
                if pub_config.login_form_selectors:
                    # Store form selectors as JSON in a custom field
                    import json
                    auth_config.cookies = {  # Reuse cookies field for metadata
                        "_form_selectors": json.dumps(pub_config.login_form_selectors)
                    }
                
                self.auth_manager.add_config(auth_config)
                results[publisher] = True
                logger.info(f"✅ Created auth config for eth_{publisher}")
                
            except Exception as e:
                logger.error(f"Failed to create config for {publisher}: {e}")
                results[publisher] = False
        
        return results
    
    def verify_setup(self) -> Dict[str, str]:
        """Verify that setup is working correctly."""
        logger.info("🔍 Verifying ETH authentication setup...")
        
        verification = {}
        
        # Check credentials
        if self.credential_manager.has_eth_credentials():
            verification["credentials"] = "✅ Available"
        else:
            verification["credentials"] = "❌ Missing"
        
        # Check auth configs
        eth_configs = [name for name in self.auth_manager.configs.keys() if name.startswith('eth_')]
        verification["auth_configs"] = f"✅ {len(eth_configs)} publishers configured" if eth_configs else "❌ No configs"
        
        # List configured publishers
        if eth_configs:
            publishers = [name.replace('eth_', '') for name in eth_configs]
            verification["publishers"] = ", ".join(publishers)
        else:
            verification["publishers"] = "None"
        
        return verification
    
    def test_auth_config(self, publisher: str) -> bool:
        """Test authentication config for a specific publisher."""
        service_name = f"eth_{publisher}"
        
        try:
            session = self.auth_manager.get_authenticated_session(service_name)
            if session:
                logger.info(f"✅ Successfully created authenticated session for {publisher}")
                return True
            else:
                logger.error(f"❌ Failed to create authenticated session for {publisher}")
                return False
        except Exception as e:
            logger.error(f"❌ Error testing {publisher}: {e}")
            return False
    
    def run_automated_setup(self, publishers: List[str] = None, verify: bool = True) -> bool:
        """Run complete automated setup."""
        try:
            logger.info("🚀 Starting automated ETH authentication setup...")
            
            # Create auth configs
            results = self.create_eth_auth_configs(publishers)
            
            successful_configs = sum(results.values())
            total_configs = len(results)
            
            logger.info(f"📊 Setup results: {successful_configs}/{total_configs} publishers configured")
            
            if verify:
                # Verify setup
                verification = self.verify_setup()
                logger.info("🔍 Verification results:")
                for key, value in verification.items():
                    logger.info(f"  {key}: {value}")
            
            # Test one config if available
            if successful_configs > 0:
                test_publisher = next(pub for pub, success in results.items() if success)
                logger.info(f"🧪 Testing configuration for {test_publisher}...")
                test_result = self.test_auth_config(test_publisher)
                
                if test_result:
                    logger.info("✅ Setup completed successfully!")
                    return True
                else:
                    logger.warning("⚠️  Setup completed but test failed")
                    return False
            else:
                logger.error("❌ No publishers configured successfully")
                return False
                
        except Exception as e:
            logger.error(f"❌ Automated setup failed: {e}")
            return False
    
    def create_usage_examples(self) -> str:
        """Generate usage examples for the configured setup."""
        examples = """
# ETH Authentication - Usage Examples

## 1. Download with ETH institutional access
```python
from scripts.downloader import acquire_paper_by_metadata

# Download from IEEE with ETH access
file_path, attempts = acquire_paper_by_metadata(
    "Deep Learning for Signal Processing",
    "/path/to/downloads",
    doi="10.1109/TSP.2023.1234567",
    auth_service="eth_ieee"  # Use ETH IEEE config
)

# Download from Springer with ETH access  
file_path, attempts = acquire_paper_by_metadata(
    "Machine Learning Theory",
    "/path/to/downloads", 
    doi="10.1007/s10994-023-12345-6",
    auth_service="eth_springer"  # Use ETH Springer config
)
```

## 2. Available ETH services
"""
        
        eth_services = [name for name in self.auth_manager.configs.keys() if name.startswith('eth_')]
        for service in eth_services:
            examples += f"- {service}\n"
        
        examples += """
## 3. Check authentication status
```python
from auth_manager import get_auth_manager

auth_manager = get_auth_manager()
session = auth_manager.get_authenticated_session("eth_ieee")
if session:
    print("✅ IEEE authentication working")
else:
    print("❌ IEEE authentication failed")
```

## 4. Environment variables for CI/CD
```bash
export ETH_USERNAME="your_eth_username"
export ETH_PASSWORD="your_eth_password"
```
"""
        return examples


def setup_eth_authentication(publishers: List[str] = None, verify: bool = True) -> bool:
    """
    Main function for automated ETH authentication setup.
    
    Args:
        publishers: List of publishers to configure (default: all supported)
        verify: Whether to verify the setup (default: True)
    
    Returns:
        True if setup successful, False otherwise
    """
    setup = AutomatedETHSetup()
    return setup.run_automated_setup(publishers, verify)


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Automated ETH Authentication Setup")
    parser.add_argument(
        "--publishers", 
        nargs="+", 
        choices=list(ETH_PUBLISHER_CONFIGS.keys()),
        help="Publishers to configure (default: all)"
    )
    parser.add_argument(
        "--no-verify", 
        action="store_true",
        help="Skip verification step"
    )
    parser.add_argument(
        "--examples",
        action="store_true", 
        help="Show usage examples"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s"
    )
    
    if args.examples:
        setup = AutomatedETHSetup()
        print(setup.create_usage_examples())
        sys.exit(0)
    
    # Run setup
    success = setup_eth_authentication(
        publishers=args.publishers,
        verify=not args.no_verify
    )
    
    if success:
        print("\n🎉 ETH authentication setup completed successfully!")
        print("\nNext steps:")
        print("1. Test downloads with: python automated_eth_setup.py --examples")
        print("2. Use auth_service='eth_<publisher>' in download calls")
        sys.exit(0)
    else:
        print("\n❌ ETH authentication setup failed!")
        sys.exit(1)