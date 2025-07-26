"""
Validation Service Interfaces

Defines the contract for validation services in the system.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Set
from pathlib import Path


class IValidationService(ABC):
    """Interface for comprehensive validation services."""
    
    @abstractmethod
    def validate_cli_inputs(self, args: Any) -> bool:
        """Validate command-line arguments."""
        pass
    
    @abstractmethod
    def validate_file_path(self, path: Union[str, Path]) -> bool:
        """Validate file path for security and accessibility."""
        pass
    
    @abstractmethod
    def validate_directory_path(self, path: Union[str, Path]) -> bool:
        """Validate directory path for security and accessibility."""
        pass
    
    @abstractmethod
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe filesystem usage."""
        pass
    
    @abstractmethod
    def validate_mathematical_content(self, text: str) -> Dict[str, Any]:
        """Validate and analyze mathematical content in text."""
        pass
    
    @abstractmethod
    def validate_academic_text(self, text: str) -> Dict[str, Any]:
        """Validate and analyze academic text content."""
        pass
    
    @abstractmethod
    def detect_security_issues(self, content: str) -> List[Dict[str, Any]]:
        """Detect potential security issues in content."""
        pass
    
    # Additional methods for comprehensive validation
    @abstractmethod
    def validate_string(self, value: str, min_length: int = 0, max_length: int = 1000, 
                       allowed_chars: Optional[Set[str]] = None) -> str:
        """Validate and sanitize string input."""
        pass
    
    @abstractmethod
    def validate_email(self, email: str) -> str:
        """Validate email address format."""
        pass
    
    @abstractmethod
    def validate_url(self, url: str, allowed_schemes: List[str] = None) -> str:
        """Validate URL format and scheme."""
        pass
    
    @abstractmethod
    def validate_ip_address(self, ip: str, version: Optional[int] = None) -> str:
        """Validate IP address."""
        pass
    
    @abstractmethod
    def validate_file_extension(self, filename: str, allowed_extensions: Optional[Set[str]] = None,
                               file_type: Optional[str] = None) -> str:
        """Validate file extension against allowed types."""
        pass
    
    @abstractmethod
    def validate_integer(self, value: Any, min_value: Optional[int] = None, 
                        max_value: Optional[int] = None) -> int:
        """Validate integer input with optional bounds."""
        pass
    
    @abstractmethod
    def detect_language(self, text: str) -> str:
        """Detect language of academic/mathematical text."""
        pass
    
    # Additional comprehensive validation methods
    @abstractmethod
    def validate_academic_filename(self, filename: str) -> Any:
        """Validate academic paper filename format."""
        pass
    
    @abstractmethod
    def validate_session(self, session_id: str, timestamp: Optional[float] = None) -> bool:
        """Validate session ID and check for timeout."""
        pass
    
    @abstractmethod
    def validate_pdf_file(self, file_path: Union[str, Path]) -> Any:
        """Validate PDF file format and metadata."""
        pass
    
    @abstractmethod
    def validate_configuration(self, config: Dict[str, Any]) -> Any:
        """Validate configuration dictionary."""
        pass