#!/usr/bin/env python3
"""
Secure File Operations
======================

Provides secure file operations with path validation and injection prevention.
"""

import os
import stat
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Union
import logging
import json

logger = logging.getLogger(__name__)


class SecureFileOperations:
    """Secure file operations with path validation and sanitization."""
    
    def __init__(self, allowed_base_paths: list = None):
        """Initialize with allowed base paths for file operations."""
        self.allowed_base_paths = [Path(p).resolve() for p in (allowed_base_paths or [])]
        # Add current working directory and common safe directories
        self.allowed_base_paths.extend([
            Path.cwd().resolve(),
            Path.home() / '.cache',
            Path(tempfile.gettempdir()).resolve()  # Use secure temp dir instead of hardcoded /tmp
        ])
    
    def _validate_path(self, file_path: Union[str, Path]) -> Path:
        """
        Validate that file path is safe and within allowed directories.
        
        Prevents:
        - Path traversal attacks (../)
        - Absolute paths to system directories
        - Symlink attacks
        """
        file_path = Path(file_path).resolve()
        
        # Check for path traversal
        if '..' in str(file_path):
            raise ValueError(f"Path traversal detected: {file_path}")
        
        # Ensure path is within allowed base paths
        allowed = False
        for base_path in self.allowed_base_paths:
            try:
                file_path.relative_to(base_path)
                allowed = True
                break
            except ValueError:
                continue
        
        if not allowed:
            raise ValueError(f"Path not in allowed directories: {file_path}")
        
        # Check for symlink attacks
        if file_path.exists() and file_path.is_symlink():
            real_path = file_path.readlink().resolve()
            # If symlink points outside allowed directories, this will raise ValueError
            self._validate_path(real_path)  # Recursively validate symlink target
        
        return file_path
    
    def secure_write(self, file_path: Union[str, Path], content: Union[str, bytes, Dict], 
                    mode: str = 'w', encoding: str = 'utf-8', 
                    permissions: int = 0o600) -> bool:
        """
        Securely write content to file with validation.
        
        Args:
            file_path: Path to write to
            content: Content to write (str, bytes, or dict for JSON)
            mode: File mode ('w', 'wb', etc.)
            encoding: Text encoding
            permissions: File permissions (default: owner-only read/write)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            validated_path = self._validate_path(file_path)
            
            # Create parent directories if needed
            validated_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write content
            if isinstance(content, dict):
                # JSON content
                with open(validated_path, 'w', encoding=encoding) as f:
                    json.dump(content, f, ensure_ascii=False, indent=2)
            elif mode.startswith('w') and isinstance(content, str):
                # Text content
                with open(validated_path, mode, encoding=encoding) as f:
                    f.write(content)
            elif mode.startswith('wb') and isinstance(content, bytes):
                # Binary content
                with open(validated_path, mode) as f:
                    f.write(content)
            else:
                raise ValueError(f"Invalid content type {type(content)} for mode {mode}")
            
            # Set secure permissions
            validated_path.chmod(permissions)
            
            logger.debug(f"Securely wrote to {validated_path}")
            return True
            
        except ValueError as e:
            # Re-raise security validation errors
            logger.error(f"Security violation in write to {file_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to securely write to {file_path}: {e}")
            return False
    
    def secure_read(self, file_path: Union[str, Path], mode: str = 'r', 
                   encoding: str = 'utf-8', max_size: int = 100 * 1024 * 1024) -> Optional[Any]:
        """
        Securely read content from file with validation.
        
        Args:
            file_path: Path to read from
            mode: File mode ('r', 'rb', etc.)
            encoding: Text encoding
            max_size: Maximum file size to read (default: 100MB)
        
        Returns:
            File content or None if failed
        """
        try:
            validated_path = self._validate_path(file_path)
            
            if not validated_path.exists():
                logger.warning(f"File does not exist: {validated_path}")
                return None
            
            # Check file size
            file_size = validated_path.stat().st_size
            if file_size > max_size:
                logger.error(f"File too large: {file_size} > {max_size}")
                return None
            
            # Read content
            if mode.startswith('r') and mode != 'rb':
                # Text content
                with open(validated_path, mode, encoding=encoding) as f:
                    content = f.read()
                    
                # Try to parse as JSON if it looks like JSON
                if content.strip().startswith(('{', '[')):
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        pass  # Return as text
                
                return content
            
            elif mode == 'rb':
                # Binary content
                with open(validated_path, mode) as f:
                    return f.read()
            
            else:
                raise ValueError(f"Unsupported file mode: {mode}")
                
        except ValueError as e:
            # Re-raise security validation errors
            logger.error(f"Security violation in read from {file_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to securely read from {file_path}: {e}")
            return None
    
    def secure_delete(self, file_path: Union[str, Path]) -> bool:
        """
        Securely delete file with validation.
        
        Args:
            file_path: Path to delete
        
        Returns:
            True if successful, False otherwise
        """
        try:
            validated_path = self._validate_path(file_path)
            
            if not validated_path.exists():
                return True  # Already deleted
            
            # Secure deletion for sensitive files
            if validated_path.is_file():
                # Overwrite with random data before deletion (basic secure delete)
                file_size = validated_path.stat().st_size
                if file_size < 1024 * 1024:  # Only for files < 1MB
                    with open(validated_path, 'wb') as f:
                        f.write(os.urandom(file_size))
                        f.flush()
                        os.fsync(f.fileno())
                
                validated_path.unlink()
            elif validated_path.is_dir():
                # Remove directory (only if empty)
                validated_path.rmdir()
            
            logger.debug(f"Securely deleted {validated_path}")
            return True
            
        except ValueError as e:
            # Re-raise security validation errors
            logger.error(f"Security violation in delete of {file_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to securely delete {file_path}: {e}")
            return False
    
    def validate_file_permissions(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Validate file permissions for security issues.
        
        Returns:
            Dictionary with permission analysis
        """
        try:
            validated_path = self._validate_path(file_path)
            
            if not validated_path.exists():
                return {"error": "File does not exist"}
            
            file_stat = validated_path.stat()
            file_mode = stat.filemode(file_stat.st_mode)
            octal_mode = oct(file_stat.st_mode)[-3:]
            
            # Check for insecure permissions
            issues = []
            
            # Check if world-readable
            if file_stat.st_mode & stat.S_IROTH:
                issues.append("World-readable")
            
            # Check if world-writable
            if file_stat.st_mode & stat.S_IWOTH:
                issues.append("World-writable")
            
            # Check if group-writable
            if file_stat.st_mode & stat.S_IWGRP:
                issues.append("Group-writable")
            
            # Check if executable when it shouldn't be
            if validated_path.suffix in ['.txt', '.json', '.yaml', '.yml', '.conf']:
                if file_stat.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
                    issues.append("Unnecessarily executable")
            
            return {
                "path": str(validated_path),
                "mode": file_mode,
                "octal": octal_mode,
                "issues": issues,
                "secure": len(issues) == 0
            }
            
        except Exception as e:
            return {"error": str(e)}


# Global instance for convenience
_secure_file_ops = SecureFileOperations()

def secure_write(file_path: Union[str, Path], content: Union[str, bytes, Dict], **kwargs) -> bool:
    """Convenience function for secure file writing."""
    return _secure_file_ops.secure_write(file_path, content, **kwargs)

def secure_read(file_path: Union[str, Path], **kwargs) -> Optional[Any]:
    """Convenience function for secure file reading."""
    return _secure_file_ops.secure_read(file_path, **kwargs)

def secure_delete(file_path: Union[str, Path]) -> bool:
    """Convenience function for secure file deletion."""
    return _secure_file_ops.secure_delete(file_path)

def validate_permissions(file_path: Union[str, Path]) -> Dict[str, Any]:
    """Convenience function for permission validation."""
    return _secure_file_ops.validate_file_permissions(file_path)