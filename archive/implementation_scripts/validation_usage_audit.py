#!/usr/bin/env python3
"""
Audit actual validation usage in the codebase to see what still needs migration.
"""

import os
import re
from pathlib import Path
from collections import defaultdict

def audit_validation_usage():
    """Find all validation imports and usage in the codebase."""
    
    validation_imports = defaultdict(list)
    validation_patterns = [
        # Old validation imports
        (r'from src\.validators\.core_validation import', 'core_validation'),
        (r'from src\.core\.security\.input_validation import', 'input_validation'),
        (r'from src\.validators\.validation_utils import', 'validation_utils'),
        (r'from src\.validators\.filename_validator import', 'filename_validator'),
        (r'from src\.validators\.author_parser import', 'author_parser'),
        (r'from src\.validators\.title_normalizer import', 'title_normalizer'),
        (r'from src\.validators\.unicode_handler import', 'unicode_handler'),
        (r'from src\.validators\.pattern_matcher import', 'pattern_matcher'),
        (r'from src\.utils\.security import', 'security_utils'),
        
        # New unified validation imports
        (r'from src\.core\.validation import UnifiedValidationService', 'unified_new'),
        (r'from src\.core\.validation import ComprehensiveUnifiedValidationService', 'comprehensive_new'),
        
        # Direct validation module imports
        (r'import src\.validators\.\w+', 'direct_validators'),
        (r'import src\.core\.validation', 'direct_unified'),
    ]
    
    project_root = Path.cwd()
    
    # Search Python files
    for root, dirs, files in os.walk(project_root):
        # Skip virtual environments and cache
        dirs[:] = [d for d in dirs if d not in {'.venv', '__pycache__', '.git', '.pytest_cache'}]
        
        for file in files:
            if file.endswith('.py'):
                file_path = Path(root) / file
                
                # Skip migration scripts and backups
                if 'migration' in str(file_path) or file.endswith('.backup'):
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check each pattern
                    for pattern, category in validation_patterns:
                        if re.search(pattern, content, re.MULTILINE):
                            validation_imports[category].append(str(file_path.relative_to(project_root)))
                            
                except Exception as e:
                    pass
    
    # Print results
    print("🔍 VALIDATION USAGE AUDIT")
    print("=" * 60)
    
    print("\n📊 Import Statistics:")
    for category, files in validation_imports.items():
        print(f"\n{category}: {len(files)} files")
        if len(files) <= 10:  # Show files if not too many
            for f in sorted(files)[:5]:
                print(f"  - {f}")
            if len(files) > 5:
                print(f"  ... and {len(files) - 5} more")
    
    # Calculate migration progress
    old_imports = sum(len(files) for cat, files in validation_imports.items() 
                     if cat not in ['unified_new', 'comprehensive_new', 'direct_unified'])
    new_imports = sum(len(files) for cat, files in validation_imports.items() 
                     if cat in ['unified_new', 'comprehensive_new', 'direct_unified'])
    
    total_files = old_imports + new_imports
    if total_files > 0:
        migration_percent = (new_imports / total_files) * 100
        print(f"\n📈 Migration Progress: {new_imports}/{total_files} files ({migration_percent:.1f}%)")
        print(f"   Still using old validation: {old_imports} files")
        print(f"   Using new unified validation: {new_imports} files")
    
    # Check for specific validation function calls
    print("\n🔎 Validation Function Usage:")
    function_patterns = [
        ('validate_cli_inputs', 0),
        ('validate_file_path', 0),
        ('sanitize_filename', 0),
        ('check_filename', 0),
        ('validate_academic_filename', 0),
        ('validate_session', 0),
    ]
    
    for root, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if d not in {'.venv', '__pycache__', '.git', '.pytest_cache'}]
        
        for file in files:
            if file.endswith('.py'):
                file_path = Path(root) / file
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    for i, (func_name, count) in enumerate(function_patterns):
                        if func_name in content:
                            function_patterns[i] = (func_name, count + content.count(func_name))
                            
                except Exception:
                    pass
    
    print("\nFunction call counts:")
    for func_name, count in sorted(function_patterns, key=lambda x: x[1], reverse=True):
        if count > 0:
            print(f"  {func_name}: {count} calls")
    
    print("\n✅ Audit Complete!")

if __name__ == "__main__":
    audit_validation_usage()