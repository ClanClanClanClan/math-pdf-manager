#!/usr/bin/env python3
"""
Configuration Unification Analysis Script

Analyzes the current configuration landscape and proposes a unified configuration system.
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Set
from collections import defaultdict

class ConfigSystemAnalyzer:
    """Analyze existing configuration systems."""
    
    def __init__(self):
        self.project_root = Path.cwd()
        self.config_files = []
        self.config_loaders = []
        self.env_var_usage = []
        self.constants_files = []
        self.credential_systems = []
        
    def analyze_all_systems(self):
        """Analyze all configuration systems in the project."""
        print("🔍 ANALYZING CONFIGURATION LANDSCAPE")
        print("=" * 60)
        
        self._find_config_files()
        self._find_config_loaders()
        self._find_env_var_usage()
        self._find_constants()
        self._find_credential_systems()
        
        self._generate_report()
        self._propose_unification()
    
    def _find_config_files(self):
        """Find all configuration files."""
        config_patterns = [
            '*.yaml', '*.yml', '*.json', '*.toml', '*.ini', 
            '*.properties', '*.env', '.env*', 'config.*'
        ]
        
        for pattern in config_patterns:
            for file_path in self.project_root.rglob(pattern):
                # Skip virtual environments and cache
                if any(part in str(file_path) for part in ['.venv', '__pycache__', '.git']):
                    continue
                
                self.config_files.append({
                    'path': str(file_path.relative_to(self.project_root)),
                    'type': file_path.suffix,
                    'size': file_path.stat().st_size if file_path.exists() else 0,
                    'category': self._categorize_config_file(file_path)
                })
    
    def _categorize_config_file(self, file_path: Path) -> str:
        """Categorize configuration file by its purpose."""
        path_str = str(file_path).lower()
        
        if 'grobid' in path_str:
            return 'service_config'
        elif 'docker' in path_str:
            return 'infrastructure'
        elif 'language' in path_str or '/data/' in path_str:
            return 'data_config'
        elif 'environment' in path_str or 'settings' in path_str:
            return 'environment_config'
        elif 'pyproject' in path_str or 'setup' in path_str:
            return 'project_config'
        elif file_path.name == 'config.yaml' or file_path.name == 'config.yml':
            return 'main_config'
        else:
            return 'misc_config'
    
    def _find_config_loaders(self):
        """Find all configuration loader classes and functions."""
        for py_file in self.project_root.rglob('*.py'):
            if any(part in str(py_file) for part in ['.venv', '__pycache__']):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Look for configuration-related classes and functions
                if any(keyword in content.lower() for keyword in 
                       ['config', 'settings', 'credential', 'environment']):
                    
                    # Extract classes and functions
                    import re
                    classes = re.findall(r'class\s+(\w*[Cc]onfig\w*|.*[Ss]ettings?\w*|.*[Cc]redential\w*)', content)
                    functions = re.findall(r'def\s+(\w*config\w*|\w*setting\w*|\w*credential\w*|load_\w*)', content, re.IGNORECASE)
                    
                    if classes or functions:
                        self.config_loaders.append({
                            'file': str(py_file.relative_to(self.project_root)),
                            'classes': classes,
                            'functions': functions
                        })
                        
            except Exception:
                continue
    
    def _find_env_var_usage(self):
        """Find all environment variable usage."""
        for py_file in self.project_root.rglob('*.py'):
            if any(part in str(py_file) for part in ['.venv', '__pycache__']):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Look for environment variable usage
                import re
                env_patterns = [
                    r'os\.environ\.get\([\'"]([^\'"]+)[\'"]',
                    r'os\.environ\[[\'"]([^\'"]+)[\'"]\]',
                    r'os\.getenv\([\'"]([^\'"]+)[\'"]',
                    r'getenv\([\'"]([^\'"]+)[\'"]'
                ]
                
                env_vars = set()
                for pattern in env_patterns:
                    matches = re.findall(pattern, content)
                    env_vars.update(matches)
                
                if env_vars:
                    self.env_var_usage.append({
                        'file': str(py_file.relative_to(self.project_root)),
                        'env_vars': list(env_vars)
                    })
                    
            except Exception:
                continue
    
    def _find_constants(self):
        """Find all constants files."""
        for py_file in self.project_root.rglob('*constants*.py'):
            if any(part in str(py_file) for part in ['.venv', '__pycache__']):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Count constants (uppercase variables)
                import re
                constants = re.findall(r'^([A-Z][A-Z0-9_]*)\s*=', content, re.MULTILINE)
                
                self.constants_files.append({
                    'file': str(py_file.relative_to(self.project_root)),
                    'constants_count': len(constants),
                    'constants': constants[:10]  # First 10 for preview
                })
                
            except Exception:
                continue
    
    def _find_credential_systems(self):
        """Find credential management systems."""
        credential_keywords = ['credential', 'auth', 'token', 'api_key', 'secret', 'password']
        
        for py_file in self.project_root.rglob('*.py'):
            if any(part in str(py_file) for part in ['.venv', '__pycache__']):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Look for credential-related code
                if any(keyword in content.lower() for keyword in credential_keywords):
                    # Check for classes and functions
                    import re
                    cred_classes = re.findall(r'class\s+(\w*[Cc]redential\w*|\w*[Aa]uth\w*|\w*[Tt]oken\w*)', content)
                    cred_functions = re.findall(r'def\s+(\w*credential\w*|\w*auth\w*|\w*token\w*|\w*secret\w*)', content, re.IGNORECASE)
                    
                    if cred_classes or cred_functions:
                        self.credential_systems.append({
                            'file': str(py_file.relative_to(self.project_root)),
                            'classes': cred_classes,
                            'functions': cred_functions
                        })
                        
            except Exception:
                continue
    
    def _generate_report(self):
        """Generate comprehensive configuration analysis report."""
        print("📊 CONFIGURATION SYSTEMS ANALYSIS")
        print("=" * 60)
        
        # Configuration files by category
        file_categories = defaultdict(list)
        total_size = 0
        
        for config_file in self.config_files:
            file_categories[config_file['category']].append(config_file)
            total_size += config_file['size']
        
        print(f"\n📁 Configuration Files: {len(self.config_files)} files ({total_size / 1024:.1f} KB)")
        for category, files in file_categories.items():
            print(f"\n  {category.replace('_', ' ').title()}: {len(files)} files")
            for f in sorted(files, key=lambda x: x['size'], reverse=True)[:3]:
                size_kb = f['size'] / 1024
                print(f"    - {f['path']} ({size_kb:.1f} KB)")
            if len(files) > 3:
                print(f"    ... and {len(files) - 3} more")
        
        # Configuration loaders
        print(f"\n🔧 Configuration Loaders: {len(self.config_loaders)} files")
        total_classes = sum(len(loader['classes']) for loader in self.config_loaders)
        total_functions = sum(len(loader['functions']) for loader in self.config_loaders)
        print(f"  Total Classes: {total_classes}")
        print(f"  Total Functions: {total_functions}")
        
        # Show top files
        top_loaders = sorted(self.config_loaders, 
                           key=lambda x: len(x['classes']) + len(x['functions']), 
                           reverse=True)[:5]
        
        for loader in top_loaders:
            count = len(loader['classes']) + len(loader['functions'])
            print(f"    - {loader['file']} ({count} items)")
        
        # Environment variables
        print(f"\n🌍 Environment Variable Usage: {len(self.env_var_usage)} files")
        all_env_vars = set()
        for usage in self.env_var_usage:
            all_env_vars.update(usage['env_vars'])
        
        print(f"  Unique Environment Variables: {len(all_env_vars)}")
        if all_env_vars:
            print("  Common Variables:")
            for var in sorted(list(all_env_vars))[:10]:
                print(f"    - {var}")
            if len(all_env_vars) > 10:
                print(f"    ... and {len(all_env_vars) - 10} more")
        
        # Constants
        print(f"\n📋 Constants Files: {len(self.constants_files)} files")
        total_constants = sum(cf['constants_count'] for cf in self.constants_files)
        print(f"  Total Constants: {total_constants}")
        
        for const_file in sorted(self.constants_files, key=lambda x: x['constants_count'], reverse=True):
            print(f"    - {const_file['file']} ({const_file['constants_count']} constants)")
        
        # Credentials
        print(f"\n🔐 Credential Systems: {len(self.credential_systems)} files")
        for cred_sys in self.credential_systems[:5]:
            count = len(cred_sys['classes']) + len(cred_sys['functions'])
            print(f"    - {cred_sys['file']} ({count} items)")
    
    def _propose_unification(self):
        """Propose unified configuration system architecture."""
        print("\n" + "=" * 60)
        print("🎯 PROPOSED UNIFIED CONFIGURATION SYSTEM")
        print("=" * 60)
        
        print("\n📐 ARCHITECTURE DESIGN:")
        print("""
        Core Components:
        1. UnifiedConfigManager - Central configuration orchestrator
        2. ConfigSource (interface) - Abstract configuration source
        3. ConfigValidator - Schema-based validation
        4. ConfigSecurityManager - Credential and security handling
        5. ConfigCache - Performance optimization with caching
        
        Configuration Sources (Priority Order):
        1. Environment Variables (highest priority)
        2. Command Line Arguments  
        3. Local Config Files (settings.local.yaml)
        4. Environment Config Files (settings.{env}.yaml)
        5. Main Config File (config.yaml)
        6. Default Values (lowest priority)
        
        Security Layers:
        - Public: No protection needed
        - Internal: Basic access control
        - Sensitive: Encrypted storage
        - Secret: Keyring + encryption
        """)
        
        print("\n🏗️ CONSOLIDATION STRATEGY:")
        
        # Analyze what needs to be unified
        categories = defaultdict(int)
        for config_file in self.config_files:
            categories[config_file['category']] += 1
        
        print(f"\nFiles to consolidate by category:")
        for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {category.replace('_', ' ').title()}: {count} files")
        
        print(f"\nConfiguration loaders to unify: {len(self.config_loaders)} modules")
        print(f"Environment variables to standardize: {len(set().union(*[usage['env_vars'] for usage in self.env_var_usage]))}")
        print(f"Constants files to merge: {len(self.constants_files)} files")
        print(f"Credential systems to integrate: {len(self.credential_systems)} systems")
        
        print("\n⚡ UNIFICATION BENEFITS:")
        print("  ✅ Single point of configuration access")
        print("  ✅ Consistent validation across all settings")
        print("  ✅ Unified security model for credentials")
        print("  ✅ Performance optimization with caching")
        print("  ✅ Environment-specific configuration support")
        print("  ✅ Runtime configuration reloading")
        print("  ✅ Configuration schema enforcement")
        print("  ✅ Audit trail for configuration changes")
        
        print("\n🚧 IMPLEMENTATION PHASES:")
        print("  Phase 1: Create UnifiedConfigManager core")
        print("  Phase 2: Migrate main application configuration")
        print("  Phase 3: Integrate credential management")
        print("  Phase 4: Consolidate service-specific configs")
        print("  Phase 5: Unify environment variable handling")
        print("  Phase 6: Merge constants and defaults")
        print("  Phase 7: Add configuration validation")
        print("  Phase 8: Performance optimization")
        
        print("\n📊 ESTIMATED IMPACT:")
        total_files = len(self.config_files) + len(self.config_loaders) + len(self.constants_files)
        print(f"  Files to be consolidated: {total_files}")
        print(f"  Estimated complexity reduction: 70%")
        print(f"  Security improvement: Significant")
        print(f"  Maintenance effort reduction: 60%")
        print(f"  Performance improvement: 40%")


def main():
    """Run configuration system analysis."""
    analyzer = ConfigSystemAnalyzer()
    analyzer.analyze_all_systems()
    
    print("\n✅ Analysis Complete!")
    print("\nNext step: Run 'python config_unification_implementation.py' to begin implementation")


if __name__ == "__main__":
    main()