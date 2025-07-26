#!/usr/bin/env python3
"""
Dependency Injection Helper Functions for main.py
Phase 1, Week 2: Strategic Transformation

Helper functions that support the dependency injection refactoring of main.py.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional
from core.dependency_injection.interfaces import IValidationService

def validate_cli_inputs_di(args: argparse.Namespace, validation_service: IValidationService) -> bool:
    """
    Validate CLI inputs using dependency injection.
    
    Args:
        args: Parsed command line arguments
        validation_service: Injected validation service
        
    Returns:
        bool: True if inputs are valid, False otherwise
    """
    # Validate root path if provided
    if args.root:
        root_path = Path(args.root)
        if not root_path.exists():
            print(f"Error: Root path '{args.root}' does not exist")
            return False
        if not root_path.is_dir():
            print(f"Error: Root path '{args.root}' is not a directory")
            return False
    
    # Validate exceptions file if provided
    if args.exceptions_file:
        exceptions_path = Path(args.exceptions_file)
        # Convert Path to string for compatibility with validation service
        if not validation_service.validate_file_path(str(exceptions_path)):
            print(f"Error: Exceptions file '{args.exceptions_file}' is not valid")
            return False
    
    # Validate output paths
    output_path = Path(args.output)
    if output_path.exists() and not output_path.is_file():
        print(f"Error: Output path '{args.output}' exists but is not a file")
        return False
    
    csv_output_path = Path(args.csv_output)
    if csv_output_path.exists() and not csv_output_path.is_file():
        print(f"Error: CSV output path '{args.csv_output}' exists but is not a file")
        return False
    
    return True

def validate_template_dir_di(template_dir: str, validation_service: IValidationService) -> bool:
    """
    Validate template directory using dependency injection.
    
    Args:
        template_dir: Path to template directory
        validation_service: Injected validation service
        
    Returns:
        bool: True if template directory is valid, False otherwise
    """
    template_path = Path(template_dir)
    
    # Check if directory exists
    if not template_path.exists():
        print(f"Warning: Template directory '{template_dir}' does not exist")
        return False
    
    # Check if it's actually a directory
    if not template_path.is_dir():
        print(f"Error: Template path '{template_dir}' is not a directory")
        return False
    
    # Check if we can read the directory
    try:
        list(template_path.iterdir())
    except PermissionError:
        print(f"Error: No permission to read template directory '{template_dir}'")
        return False
    
    return True

def setup_environment_di() -> None:
    """
    Setup environment variables for the application.
    Enhanced version with dependency injection support.
    """
    # Environment configuration
    env_config = {
        "PYTHONWARNINGS": "ignore",
        "MPLBACKEND": "agg",
        "FITZ_IGNORE_NO_MUPDF": "1",
    }
    
    # Set environment variables
    for key, value in env_config.items():
        os.environ.setdefault(key, value)
    
    # Add current directory to Python path for imports
    current_dir = Path.cwd()
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))

def get_config_paths_di() -> dict[str, Path]:
    """
    Get standardized configuration file paths.
    
    Returns:
        dict: Dictionary of configuration file paths
    """
    script_dir = Path(__file__).parent
    
    return {
        'config_file': script_dir / "config.yaml",
        'known_words_file': script_dir / "known_words.txt",
        'name_dash_whitelist_file': script_dir / "name_dash_whitelist.txt",
        'multiword_familynames_file': script_dir / "multiword_familynames.txt",
    }

def resolve_dropbox_path_di(path: Path) -> Path:
    """
    Resolve Dropbox path migration for dependency injection.
    
    Args:
        path: Original path that might need migration
        
    Returns:
        Path: Resolved path (migrated if necessary)
    """
    dropbox_old_path = Path.home() / "Dropbox"
    dropbox_new_path = Path.home() / "Library/CloudStorage/Dropbox"
    
    # Check if path needs migration
    if str(path).startswith(str(dropbox_old_path)) and not path.exists():
        # Try the new path
        relative_path = path.relative_to(dropbox_old_path)
        new_path = dropbox_new_path / relative_path
        if new_path.exists():
            return new_path
    
    return path