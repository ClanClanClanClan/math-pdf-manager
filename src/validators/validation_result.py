"""
Validation Result Objects

Data models for validation results extracted from src.validators.filename_checker.py
"""

from dataclasses import dataclass
from typing import List, Optional, Literal


@dataclass 
class Message:
    """Validation message (error, warning, or info)"""
    level: Literal["error", "warning", "info"]
    code: str
    text: str
    pos: Optional[int] = None


@dataclass
class FilenameCheckResult:
    """Result of filename validation check"""
    filename: str
    messages: List[Message]
    fixed_filename: Optional[str] = None
    fixed_author: Optional[str] = None
    path: str = ""
    folder: str = ""

    @property
    def errors(self) -> List[str]:
        """Get all error messages"""
        return [m.text for m in self.messages if m.level == "error"]

    @property
    def suggestions(self) -> List[str]:
        """Get all suggestion messages (warnings and info)"""
        return [m.text for m in self.messages if m.level != "error"]

    @property
    def has_errors(self) -> bool:
        """Check if result has any errors"""
        return len(self.errors) > 0

    @property
    def has_suggestions(self) -> bool:
        """Check if result has any suggestions"""
        return len(self.suggestions) > 0

    def add_message(self, level: Literal["error", "warning", "info"], 
                   code: str, text: str, pos: Optional[int] = None) -> None:
        """Add a validation message"""
        self.messages.append(Message(level=level, code=code, text=text, pos=pos))

    def add_error(self, code: str, text: str, pos: Optional[int] = None) -> None:
        """Add an error message"""
        self.add_message("error", code, text, pos)

    def add_warning(self, code: str, text: str, pos: Optional[int] = None) -> None:
        """Add a warning message"""
        self.add_message("warning", code, text, pos)

    def add_info(self, code: str, text: str, pos: Optional[int] = None) -> None:
        """Add an info message"""
        self.add_message("info", code, text, pos)


@dataclass
class ValidationResult:
    """Generic validation result"""
    is_valid: bool
    original: str
    fixed: Optional[str] = None
    messages: List[Message] = None
    
    def __post_init__(self):
        if self.messages is None:
            self.messages = []

    @property
    def errors(self) -> List[str]:
        """Get all error messages"""
        return [m.text for m in self.messages if m.level == "error"]

    @property
    def warnings(self) -> List[str]:
        """Get all warning messages"""
        return [m.text for m in self.messages if m.level == "warning"]

    @property
    def info(self) -> List[str]:
        """Get all info messages"""
        return [m.text for m in self.messages if m.level == "info"]


# Backward compatibility aliases
CheckResult = FilenameCheckResult