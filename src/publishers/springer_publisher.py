#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
publishers/springer_publisher.py - Springer Publisher Implementation
Consolidates all Springer-related download and authentication logic
"""

import requests
from typing import Dict, Any, Optional, List
from pathlib import Path

from . import PublisherInterface, DownloadResult, publisher_registry


class SpringerPublisher(PublisherInterface):
    """Springer publisher implementation"""
    
    @property
    def publisher_name(self) -> str:
        return "Springer"
    
    @property
    def base_url(self) -> str:
        return "https://link.springer.com"
    
    def authenticate(self) -> bool:
        """Authenticate with Springer"""
        try:
            self.session = requests.Session()
            
            # Set common headers
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            })
            
            # If we have session cookies, use them
            if self.auth_config.session_cookies:
                self.session.cookies.update(self.auth_config.session_cookies)
                self.logger.info("Using provided session cookies")
                return True
            
            # If we have credentials, perform login
            if self.auth_config.username and self.auth_config.password:
                return self._login_with_credentials()
            
            # If institutional login is configured
            if self.auth_config.institutional_login:
                return self._institutional_login()
            
            # Default: try anonymous access
            self.logger.info("Using anonymous access")
            return True
            
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            return False
    
    def _login_with_credentials(self) -> bool:
        """Login with username/password - Springer requires institutional authentication"""
        self.logger.info("Springer requires institutional authentication, not direct username/password")
        return self._institutional_login()
    
    def _institutional_login(self) -> bool:
        """Handle institutional login/SSO"""
        try:
            # Handle Springer institutional access
            self.logger.info(f"Attempting institutional login for: {self.auth_config.institutional_login}")
            
            # Springer institutional login flow requires browser automation
            # The complete flow is implemented in tools/security/
            # For now, return False to indicate manual authentication needed
            
            return False  # Browser automation required
        except Exception as e:
            self.logger.error(f"Institutional login failed: {e}")
            return False
    
    def search_paper(self, title: str, authors: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Search for papers on Springer"""
        try:
            if not self.session:
                self.authenticate()
            
            # Build search query
            search_params = {
                'query': title,
                'facet-content-type': 'Article',
                'showAll': 'false'
            }
            
            if authors:
                # Add author search
                author_query = ' OR '.join(authors)
                search_params['facet-creator'] = author_query
            
            # Search endpoint
            search_url = f"{self.base_url}/search"
            response = self.session.get(search_url, params=search_params)
            
            if response.status_code == 200:
                # Parse search results from HTML
                # This would need HTML parsing to extract results
                self.logger.info("Search completed successfully")
                return []  # Placeholder
            else:
                self.logger.error(f"Search failed: {response.status_code}")
                return []
                
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []
    
    def download_paper(self, paper_id: str, download_path: Path) -> DownloadResult:
        """Download a paper from Springer"""
        try:
            if not self.session:
                if not self.authenticate():
                    return DownloadResult(False, error_message="Authentication failed")
            
            # Handle different Springer identifier formats
            download_url = self._build_download_url(paper_id)
            if not download_url:
                return DownloadResult(False, error_message="Could not build download URL")
            
            # Download the paper
            response = self.session.get(download_url, stream=True)
            
            if response.status_code == 200:
                # Save to file
                download_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(download_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                self.logger.info(f"Successfully downloaded paper {paper_id}")
                return DownloadResult(True, file_path=download_path)
            else:
                error_msg = f"Download failed: HTTP {response.status_code}"
                if response.status_code == 403:
                    error_msg += " (Access denied - authentication may be required)"
                self.logger.error(error_msg)
                return DownloadResult(False, error_message=error_msg)
                
        except Exception as e:
            error_msg = f"Download failed: {e}"
            self.logger.error(error_msg)
            return DownloadResult(False, error_message=error_msg)
    
    def _build_download_url(self, identifier: str) -> Optional[str]:
        """Build Springer download URL from identifier."""
        # Handle DOI format: 10.1007/978-3-319-07443-6_15
        if '10.1007' in identifier:
            doi_part = identifier.split('10.1007/')[-1]
            return f"{self.base_url}/content/pdf/10.1007/{doi_part}.pdf"
        
        # Handle direct Springer URLs
        elif 'link.springer.com' in identifier:
            if '/pdf/' not in identifier:
                # Convert article/chapter URL to PDF URL
                identifier = identifier.replace('/article/', '/content/pdf/')
                identifier = identifier.replace('/chapter/', '/content/pdf/')
                if not identifier.endswith('.pdf'):
                    identifier += '.pdf'
            return identifier
        
        return None
    
    def get_paper_metadata(self, paper_id: str) -> Dict[str, Any]:
        """Get metadata for a paper"""
        try:
            if not self.session:
                self.authenticate()
            
            # Handle different identifier formats
            if '10.1007' in paper_id:
                # DOI format
                details_url = f"{self.base_url}/article/10.1007/{paper_id.split('10.1007/')[-1]}"
            elif 'link.springer.com' in paper_id:
                details_url = paper_id
            else:
                return {}
            
            response = self.session.get(details_url)
            
            if response.status_code == 200:
                # Parse metadata from HTML
                # This would need HTML parsing to extract metadata
                self.logger.info("Metadata retrieved successfully")
                return {}  # Placeholder
            else:
                self.logger.error(f"Failed to get metadata: {response.status_code}")
                return {}
                
        except Exception as e:
            self.logger.error(f"Failed to get metadata: {e}")
            return {}


# Register the Springer publisher
publisher_registry.register('springer', SpringerPublisher)


# Export the class
__all__ = ['SpringerPublisher']