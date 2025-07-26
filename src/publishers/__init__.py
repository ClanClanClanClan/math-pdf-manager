#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
publishers/__init__.py - Unified Publisher Interface
Consolidates IEEE, SIAM, and other publisher-specific downloading logic
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class DownloadResult:
    """Result of a download operation"""
    success: bool
    file_path: Optional[Path] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AuthenticationConfig:
    """Authentication configuration for publishers"""
    username: Optional[str] = None
    password: Optional[str] = None
    session_cookies: Optional[Dict[str, str]] = None
    headers: Optional[Dict[str, str]] = None
    use_sso: bool = False
    institutional_login: Optional[str] = None


class PublisherInterface(ABC):
    """Abstract base class for publisher downloaders"""
    
    def __init__(self, auth_config: Optional[AuthenticationConfig] = None):
        self.auth_config = auth_config or AuthenticationConfig()
        self.session = None
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the publisher"""
        pass
    
    @abstractmethod
    def search_paper(self, title: str, authors: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Search for papers by title and/or authors"""
        pass
    
    @abstractmethod
    def download_paper(self, paper_id: str, download_path: Path) -> DownloadResult:
        """Download a paper by ID"""
        pass
    
    @abstractmethod
    def get_paper_metadata(self, paper_id: str) -> Dict[str, Any]:
        """Get metadata for a paper"""
        pass
    
    @property
    @abstractmethod
    def publisher_name(self) -> str:
        """Name of the publisher"""
        pass
    
    @property
    @abstractmethod
    def base_url(self) -> str:
        """Base URL for the publisher"""
        pass
    
    def is_authenticated(self) -> bool:
        """Check if currently authenticated"""
        return self.session is not None
    
    def logout(self) -> bool:
        """Logout and clean up session"""
        if self.session:
            self.session.close()
            self.session = None
        return True


class PublisherRegistry:
    """Registry for managing publisher implementations"""
    
    def __init__(self):
        self._publishers: Dict[str, type] = {}
    
    def register(self, name: str, publisher_class: type):
        """Register a publisher implementation"""
        if not issubclass(publisher_class, PublisherInterface):
            raise ValueError("Publisher class must inherit from PublisherInterface")
        self._publishers[name] = publisher_class
    
    def get_publisher(self, name: str, auth_config: Optional[AuthenticationConfig] = None) -> PublisherInterface:
        """Get a publisher instance by name"""
        if name not in self._publishers:
            raise ValueError(f"Unknown publisher: {name}")
        return self._publishers[name](auth_config)
    
    def list_publishers(self) -> List[str]:
        """List all registered publishers"""
        return list(self._publishers.keys())


# Global registry instance
publisher_registry = PublisherRegistry()


# Export main classes
__all__ = [
    'PublisherInterface',
    'PublisherRegistry',
    'DownloadResult',
    'AuthenticationConfig',
    'publisher_registry'
]