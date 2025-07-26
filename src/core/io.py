#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/io.py - File I/O Operations
Extracted from utils.py to improve modularity
"""

import os
import logging
import yaml
from typing import Dict, Set

# Initialize logger
logger = logging.getLogger(__name__)


def load_yaml_config(path: str) -> Dict:
    """Load YAML configuration file safely."""
    path = os.path.expanduser(path)
    try:
        with open(path, encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except Exception as exc:  # noqa: BLE001 – robust helper
        logger.error("Unable to read %s: %s", path, exc)
        return {}


def load_word_list(path: str) -> Set[str]:
    """Load word list from file with duplicate checking."""
    path = os.path.expanduser(path)
    out: Set[str] = set()
    try:
        with open(path, encoding="utf-8") as fh:
            for i, raw in enumerate(fh, 1):
                s = raw.strip()
                if not s or s.startswith("#"):
                    continue
                if s in out:
                    logger.warning("Duplicate in %s line %d: %r", path, i, s)
                out.add(s)
    except Exception as exc:  # noqa: BLE001
        logger.error("Unable to read %s: %s", path, exc)
    return out


def debug_print(msg: str) -> None:
    """Print debug message if debugging is enabled."""
    # Import here to avoid circular dependency
    try:
        import core.sentence_case
        if hasattr(core.sentence_case, 'DEBUG_SENTENCE_CASE') and core.sentence_case.DEBUG_SENTENCE_CASE:
            print(f"[DEBUG] {msg}")
    except ImportError:
        # Fallback to utils module
        try:
            from utils import DEBUG_SENTENCE_CASE
            if DEBUG_SENTENCE_CASE:
                print(f"[DEBUG] {msg}")
        except ImportError:
            # If neither is available, don't print debug messages
            pass


# Export all functions
__all__ = [
    'load_yaml_config',
    'load_word_list', 
    'debug_print'
]