#!/usr/bin/env python3
"""
CRITICAL IMPORT FIXES: Fix all broken imports to restore functionality
"""

import os
import re
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_critical_imports():
    """Fix all broken imports to restore functionality."""
    project_root = Path(__file__).parent
    
    logger.info("🚨 CRITICAL IMPORT FIXES STARTING...")
    
    # Define import fixes needed
    import_fixes = [
        # filename_checker moved to validators/filename_checker/
        (r'from filename_checker', 'from src.validators.filename_checker'),
        (r'import filename_checker', 'import src.validators.filename_checker as filename_checker'),
        
        # config_loader moved to core/config/
        (r'from config_loader', 'from src.core.config.config_loader'),
        (r'import config_loader', 'import src.core.config.config_loader as config_loader'),
        
        # validation moved to validators/
        (r'from validation', 'from src.validators.core_validation'),
        (r'import validation', 'import src.core.validation as validation'),
        
        # Add src. prefix for internal imports
        (r'from secure_credential_manager', 'from src.secure_credential_manager'),
        (r'from metadata_fetcher', 'from src.metadata_fetcher'),
        (r'from main_processing', 'from src.processing.main_processing'),
    ]
    
    # Files to fix (focus on critical ones first)
    files_to_fix = []
    
    # Find all Python files in src/ and tests/
    for directory in ['src', 'tests']:
        dir_path = project_root / directory
        if dir_path.exists():
            for file_path in dir_path.rglob('*.py'):
                files_to_fix.append(file_path)
    
    fixed_files = 0
    total_fixes = 0
    
    for file_path in files_to_fix:
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            file_fixes = 0
            
            # Apply all import fixes
            for old_pattern, new_pattern in import_fixes:
                if re.search(old_pattern, content):
                    content = re.sub(old_pattern, new_pattern, content)
                    file_fixes += 1
            
            # Write back if changes were made
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                fixed_files += 1
                total_fixes += file_fixes
                logger.info(f"✅ Fixed {file_fixes} imports in {file_path.relative_to(project_root)}")
                
        except Exception as e:
            logger.error(f"❌ Error fixing {file_path}: {e}")
    
    logger.info(f"🎉 IMPORT FIXES COMPLETE: {total_fixes} fixes in {fixed_files} files")
    return fixed_files, total_fixes

if __name__ == "__main__":
    fixed_files, total_fixes = fix_critical_imports()
    print(f"\n📊 IMPORT FIX RESULTS:")
    print(f"   Files fixed: {fixed_files}")
    print(f"   Total fixes: {total_fixes}")