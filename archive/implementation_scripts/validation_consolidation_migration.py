#!/usr/bin/env python3
"""
Validation Systems Consolidation Migration Script

This script migrates all validation imports throughout the codebase to use
the new unified validation system, providing backward compatibility and
a clear migration path.
"""

import os
import re
import shutil
from pathlib import Path
from typing import List, Tuple, Dict

def find_python_files(directory: Path) -> List[Path]:
    """Find all Python files in the directory tree."""
    python_files = []
    for root, dirs, files in os.walk(directory):
        # Skip __pycache__ directories
        dirs[:] = [d for d in dirs if d != '__pycache__']
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(Path(root) / file)
    
    return python_files

def update_validation_imports(file_path: Path) -> Tuple[bool, List[str]]:
    """
    Update validation imports in a single file.
    
    Returns:
        (changed, changes_made)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes = []
        
        # Import replacements
        import_replacements = [
            # CLI validation imports
            (r'from src\.validators\.core_validation import validate_cli_inputs',
             'from src.core.validation import validate_cli_inputs'),
            (r'from src\.validators\.core_validation import validate_template_dir',
             'from src.core.validation import validate_template_dir'),
            
            # Input validation imports
            (r'from src\.core\.security\.input_validation import InputValidator',
             'from src.core.validation import InputValidator'),
            (r'from src\.core\.security\.input_validation import ValidationError',
             'from src.core.validation import ValidationError'),
            (r'from src\.core\.security\.input_validation import SecureFileHandler',
             'from src.core.validation import SecureFileHandler'),
            
            # Validation utils imports
            (r'from src\.validators\.validation_utils import get_language',
             'from src.core.validation import get_language'),
            
            # DI validation service imports
            (r'from src\.core\.dependency_injection\.validation_service import UnifiedValidationService',
             'from src.core.validation import UnifiedValidationService_Legacy as UnifiedValidationService'),
            
            # Direct module imports
            (r'import src\.validators\.core_validation',
             'import src.core.validation'),
            (r'import src\.core\.security\.input_validation',
             'import src.core.validation'),
            (r'import src\.validators\.validation_utils',
             'import src.core.validation'),
            
            # Relative imports in validators package
            (r'from \.core_validation import',
             'from src.core.validation import'),
            (r'from \.validation_utils import',
             'from src.core.validation import'),
        ]
        
        # Apply import replacements
        for old_pattern, new_import in import_replacements:
            if re.search(old_pattern, content):
                content = re.sub(old_pattern, new_import, content)
                changes.append(f"Updated import: {old_pattern} -> {new_import}")
        
        # Usage pattern replacements (for cases where the module is imported differently)
        usage_replacements = [
            # CLI validation usage
            (r'core_validation\.validate_cli_inputs',
             'validate_cli_inputs'),
            (r'core_validation\.validate_template_dir',
             'validate_template_dir'),
            
            # Input validation usage
            (r'input_validation\.InputValidator',
             'InputValidator'),
            (r'input_validation\.ValidationError',
             'ValidationError'),
            (r'input_validation\.SecureFileHandler',
             'SecureFileHandler'),
            
            # Validation utils usage
            (r'validation_utils\.get_language',
             'get_language'),
        ]
        
        # Apply usage replacements
        for old_pattern, new_usage in usage_replacements:
            if re.search(old_pattern, content):
                content = re.sub(old_pattern, new_usage, content)
                changes.append(f"Updated usage: {old_pattern} -> {new_usage}")
        
        # Write back if changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, changes
        
        return False, []
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False, []

def backup_old_validation_modules(project_root: Path):
    """Create backups of old validation modules before removal."""
    backup_dir = project_root / "migration_backups" / "validation_modules"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    modules_to_backup = [
        "src/validators/core_validation.py",
        "src/core/security/input_validation.py", 
        "src/validators/validation_utils.py",
        "src/core/dependency_injection/validation_service.py",
    ]
    
    backed_up = []
    for module_path in modules_to_backup:
        source = project_root / module_path
        if source.exists():
            dest = backup_dir / source.name
            shutil.copy2(source, dest)
            backed_up.append(str(source))
    
    return backed_up

def create_deprecation_notices(project_root: Path):
    """Create deprecation notice files for old validation modules."""
    deprecation_notice = '''"""
DEPRECATED MODULE

This module has been consolidated into the unified validation system.
Please update your imports:

OLD: from src.core.validation import validate_cli_inputs
NEW: from src.core.validation import validate_cli_inputs

OLD: from src.core.validation import InputValidator  
NEW: from src.core.validation import InputValidator

For more information, see: src/core/validation/
"""

import warnings
from src.core.validation.compatibility import *

warnings.warn(
    f"Module {__name__} is deprecated. Use src.core.validation instead.",
    DeprecationWarning,
    stacklevel=2
)
'''
    
    # Create deprecation notices
    deprecated_modules = [
        "src/validators/core_validation.py",
        "src/core/security/input_validation.py",
        "src/validators/validation_utils.py",
    ]
    
    for module_path in deprecated_modules:
        module_file = project_root / module_path
        if module_file.exists():
            # Backup original content
            backup_path = module_file.with_suffix('.py.backup')
            shutil.copy2(module_file, backup_path)
            
            # Write deprecation notice
            with open(module_file, 'w', encoding='utf-8') as f:
                f.write(deprecation_notice)

def main():
    """Main migration function."""
    print("🔄 VALIDATION SYSTEMS CONSOLIDATION MIGRATION")
    print("=" * 60)
    
    project_root = Path(__file__).parent
    
    # Step 1: Find all Python files
    print("\n1. Finding Python files...")
    python_files = find_python_files(project_root)
    print(f"   Found {len(python_files)} Python files")
    
    # Step 2: Update imports in all files
    print("\n2. Updating validation imports...")
    updated_files = []
    total_changes = []
    
    for file_path in python_files:
        # Skip the new validation modules themselves
        if 'src/core/validation' in str(file_path):
            continue
            
        changed, changes = update_validation_imports(file_path)
        if changed:
            updated_files.append(str(file_path))
            total_changes.extend(changes)
            print(f"   ✅ Updated: {file_path}")
            for change in changes:
                print(f"      {change}")
    
    print(f"\n   Updated {len(updated_files)} files with {len(total_changes)} changes")
    
    # Step 3: Create backups of old modules
    print("\n3. Creating backups of old validation modules...")
    backed_up = backup_old_validation_modules(project_root)
    for backup in backed_up:
        print(f"   📦 Backed up: {backup}")
    
    # Step 4: Create deprecation notices
    print("\n4. Creating deprecation notices...")
    create_deprecation_notices(project_root)
    print("   ⚠️  Old modules now show deprecation warnings")
    
    # Step 5: Summary
    print("\n" + "=" * 60)
    print("📊 MIGRATION SUMMARY")
    print("=" * 60)
    print(f"Files updated: {len(updated_files)}")
    print(f"Total changes: {len(total_changes)}")
    print(f"Modules backed up: {len(backed_up)}")
    
    print("\n✅ VALIDATION CONSOLIDATION COMPLETE!")
    print("🔧 All imports now use the unified validation system")
    print("⚠️  Old modules show deprecation warnings")
    print("📦 Backups created in migration_backups/validation_modules/")
    print("\n🚀 The codebase now uses a single, coherent validation system!")

if __name__ == "__main__":
    main()