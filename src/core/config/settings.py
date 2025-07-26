#!/usr/bin/env python3
"""
Centralized configuration management
Optimized settings for academic document processing
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class PerformanceSettings:
    """Performance-related configuration."""
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600
    cache_size_mb: int = 100
    max_workers: int = 4
    chunk_size: int = 1000
    enable_parallel_processing: bool = True


@dataclass
class ValidationSettings:
    """Validation-related configuration."""
    strict_unicode: bool = True
    auto_fix_nfc: bool = True
    auto_fix_authors: bool = False
    ignore_nfc_on_macos: bool = True
    max_filename_length: int = 255


@dataclass
class ParsingSettings:
    """Document parsing configuration."""
    preferred_parser: str = "pymupdf"
    enable_fallback_parsers: bool = True
    ocr_enabled: bool = False
    grobid_url: Optional[str] = None
    timeout_seconds: int = 30


@dataclass
class AppSettings:
    """Complete application settings."""
    performance: PerformanceSettings = None
    validation: ValidationSettings = None
    parsing: ParsingSettings = None
    debug: bool = False
    log_level: str = "INFO"
    
    def __post_init__(self):
        if self.performance is None:
            self.performance = PerformanceSettings()
        if self.validation is None:
            self.validation = ValidationSettings()
        if self.parsing is None:
            self.parsing = ParsingSettings()


class ConfigManager:
    """Manages application configuration with environment variable overrides."""
    
    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = config_file or Path.home() / ".academic_papers" / "config.json"
        self.settings = self._load_settings()
    
    def _load_settings(self) -> AppSettings:
        """Load settings from file and environment variables."""
        # Start with defaults
        settings_dict = {}
        
        # Load from file if it exists
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    file_settings = json.load(f)
                    settings_dict.update(file_settings)
            except (json.JSONDecodeError, OSError):
                pass  # Use defaults if file is corrupted
        
        # Override with environment variables
        env_overrides = self._get_env_overrides()
        settings_dict.update(env_overrides)
        
        return self._dict_to_settings(settings_dict)
    
    def _get_env_overrides(self) -> Dict[str, Any]:
        """Get configuration overrides from environment variables."""
        overrides = {}
        
        # Performance settings
        if os.getenv("ENABLE_CACHING"):
            overrides.setdefault("performance", {})["enable_caching"] = os.getenv("ENABLE_CACHING").lower() == "true"
        
        if os.getenv("CACHE_TTL_SECONDS"):
            try:
                overrides.setdefault("performance", {})["cache_ttl_seconds"] = int(os.getenv("CACHE_TTL_SECONDS"))
            except ValueError:
                pass
        
        if os.getenv("MAX_WORKERS"):
            try:
                overrides.setdefault("performance", {})["max_workers"] = int(os.getenv("MAX_WORKERS"))
            except ValueError:
                pass
        
        # Validation settings
        if os.getenv("AUTO_FIX_NFC"):
            overrides.setdefault("validation", {})["auto_fix_nfc"] = os.getenv("AUTO_FIX_NFC").lower() == "true"
        
        if os.getenv("AUTO_FIX_AUTHORS"):
            overrides.setdefault("validation", {})["auto_fix_authors"] = os.getenv("AUTO_FIX_AUTHORS").lower() == "true"
        
        # Parsing settings
        if os.getenv("PREFERRED_PARSER"):
            overrides.setdefault("parsing", {})["preferred_parser"] = os.getenv("PREFERRED_PARSER")
        
        if os.getenv("GROBID_URL"):
            overrides.setdefault("parsing", {})["grobid_url"] = os.getenv("GROBID_URL")
        
        # General settings
        if os.getenv("DEBUG"):
            overrides["debug"] = os.getenv("DEBUG").lower() == "true"
        
        if os.getenv("LOG_LEVEL"):
            overrides["log_level"] = os.getenv("LOG_LEVEL").upper()
        
        return overrides
    
    def _dict_to_settings(self, settings_dict: Dict[str, Any]) -> AppSettings:
        """Convert dictionary to AppSettings object."""
        # Extract nested settings
        performance_dict = settings_dict.get("performance", {})
        validation_dict = settings_dict.get("validation", {})
        parsing_dict = settings_dict.get("parsing", {})
        
        # Create settings objects
        performance = PerformanceSettings(**performance_dict)
        validation = ValidationSettings(**validation_dict)
        parsing = ParsingSettings(**parsing_dict)
        
        # Create main settings
        main_settings = {k: v for k, v in settings_dict.items() 
                        if k not in ["performance", "validation", "parsing"]}
        
        return AppSettings(
            performance=performance,
            validation=validation,
            parsing=parsing,
            **main_settings
        )
    
    def save_settings(self):
        """Save current settings to file."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        settings_dict = asdict(self.settings)
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(settings_dict, f, indent=2)
        except OSError:
            pass  # Saving is optional
    
    def get(self) -> AppSettings:
        """Get current settings."""
        return self.settings
    
    def update(self, **kwargs):
        """Update settings."""
        for key, value in kwargs.items():
            if hasattr(self.settings, key):
                setattr(self.settings, key, value)


# Global configuration instance
_config_manager = ConfigManager()


def get_settings() -> AppSettings:
    """Get application settings."""
    return _config_manager.get()


def update_settings(**kwargs):
    """Update application settings."""
    _config_manager.update(**kwargs)


def save_settings():
    """Save current settings to file."""
    _config_manager.save_settings()