#!/usr/bin/env python3
"""
Simple Configuration Manager
Replacement for the 3 complex configuration systems.

Provides clean, fast configuration loading with:
- Single YAML source of truth
- Environment variable overrides
- Type safety and validation
- Simple credential management
- No security theater
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover
    raise RuntimeError(
        "PyYAML is required to load configuration files. Install dependencies via "
        "`pip install -r requirements.txt` before running the CLI."
    ) from exc


@dataclass
class ConfigData:
    """Clean configuration data class."""

    # Core paths
    base_maths_folder: str = ""
    known_words_file: str = ""
    name_dash_whitelist_file: str = ""
    multiword_familynames_file: str = ""
    exceptions_file: str = ""
    template_dir: str = ""

    # Word lists (loaded from YAML)
    capitalization_whitelist: list[str] = field(default_factory=list)
    common_acronyms: list[str] = field(default_factory=list)
    mixed_case_words: list[str] = field(default_factory=list)
    proper_adjectives: list[str] = field(default_factory=list)
    compound_terms: list[str] = field(default_factory=list)

    # Settings
    enable_spellcheck: bool = True
    backup_enabled: bool = True
    dry_run_default: bool = True
    max_unpublished_age_years: int = 5

    # Folder organization
    folder_categories: dict[str, list[str]] = field(default_factory=dict)
    folder_shortcuts: dict[str, str | list[str]] = field(default_factory=dict)

    # Extraction settings
    extraction: dict[str, Any] = field(default_factory=dict)
    repositories: dict[str, Any] = field(default_factory=dict)
    scoring: dict[str, Any] = field(default_factory=dict)
    performance: dict[str, Any] = field(default_factory=dict)

    # External services
    grobid: dict[str, Any] = field(default_factory=dict)
    ocr: dict[str, Any] = field(default_factory=dict)
    google_scholar: dict[str, Any] = field(default_factory=dict)

    # Logging
    logging: dict[str, Any] = field(default_factory=dict)


class ConfigManager:
    """
    Simple configuration manager.

    Replaces 3 complex systems with one clean implementation.
    """

    def __init__(self, config_path: Path | None = None):
        self.config_path = config_path or self._find_config_file()
        self._config: ConfigData | None = None
        self._raw_config: dict[str, Any] | None = None

    def _find_config_file(self) -> Path:
        """Find the configuration file."""
        # Look in standard locations
        possible_paths = [
            Path.cwd() / "config.yaml",
            Path.cwd() / "config" / "config.yaml",
            Path(__file__).parent.parent.parent / "config" / "config.yaml",
        ]

        for path in possible_paths:
            if path.exists():
                return path

        raise FileNotFoundError("No config.yaml found in standard locations")

    def _expand_path(self, path_str: str) -> str:
        """Expand user paths and environment variables."""
        if not path_str:
            return path_str

        # Expand environment variables
        path_str = os.path.expandvars(path_str)

        # Expand user home directory
        path_str = os.path.expanduser(path_str)

        return path_str

    def _apply_env_overrides(self, config: dict[str, Any]) -> dict[str, Any]:
        """Apply environment variable overrides."""
        # Simple pattern: MATHPDF_SECTION_KEY overrides config[section][key]
        for key, value in os.environ.items():
            if not key.startswith("MATHPDF_"):
                continue

            # Parse MATHPDF_EXTRACTION_MAX_PAGES -> extraction.max_pages
            parts = key[8:].lower().split("_", 1)  # Remove MATHPDF_ prefix
            if len(parts) == 2:
                section, setting = parts
                if section in config and isinstance(config[section], dict):
                    # Try to convert to appropriate type
                    try:
                        if value.lower() in ("true", "false"):
                            config[section][setting] = value.lower() == "true"
                        elif value.isdigit():
                            config[section][setting] = int(value)
                        else:
                            config[section][setting] = value
                    except (ValueError, TypeError):
                        config[section][setting] = value

        return config

    def load(self) -> ConfigData:
        """Load configuration from file with environment overrides."""
        if self._config is not None:
            return self._config

        # Load YAML
        with open(self.config_path, encoding='utf-8') as f:
            raw_config = yaml.safe_load(f)

        # Apply environment overrides
        raw_config = self._apply_env_overrides(raw_config)
        self._raw_config = raw_config

        # Expand paths
        path_fields = [
            'base_maths_folder', 'known_words_file', 'name_dash_whitelist_file',
            'multiword_familynames_file', 'exceptions_file', 'template_dir'
        ]

        for field in path_fields:
            if field in raw_config:
                raw_config[field] = self._expand_path(raw_config[field])

        # Create config object
        self._config = ConfigData(
            # Core paths
            base_maths_folder=raw_config.get('base_maths_folder', ''),
            known_words_file=raw_config.get('known_words_file', ''),
            name_dash_whitelist_file=raw_config.get('name_dash_whitelist_file', ''),
            multiword_familynames_file=raw_config.get('multiword_familynames_file', ''),
            exceptions_file=raw_config.get('exceptions_file', ''),
            template_dir=raw_config.get('template_dir', ''),

            # Word lists
            capitalization_whitelist=raw_config.get('capitalization_whitelist', []),
            common_acronyms=raw_config.get('common_acronyms', []),
            mixed_case_words=raw_config.get('mixed_case_words', []),
            proper_adjectives=raw_config.get('proper_adjectives', []),
            compound_terms=raw_config.get('compound_terms', []),

            # Settings
            enable_spellcheck=raw_config.get('enable_spellcheck', True),
            backup_enabled=raw_config.get('backup_enabled', True),
            dry_run_default=raw_config.get('dry_run_default', True),
            max_unpublished_age_years=raw_config.get('max_unpublished_age_years', 5),

            # Complex structures
            folder_categories=raw_config.get('folder_categories', {}),
            folder_shortcuts=raw_config.get('folder_shortcuts', {}),
            extraction=raw_config.get('extraction', {}),
            repositories=raw_config.get('repositories', {}),
            scoring=raw_config.get('scoring', {}),
            performance=raw_config.get('performance', {}),
            grobid=raw_config.get('grobid', {}),
            ocr=raw_config.get('ocr', {}),
            google_scholar=raw_config.get('google_scholar', {}),
            logging=raw_config.get('logging', {}),
        )

        return self._config

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key."""
        if self._config is None:
            self.load()

        # Support dot notation: extraction.max_pages
        if '.' in key:
            parts = key.split('.')
            value = self._raw_config
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return default
            return value

        # Direct attribute access
        return getattr(self._config, key, default)

    def get_folder_paths(self, category: str) -> list[str]:
        """Get folder paths for a category."""
        config = self.load()

        # First check shortcuts
        if category in config.folder_shortcuts:
            shortcut = config.folder_shortcuts[category]
            if isinstance(shortcut, str):
                return [os.path.join(config.base_maths_folder, shortcut)]
            else:
                return [os.path.join(config.base_maths_folder, path) for path in shortcut]

        # Then check categories
        if category in config.folder_categories:
            return [os.path.join(config.base_maths_folder, path)
                   for path in config.folder_categories[category]]

        return []

    def reload(self) -> ConfigData:
        """Reload configuration from file."""
        self._config = None
        self._raw_config = None
        return self.load()


# Global configuration manager instance
_config_manager: ConfigManager | None = None


def get_config() -> ConfigData:
    """Get the global configuration."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager.load()


def get_config_value(key: str, default: Any = None) -> Any:
    """Get a configuration value by key."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager.get(key, default)


def reload_config() -> ConfigData:
    """Reload configuration from file."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager.reload()
