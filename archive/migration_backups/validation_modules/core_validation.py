#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validation Module
Phase 1, Week 2: Extracted from main.py to reduce file size

Handles input validation for CLI arguments and paths.
"""

import os
from pathlib import Path

from src.core.utils.service_registry import get_logging_service


def validate_cli_inputs(args) -> bool:
    """Validate command-line arguments for safety with stricter path traversal detection."""
    # Get services from registry
    logging_service = get_logging_service()
    
    if hasattr(args, "root") and args.root:
        try:
            # Check for path traversal BEFORE resolving the path
            raw_path = str(args.root)
            if ".." in raw_path:
                logging_service.error("Path traversal detected in root argument")
                return False

            # Also check after resolution
            root_path = Path(args.root).expanduser().resolve()
            root_str = str(root_path)

            # Additional checks for resolved path
            if ".." in root_str:
                logging_service.error("Path traversal detected in resolved root argument")
                return False

            # Ensure reasonable path length
            if len(root_str) > 1000:
                logging_service.error("Root path too long (potential attack)")
                return False

        except Exception as e:
            logging_service.error(f"Invalid root path: {args.root} ({e})")
            return False

    # Validate output file paths
    for output_arg in ["output", "csv_output"]:
        if hasattr(args, output_arg):
            output_path = getattr(args, output_arg, None)
            if output_path:
                try:
                    # Check raw path first
                    if ".." in str(output_path):
                        logging_service.error(
                            f"Path traversal detected in {output_arg}: {output_path}"
                        )
                        return False

                    out_path = Path(output_path).resolve()
                    out_str = str(out_path)
                    if ".." in out_str or len(out_str) > 500:
                        logging_service.error(f"Invalid output path: {output_path}")
                        return False
                except Exception:
                    logging_service.error(f"Cannot resolve output path: {output_path}")
                    return False

    return True


def validate_template_dir(template_dir: str) -> bool:
    """Validate template directory exists and is safe."""
    # Get services from registry
    logging_service = get_logging_service()
    
    try:
        tmpl_path = Path(template_dir).resolve()

        if not tmpl_path.exists():
            logging_service.warning(f"Template directory does not exist: {template_dir}")
            logging_service.info("Reports will use default templates")
            return False

        if not tmpl_path.is_dir():
            logging_service.error(f"Template path is not a directory: {template_dir}")
            return False

        if not os.access(tmpl_path, os.R_OK):
            logging_service.error(f"Cannot read template directory: {template_dir}")
            return False

        logging_service.info(f"Using template directory: {template_dir}")
        return True

    except Exception as e:
        logging_service.error(f"Template directory validation failed: {e}")
        return False