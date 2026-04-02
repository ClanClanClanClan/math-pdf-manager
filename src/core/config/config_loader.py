#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration Loading Module
Phase 1, Week 2: Extracted from main.py to reduce file size

Handles all configuration loading, word list loading, and validation.
"""

import yaml
from pathlib import Path
from typing import Set, Dict, Any, Optional
from unicodedata import normalize

from core.utils.service_registry import get_logging_service, get_file_service, get_config_service
from core.dependency_injection import IConfigurationService

# Constants from main.py
DEFAULT_CONFIG_FILE = "config.yaml"
DEFAULT_KNOWN_WORDS_FILE = "known_words.txt"
DEFAULT_NAME_DASH_WHITELIST_FILE = "name_dash_whitelist.txt"
DEFAULT_MULTIWORD_FAMILYNAMES_FILE = "multiword_familynames.txt"


def normalize_nfc_cached(text: str) -> str:
    """Cache Unicode NFC normalization for performance."""
    if text is None:
        return ""
    return normalize("NFC", str(text))


def load_yaml_config_secure(config_path: str, config_service: Optional[IConfigurationService] = None) -> dict:
    """
    Load YAML configuration with comprehensive error handling and malformed YAML extraction.

    This function safely loads YAML configuration files and can extract useful data
    even from malformed YAML files that contain loose list items.

    Args:
        config_path: Path to the YAML configuration file
        config_service: Optional configuration service for advanced processing

    Returns:
        Dictionary containing configuration data
    """
    # Get services from registry
    logging_service = get_logging_service()
    file_service = get_file_service()
    
    if not config_path:
        logging_service.warning("No config path provided")
        return {}

    # Use file service to check if config exists
    config_file = Path(config_path)
    if not file_service.exists(config_file):
        logging_service.warning(f"Config file not found: {config_path}")
        return {}

    try:
        # Security check: validate file size (prevent loading huge files)
        config_stats = config_file.stat()
        max_config_size = 1_000_000  # 1MB limit
        if config_stats.st_size > max_config_size:
            logging_service.error(
                f"Configuration file too large: {config_stats.st_size} bytes "
                f"(max: {max_config_size} bytes)"
            )
            return {}
        
        # Use file service to read content
        content = file_service.read_file(config_file)

        if not content.strip():
            logging_service.warning(f"Config file is empty: {config_path}")
            return {}

        try:
            # Use config service if available, otherwise fallback to direct YAML
            if config_service:
                # Try to use config service for YAML parsing
                cfg = config_service.get_section('root', yaml.safe_load(content))
            else:
                # Fallback for when config service not available
                cfg = yaml.safe_load(content)
            if cfg is None:
                cfg = {}
            if not isinstance(cfg, dict):
                logging_service.warning(
                    f"Config file should contain a dictionary, got {type(cfg)}"
                )
                cfg = {}

            logging_service.info(f"✓ Config loaded with {len(cfg)} keys")

            # Try to extract malformed lists from comments/loose items
            extracted_lists = extract_malformed_lists(content)
            if extracted_lists:
                cfg.update(extracted_lists)
                logging_service.info(f"✓ Also extracted {len(extracted_lists)} malformed lists")

            return cfg

        except yaml.YAMLError as e:
            logging_service.error(f"YAML parsing failed: {e}")
            # Try to extract what we can from malformed YAML
            extracted = extract_malformed_lists(content)
            if extracted:
                logging_service.info(f"✓ Extracted {len(extracted)} lists from malformed YAML")
                return extracted
            return {}

    except Exception as e:
        logging_service.error(f"Failed to load config: {e}")
        return {}


def extract_malformed_lists(content: str) -> dict:
    """
    Extract useful lists from malformed YAML content.

    This function tries to extract list items that might be floating
    outside of proper YAML structure, such as commented lists or
    loose list items.

    Args:
        content: Raw YAML file content

    Returns:
        Dictionary with extracted lists
    """
    # Get services from registry
    logging_service = get_logging_service()
    
    extracted = {}

    # Look for patterns like loose list items after comments
    lines = content.split("\n")
    current_list = []
    current_key = None

    for line in lines:
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Check for comment indicating list type
        if line.startswith("#"):
            # Finish previous list if any
            if current_list and current_key:
                extracted[current_key] = current_list
                current_list = []

            # Determine list type from comment
            comment_lower = line.lower()
            if "mathematician" in comment_lower or "names" in comment_lower:
                current_key = "capitalization_whitelist_from_comments"
            elif "math" in comment_lower and "term" in comment_lower:
                current_key = "math_terms_from_comments"
            elif "roman" in comment_lower and "numeral" in comment_lower:
                current_key = "roman_numerals_from_comments"
            elif "german" in comment_lower and "noun" in comment_lower:
                current_key = "german_nouns_from_comments"
            elif "exception" in comment_lower:
                current_key = "exceptions_from_comments"
            else:
                current_key = "capitalization_whitelist_from_comments"  # Default

        # Check for list items
        elif line.startswith("- "):
            item = line[2:].strip()
            if item and current_key:
                current_list.append(item)

    # Finish last list
    if current_list and current_key:
        extracted[current_key] = current_list

    if extracted:
        logging_service.info(f"✓ Extracted {len(extracted)} lists from malformed YAML")
        for key, items in extracted.items():
            logging_service.info(f"  {key}: {len(items)} items")

    return extracted


def load_words_file_fixed(
    path: str | None, base_dir: str | None = None, description: str = "word file"
) -> Set[str]:
    """Load words file with better path resolution and error reporting."""
    # Get services from registry
    logging_service = get_logging_service()
    file_service = get_file_service()
    
    if not path:
        logging_service.info(f"No path specified for {description}")
        return set()

    # Better path resolution
    resolved_path = Path(path)
    if not resolved_path.is_absolute() and base_dir:
        resolved_path = Path(base_dir) / resolved_path

    resolved_path = resolved_path.resolve()
    logging_service.info(f"Loading {description}: {resolved_path}")

    if not resolved_path.exists():
        logging_service.warning(f"{description} not found: {resolved_path}")

        # Try alternative locations
        alternatives = [
            Path.cwd() / path,
            Path(__file__).parent / path,
            Path.home() / ".math_pdf_manager" / path,
        ]
        for alt in alternatives:
            if alt.exists():
                logging_service.info(f"Found {description} at: {alt}")
                resolved_path = alt
                break
        else:
            logging_service.warning(f"No {description} found in any location")
            return set()

    try:
        # Use injected file service for file operations
        content = file_service.read_file(resolved_path)
        words = {
            normalize_nfc_cached(line.strip())
            for line in content.split('\n')
            if line.strip() and not line.strip().startswith("#")
        }

        logging_service.info(f"✓ Loaded {len(words)} words from {description}")
        return words

    except Exception as e:
        logging_service.error(f"Failed to load {description} from {resolved_path}: {e}")
        return set()


def load_config_list(config: dict, key: str, default=None) -> set:
    """Load a list from config and convert to set."""
    # Get services from registry
    logging_service = get_logging_service()
    
    if default is None:
        default = []

    raw_data = config.get(key, default)
    if isinstance(raw_data, (list, set)):
        result = set(raw_data)
        if result:
            logging_service.info(f"✓ Loaded {len(result)} items from config key '{key}'")
        return result
    elif raw_data is None:
        return set()
    else:
        logging_service.warning(f"Config key '{key}' should be a list, got {type(raw_data)}")
        return set()


class ConfigurationData:
    """Container for all loaded configuration data."""
    
    def __init__(self):
        self.config: Dict[str, Any] = {}
        self.known_words: Set[str] = set()
        self.name_dash_whitelist: Set[str] = set()
        self.multiword_surnames: Set[str] = set()
        self.exceptions: Set[str] = set()
        self.compound_terms: Set[str] = set()
        self.capitalization_whitelist: Set[str] = set()
    
    def load_all(self, args, script_dir: Path) -> None:
        """Load all configuration data."""
        logging_service = get_logging_service()
        config_service = get_config_service()
        
        # Load main config
        logging_service.info("=== Loading Configuration ===")
        cfg_path = Path(DEFAULT_CONFIG_FILE)
        self.config = load_yaml_config_secure(str(cfg_path), config_service)
        
        # Load word files
        logging_service.info("=== Loading Word Files ===")
        self.known_words = load_words_file_fixed(
            self.config.get("known_words_file", DEFAULT_KNOWN_WORDS_FILE),
            str(script_dir),
            "known words file",
        )
        
        self.name_dash_whitelist = load_words_file_fixed(
            self.config.get("name_dash_whitelist_file", DEFAULT_NAME_DASH_WHITELIST_FILE),
            str(script_dir),
            "name dash whitelist file",
        )
        
        self.multiword_surnames = load_words_file_fixed(
            self.config.get("multiword_familynames_file", DEFAULT_MULTIWORD_FAMILYNAMES_FILE),
            str(script_dir),
            "multiword family names file",
        )
        
        # Load exceptions
        logging_service.info("=== Loading Exception Lists ===")
        if args.exceptions_file:
            self.exceptions.update(
                load_words_file_fixed(
                    args.exceptions_file, str(script_dir), "CLI exceptions file"
                )
            )
        
        cfg_exc = (
            self.config.get("exceptions_file")
            or self.config.get("exceptions_list")
            or self.config.get("exceptions")
        )
        if isinstance(cfg_exc, str):
            self.exceptions.update(
                load_words_file_fixed(cfg_exc, str(script_dir), "config exceptions file")
            )
        elif isinstance(cfg_exc, (list, set)):
            self.exceptions.update({normalize_nfc_cached(w) for w in cfg_exc})
            logging_service.info(f"✓ Added {len(cfg_exc)} exceptions from config")
        
        # Load compound terms
        logging_service.info("=== Loading Compound Terms ===")
        self.compound_terms = load_config_list(self.config, "compound_terms")
        
        # Load and combine all capitalization lists
        logging_service.info("=== Loading ALL Capitalization Lists ===")
        self._load_capitalization_lists()
        
        # Log final counts
        logging_service.info("=== FINAL WORD LIST COUNTS ===")
        logging_service.info(f"Known words: {len(self.known_words)}")
        logging_service.info(f"Name dash whitelist: {len(self.name_dash_whitelist)}")
        logging_service.info(f"Multiword surnames: {len(self.multiword_surnames)}")
        logging_service.info(f"Exceptions: {len(self.exceptions)}")
        logging_service.info(f"Compound terms: {len(self.compound_terms)}")
        logging_service.info(f"Capitalization whitelist (COMBINED): {len(self.capitalization_whitelist)}")
    
    def _load_capitalization_lists(self) -> None:
        """Load and combine all capitalization-related word lists."""
        logging_service = get_logging_service()
        
        # List of all config lists that should be included
        config_word_lists = [
            ("capitalization_whitelist", "Core capitalization whitelist"),
            ("compound_terms", "Compound terms (hyphenated words)"),
            ("common_acronyms", "Common acronyms"),
            ("mixed_case_words", "Mixed case words"),
            ("proper_adjectives", "Proper adjectives"),
            # These might exist from malformed YAML extraction
            ("capitalization_whitelist_from_comments", "Extracted from comments"),
            ("math_terms_from_comments", "Math terms from comments"),
            ("roman_numerals_from_comments", "Roman numerals from comments"),
            ("german_nouns_from_comments", "German nouns from comments"),
            ("exceptions_from_comments", "Exceptions from comments"),
        ]
        
        total_loaded = 0
        for list_key, description in config_word_lists:
            if list_key in self.config:
                word_list = self.config[list_key]
                if isinstance(word_list, (list, set)):
                    words = set(word_list)
                    self.capitalization_whitelist.update(words)
                    total_loaded += len(words)
                    logging_service.info(f"✓ Added {description}: {len(words)} items")
                else:
                    logging_service.warning(f"⚠️  {list_key} is not a list ({type(word_list)})")
        
        logging_service.info(f"✓ Total words loaded from config: {total_loaded}")
        logging_service.info(
            f"✓ Combined capitalization_whitelist: {len(self.capitalization_whitelist)} unique items"
        )