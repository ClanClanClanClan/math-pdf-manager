#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File Operations Module
Phase 1, Week 2: Extracted from main.py to reduce file size

Handles file operations, path handling, and metadata processing.
"""

import os
from pathlib import Path
from typing import Any, List

from src.core.utils.service_registry import get_logging_service

# Dropbox migration paths
DROPBOX_OLD_PATH = Path.home() / "Dropbox"
DROPBOX_NEW_PATH = Path.home() / "Library/CloudStorage/Dropbox"


def migrate_dropbox(p: str | Path) -> str:
    """Migrate Dropbox paths with improved error handling."""
    # Get services from registry
    logging_service = get_logging_service()
    
    try:
        p = Path(p).expanduser().resolve()

        # Validate path doesn't contain suspicious components
        if any(part.startswith(".") and len(part) > 2 for part in p.parts):
            logging_service.warning(f"Suspicious path component detected: {p}")
            return str(p)

        if p.is_absolute() and DROPBOX_OLD_PATH in p.parents and not p.exists():
            alt = DROPBOX_NEW_PATH / p.relative_to(DROPBOX_OLD_PATH)
            if alt.exists():
                logging_service.info(f"Migrated Dropbox path: {p} → {alt}")
                return str(alt)

    except (ValueError, OSError) as e:
        logging_service.warning(f"Path migration failed for {p}: {e}")

    return str(p)


def resolve_path(p: str | Path | None, base: str | Path | None = None) -> str | None:
    """Resolve path with improved error handling."""
    if not p:
        return None
    p = os.path.expanduser(str(p))
    if not os.path.isabs(p) and base:
        p = os.path.join(os.path.expanduser(base), p)
    return os.path.abspath(migrate_dropbox(p))


def safe_file_rename(old_path: Path, new_path: Path, create_backup: bool = False) -> bool:
    """Safely rename file with specific error handling and optional backup."""
    # Get services from registry
    logging_service = get_logging_service()
    
    try:
        # Check permissions before attempting rename
        if not os.access(old_path.parent, os.W_OK):
            logging_service.error(f"No write permission in directory: {old_path.parent}")
            return False

        # Check if target already exists
        if new_path.exists():
            logging_service.error(f"Target file already exists: {new_path}")
            return False

        # Create backup if requested
        if create_backup:
            backup_path = old_path.with_suffix(old_path.suffix + '.backup')
            counter = 1
            while backup_path.exists():
                backup_path = old_path.with_suffix(f"{old_path.suffix}.backup{counter}")
                counter += 1
            
            import shutil
            shutil.copy2(old_path, backup_path)
            logging_service.info(f"Created backup: {backup_path.name}")

        # Perform the rename
        old_path.rename(new_path)
        logging_service.info(f"Renamed: {old_path.name} → {new_path.name}")
        return True

    except PermissionError:
        logging_service.error(f"Permission denied renaming: {old_path}")
    except FileNotFoundError:
        logging_service.error(f"Source file not found: {old_path}")
    except FileExistsError:
        logging_service.error(f"Target file exists: {new_path}")
    except OSError as e:
        logging_service.error(f"OS error renaming {old_path} → {new_path}: {e}")
    except Exception as e:
        logging_service.error(f"Unexpected error renaming {old_path}: {e}")

    return False


def normalize_file_metadata(files: List[dict[str, Any]]) -> List[dict[str, Any]]:
    """
    Normalize file metadata to handle different scanner implementations.
    
    This ensures consistent field names regardless of which scanner was used.
    Maps various field name variations to standard names.
    """
    normalized = []
    
    for file_dict in files:
        # Create normalized dict with standard field names
        norm_dict = {}
        
        # Handle filename variations
        norm_dict["filename"] = (
            file_dict.get("filename") or 
            file_dict.get("name") or 
            file_dict.get("file_name") or 
            "UNKNOWN"
        )
        
        # Handle path variations
        norm_dict["path"] = (
            file_dict.get("path") or 
            file_dict.get("filepath") or 
            file_dict.get("full_path") or 
            file_dict.get("absolute_path") or 
            ""
        )
        
        # Handle folder/directory variations
        norm_dict["folder"] = (
            file_dict.get("folder") or 
            file_dict.get("directory") or 
            file_dict.get("dir") or 
            file_dict.get("parent") or 
            ""
        )
        
        # Handle extension variations
        norm_dict["extension"] = (
            file_dict.get("extension") or 
            file_dict.get("ext") or 
            file_dict.get("suffix") or 
            ""
        )
        
        # Copy over any other fields that might exist
        for key, value in file_dict.items():
            if key not in ["filename", "name", "file_name", "path", "filepath", 
                          "full_path", "absolute_path", "folder", "directory", 
                          "dir", "parent", "extension", "ext", "suffix"]:
                norm_dict[key] = value
        
        # Ensure required fields exist with defaults
        norm_dict.setdefault("size", None)
        norm_dict.setdefault("is_symlink", False)
        norm_dict.setdefault("error", None)
        norm_dict.setdefault("path", "")
        norm_dict.setdefault("folder", "")
        norm_dict.setdefault("extension", "")
        
        normalized.append(norm_dict)
    
    return normalized