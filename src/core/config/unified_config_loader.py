#!/usr/bin/env python3
"""
Unified Configuration Loader

Replaces the monolithic 1,573-line config.yaml with a modular configuration system.
Loads and merges configuration from multiple focused files for better maintainability.
"""

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover
    raise RuntimeError(
        "PyYAML is required to load configuration files. Install it with `pip install -r requirements.txt` "
        "before running the CLI."
    ) from exc

logger = logging.getLogger(__name__)


class UnifiedConfigLoader:
    """Loads and manages configuration from multiple modular YAML files"""

    def __init__(self, config_dir: Path | None = None):
        if config_dir is None:
            # Default to the config directory relative to the script root
            script_root = Path(__file__).parent.parent.parent.parent
            config_dir = script_root / "config"

        self.config_dir = Path(config_dir)
        self._config_cache = {}
        self._last_modified = {}

    def _expand_path(self, path_str: str) -> str:
        """Expand ~ and environment variables in path strings"""
        if path_str.startswith("~/"):
            return str(Path.home() / path_str[2:])
        return os.path.expandvars(path_str)

    def _process_paths(self, config: dict[str, Any]) -> dict[str, Any]:
        """Recursively expand paths in configuration"""
        processed = {}

        for key, value in config.items():
            if isinstance(value, str) and (
                value.startswith("~/") or
                "$" in value or
                key.endswith("_file") or
                key.endswith("_dir") or
                key.endswith("_folder") or
                key.endswith("_path")
            ):
                processed[key] = self._expand_path(value)
            elif isinstance(value, dict):
                processed[key] = self._process_paths(value)
            elif isinstance(value, list):
                processed[key] = [
                    self._expand_path(item) if isinstance(item, str) and item.startswith("~/") else item
                    for item in value
                ]
            else:
                processed[key] = value

        return processed

    def _load_yaml_file(self, file_path: Path) -> dict[str, Any]:
        """Load a single YAML file with caching and modification time checking"""
        if not file_path.exists():
            logger.warning(f"Configuration file not found: {file_path}")
            return {}

        # Check if file has been modified
        current_mtime = file_path.stat().st_mtime
        cache_key = str(file_path)

        if (cache_key in self._config_cache and
            cache_key in self._last_modified and
            self._last_modified[cache_key] == current_mtime):
            return self._config_cache[cache_key]

        try:
            with open(file_path, encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}

            # Process paths
            config = self._process_paths(config)

            # Cache the result
            self._config_cache[cache_key] = config
            self._last_modified[cache_key] = current_mtime

            logger.debug(f"Loaded configuration from: {file_path}")
            return config

        except Exception as e:
            logger.error(f"Failed to load configuration from {file_path}: {e}")
            return {}

    def _merge_configs(self, base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
        """Deep merge two configuration dictionaries"""
        result = base.copy()

        for key, value in overlay.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value

        return result

    @lru_cache(maxsize=1)
    def load_full_config(self) -> dict[str, Any]:
        """Load and merge all configuration files into a single configuration"""
        logger.info("Loading unified configuration from modular files...")

        # Define the configuration files in load order
        config_files = [
            "core.yaml",                # Core system settings
            "academic_vocabulary.yaml", # Academic names and terms
            "technical_terms.yaml",     # Technical acronyms
            "language_rules.yaml",      # Language processing rules
        ]

        # Start with empty configuration
        unified_config = {}

        # Load and merge each configuration file
        for config_file in config_files:
            file_path = self.config_dir / config_file
            file_config = self._load_yaml_file(file_path)

            if file_config:
                unified_config = self._merge_configs(unified_config, file_config)
                logger.debug(f"Merged configuration from: {config_file}")

        # Fallback to legacy config.yaml if modular files don't exist
        if not unified_config:
            logger.warning("No modular config files found, falling back to legacy config.yaml")
            legacy_config_path = self.config_dir / "config.yaml"
            unified_config = self._load_yaml_file(legacy_config_path)

        logger.info(f"Configuration loaded successfully with {len(unified_config)} top-level keys")
        return unified_config

    def get_config(self, section: str | None = None) -> Any:
        """Get configuration, optionally for a specific section"""
        config = self.load_full_config()

        if section is None:
            return config

        return config.get(section)

    def reload_config(self):
        """Force reload of all configuration files"""
        self._config_cache.clear()
        self._last_modified.clear()
        self.load_full_config.cache_clear()
        logger.info("Configuration cache cleared and reloaded")


# Global configuration loader instance
_config_loader = None

def get_config_loader() -> UnifiedConfigLoader:
    """Get the global configuration loader instance"""
    global _config_loader
    if _config_loader is None:
        _config_loader = UnifiedConfigLoader()
    return _config_loader

def get_config(section: str | None = None) -> Any:
    """Convenience function to get configuration"""
    return get_config_loader().get_config(section)

def reload_config():
    """Convenience function to reload configuration"""
    get_config_loader().reload_config()


# Backward compatibility - maintain the old interface
def load_config() -> dict[str, Any]:
    """Legacy function for backward compatibility"""
    return get_config()


if __name__ == "__main__":
    # Test the configuration loader
    logging.basicConfig(level=logging.INFO)

    loader = UnifiedConfigLoader()
    config = loader.load_full_config()

    print("✅ Configuration loaded successfully!")
    print(f"   - Top-level keys: {list(config.keys())}")
    print(f"   - Base folder: {config.get('base_maths_folder', 'Not found')}")
    print(f"   - Academic names count: {len(config.get('capitalization_whitelist', []))}")
    print(f"   - Technical acronyms count: {len(config.get('common_acronyms', []))}")
