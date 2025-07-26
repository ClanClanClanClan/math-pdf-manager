"""
Data structures for filename validation.

This module contains the core data structures used throughout the filename
validation system.
"""

from typing import List, Optional
from dataclasses import dataclass


@dataclass
class Token:
    """Represents a tokenized piece of text."""
    kind: str
    value: str
    start: int
    end: int


@dataclass
class Message:
    """Represents a validation message (error or warning)."""
    type: str
    message: str
    position: Optional[int] = None
    suggestion: Optional[str] = None


@dataclass
class FilenameCheckResult:
    """Contains the results of filename validation."""
    is_valid: bool
    original_filename: str
    corrected_filename: Optional[str] = None
    messages: List[Message] = None
    warnings: List[str] = None
    errors: List[str] = None
    suggestions: List[str] = None
    
    # Backward compatibility properties
    @property
    def filename(self) -> str:
        """Backward compatibility for filename property."""
        return self.original_filename
    
    @property
    def fixed_filename(self) -> Optional[str]:
        """Backward compatibility for fixed_filename property."""
        return self.corrected_filename
    
    def __post_init__(self):
        """Initialize empty lists if None."""
        if self.messages is None:
            self.messages = []
        if self.warnings is None:
            self.warnings = []
        if self.errors is None:
            self.errors = []
        if self.suggestions is None:
            self.suggestions = []
    
    def add_message(self, msg_type: str, message: str, position: Optional[int] = None, 
                   suggestion: Optional[str] = None):
        """Add a validation message."""
        msg = Message(msg_type, message, position, suggestion)
        self.messages.append(msg)
        
        if msg_type == "error":
            self.errors.append(message)
        elif msg_type == "warning":
            self.warnings.append(message)
        elif msg_type == "suggestion":
            self.suggestions.append(message)
    
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0