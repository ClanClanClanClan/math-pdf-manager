#!/usr/bin/env python3
"""
Configuration Migration Module
Provides compatibility layer to migrate from old ConfigurationData to new ConfigManager.
"""

from pathlib import Path
from typing import Set, Dict, Any, Optional
import unicodedata

from ..config_manager import get_config, get_config_value


class ConfigurationData:
    """
    Compatibility wrapper that mimics the old ConfigurationData interface
    but uses the new simplified ConfigManager internally.
    """
    
    def __init__(self):
        # Load from new config manager
        self._config_manager = get_config()
        
        # Initialize sets (will be populated in load_all)
        self.config: Dict[str, Any] = {}
        self.known_words: Set[str] = set()
        self.name_dash_whitelist: Set[str] = set()
        self.multiword_surnames: Set[str] = set()
        self.exceptions: Set[str] = set()
        self.compound_terms: Set[str] = set()
        self.capitalization_whitelist: Set[str] = set()
    
    def load_all(self, args, script_dir: Path) -> None:
        """Load all configuration data using the new config manager."""
        # Get the unified config
        cfg = self._config_manager
        
        # Populate the legacy config dict
        self.config = {
            'known_words_file': cfg.known_words_file,
            'name_dash_whitelist_file': cfg.name_dash_whitelist_file,
            'multiword_familynames_file': cfg.multiword_familynames_file,
            'exceptions_file': cfg.exceptions_file,
            'template_dir': cfg.template_dir,
            'base_maths_folder': cfg.base_maths_folder,
            'enable_spellcheck': cfg.enable_spellcheck,
            'backup_enabled': cfg.backup_enabled,
            'dry_run_default': cfg.dry_run_default,
        }
        
        # Load word files if they exist
        self.known_words = self._load_word_file(cfg.known_words_file, "known words")
        self.name_dash_whitelist = self._load_word_file(cfg.name_dash_whitelist_file, "name dash whitelist")
        self.multiword_surnames = self._load_word_file(cfg.multiword_familynames_file, "multiword surnames")
        
        # Load exceptions from file or args
        if args.exceptions_file:
            self.exceptions.update(self._load_word_file(args.exceptions_file, "CLI exceptions"))
        elif cfg.exceptions_file:
            self.exceptions.update(self._load_word_file(cfg.exceptions_file, "config exceptions"))
        
        # Use the lists from config directly
        self.compound_terms = set(cfg.compound_terms)
        self.capitalization_whitelist = set(cfg.capitalization_whitelist)
        
        # Add other lists to capitalization whitelist
        self.capitalization_whitelist.update(cfg.common_acronyms)
        self.capitalization_whitelist.update(cfg.mixed_case_words)
        self.capitalization_whitelist.update(cfg.proper_adjectives)
        
        # Log summary (simplified)
        print(f"✓ Loaded configuration:")
        print(f"  Known words: {len(self.known_words)}")
        print(f"  Capitalization whitelist: {len(self.capitalization_whitelist)}")
        print(f"  Exceptions: {len(self.exceptions)}")
        print(f"  Compound terms: {len(self.compound_terms)}")
    
    def _load_word_file(self, file_path: str, description: str) -> Set[str]:
        """Load words from a file."""
        words = set()
        
        if not file_path:
            return words
        
        path = Path(file_path)
        if not path.exists():
            print(f"⚠ {description} file not found: {file_path}")
            return words
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Normalize to NFC
                        words.add(unicodedata.normalize('NFC', line))
            
            print(f"✓ Loaded {len(words)} items from {description}")
        except Exception as e:
            print(f"⚠ Error loading {description}: {e}")
        
        return words
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.config.get(key, default)


def load_configuration(args, script_dir: Path) -> ConfigurationData:
    """
    Load configuration using the new system but return old interface.
    This allows gradual migration of the codebase.
    """
    config_data = ConfigurationData()
    config_data.load_all(args, script_dir)
    return config_data