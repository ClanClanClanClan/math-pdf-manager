#!/usr/bin/env python3
"""
Type Hints and Type Aliases
Common type definitions used across the application
"""

from typing import (
    Any, Callable, Dict, List, Optional, Tuple, Union, 
    TypeVar, Protocol, Literal, TypedDict, Final, NewType
)
from pathlib import Path
from datetime import datetime
import sys

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

# Generic type variables
T = TypeVar('T')
T_co = TypeVar('T_co', covariant=True)
T_contra = TypeVar('T_contra', contravariant=True)

# File and path types
FilePath: TypeAlias = Union[str, Path]
FileContent: TypeAlias = Union[str, bytes]
FileMode = Literal['r', 'w', 'a', 'rb', 'wb', 'ab']

# Data types
JSONValue: TypeAlias = Union[str, int, float, bool, None, Dict[str, 'JSONValue'], List['JSONValue']]
JSONDict: TypeAlias = Dict[str, JSONValue]
JSONList: TypeAlias = List[JSONValue]

# Unicode and text types
UnicodeChar = NewType('UnicodeChar', str)
NormalizedText = NewType('NormalizedText', str)
CharacterCode = NewType('CharacterCode', int)

# Academic paper types
DOI = NewType('DOI', str)
ArxivID = NewType('ArxivID', str)
PaperID: TypeAlias = Union[DOI, ArxivID, str]

# Authentication types
AuthToken = NewType('AuthToken', str)
UserID = NewType('UserID', str)
Password = NewType('Password', str)

# Configuration types
ConfigValue: TypeAlias = Union[str, int, float, bool, List[str], Dict[str, Any]]
ConfigDict: TypeAlias = Dict[str, ConfigValue]

# Validation types
ValidationResult: TypeAlias = Tuple[bool, Optional[str]]  # (is_valid, error_message)
ValidatorFunc: TypeAlias = Callable[[Any], ValidationResult]

# Error types
ErrorCode = NewType('ErrorCode', str)
ErrorMessage = NewType('ErrorMessage', str)

# Performance types
ByteSize = NewType('ByteSize', int)
Milliseconds = NewType('Milliseconds', float)
Percentage = NewType('Percentage', float)


class FileInfo(TypedDict):
    """Information about a file."""
    path: str
    size: int
    modified: datetime
    mime_type: Optional[str]


class PaperMetadata(TypedDict, total=False):
    """Metadata for an academic paper."""
    title: str
    authors: List[str]
    abstract: str
    doi: Optional[str]
    arxiv_id: Optional[str]
    year: Optional[int]
    journal: Optional[str]
    keywords: List[str]
    url: Optional[str]


class AuthCredentials(TypedDict):
    """Authentication credentials."""
    username: str
    password: str
    institution: Optional[str]
    method: Literal['basic', 'oauth', 'shibboleth']


class ProcessingOptions(TypedDict, total=False):
    """Options for processing operations."""
    normalize_unicode: bool
    fix_authors: bool
    validate_format: bool
    extract_metadata: bool
    use_cache: bool
    timeout: Optional[float]


# Protocol definitions for duck typing
class Cacheable(Protocol):
    """Protocol for cacheable objects."""
    def cache_key(self) -> str: ...
    def to_cache(self) -> bytes: ...
    @classmethod
    def from_cache(cls, data: bytes) -> 'Cacheable': ...


class Validator(Protocol):
    """Protocol for validators."""
    def validate(self, value: Any) -> ValidationResult: ...
    def sanitize(self, value: Any) -> Any: ...


class Parser(Protocol[T]):
    """Protocol for parsers."""
    def parse(self, content: str) -> T: ...
    def can_parse(self, content: str) -> bool: ...


class Logger(Protocol):
    """Protocol for loggers."""
    def debug(self, message: str, **kwargs: Any) -> None: ...
    def info(self, message: str, **kwargs: Any) -> None: ...
    def warning(self, message: str, **kwargs: Any) -> None: ...
    def error(self, message: str, **kwargs: Any) -> None: ...
    def critical(self, message: str, **kwargs: Any) -> None: ...


# Constants
MAX_FILENAME_LENGTH: Final[int] = 255
MAX_PATH_LENGTH: Final[int] = 4096
DEFAULT_ENCODING: Final[str] = 'utf-8'
UNICODE_NORMALIZATION_FORM: Final[Literal['NFC', 'NFD', 'NFKC', 'NFKD']] = 'NFC'

# Type guards
def is_valid_doi(value: Any) -> bool:
    """Check if value is a valid DOI."""
    if not isinstance(value, str):
        return False
    return value.startswith('10.') and '/' in value


def is_valid_arxiv_id(value: Any) -> bool:
    """Check if value is a valid arXiv ID."""
    if not isinstance(value, str):
        return False
    # Simple check - real validation would be more complex
    return bool(value) and ('.' in value or value.isdigit())


def is_json_serializable(value: Any) -> bool:
    """Check if value is JSON serializable."""
    try:
        import json
        json.dumps(value)
        return True
    except (TypeError, ValueError):
        return False


# Type conversion utilities
def ensure_path(value: FilePath) -> Path:
    """Ensure value is a Path object."""
    return Path(value) if isinstance(value, str) else value


def ensure_list(value: Union[T, List[T]]) -> List[T]:
    """Ensure value is a list."""
    return value if isinstance(value, list) else [value]


def ensure_dict(value: Union[Dict[str, T], Any], default: Dict[str, T] = None) -> Dict[str, T]:
    """Ensure value is a dictionary."""
    if isinstance(value, dict):
        return value
    return default or {}


# Type aliases for common function signatures
ErrorHandler: TypeAlias = Callable[[Exception], Optional[Any]]
ProgressCallback: TypeAlias = Callable[[float, str], None]
FilterFunc: TypeAlias = Callable[[T], bool]
TransformFunc: TypeAlias = Callable[[T], T]
AsyncFunc: TypeAlias = Callable[..., Any]  # For async functions