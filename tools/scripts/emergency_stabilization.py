#!/usr/bin/env python3
"""
EMERGENCY STABILIZATION: Fix critical issues immediately
"""

import shutil
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def emergency_stabilization():
    """Fix critical issues immediately to restore functionality."""
    project_root = Path(__file__).parent
    
    logger.info("🚨 EMERGENCY STABILIZATION STARTING...")
    
    # 1. Move orphaned unicode_utils directory
    orphaned_unicode = project_root / "unicode_utils"
    archive_dir = project_root / ".archive" / "legacy"
    
    if orphaned_unicode.exists():
        archive_dir.mkdir(parents=True, exist_ok=True)
        dest = archive_dir / "unicode_utils_orphaned"
        try:
            shutil.move(str(orphaned_unicode), str(dest))
            logger.info(f"✅ Moved orphaned unicode_utils/ to .archive/legacy/")
        except Exception as e:
            logger.error(f"❌ Error moving unicode_utils: {e}")
    
    # 2. Fix massive src/unicode_utils_v2 bloat by moving to archive
    bloated_unicode = project_root / "src" / "unicode_utils_v2"
    if bloated_unicode.exists():
        try:
            # Get size first
            import os
            size = sum(os.path.getsize(os.path.join(dirpath, filename))
                      for dirpath, dirnames, filenames in os.walk(bloated_unicode)
                      for filename in filenames) / (1024*1024)  # MB
            
            logger.info(f"Found src/unicode_utils_v2/ with {size:.1f}MB - moving to archive")
            
            dest = archive_dir / "unicode_utils_v2_bloated"
            shutil.move(str(bloated_unicode), str(dest))
            logger.info(f"✅ Moved {size:.1f}MB unicode_utils_v2 to archive")
        except Exception as e:
            logger.error(f"❌ Error moving unicode_utils_v2: {e}")
    
    # 3. Fix nested duplication issues
    duplicated_extractors = project_root / "src" / "extractors" / "extractors"
    if duplicated_extractors.exists():
        parent_dir = duplicated_extractors.parent
        for item in duplicated_extractors.iterdir():
            dest = parent_dir / item.name
            if not dest.exists():
                shutil.move(str(item), str(dest))
        if not any(duplicated_extractors.iterdir()):
            duplicated_extractors.rmdir()
        logger.info("✅ Fixed nested extractors/extractors/ duplication")
    
    duplicated_unicode = project_root / "src" / "unicode_utils" / "unicode_utils"
    if duplicated_unicode.exists():
        parent_dir = duplicated_unicode.parent
        for item in duplicated_unicode.iterdir():
            dest = parent_dir / item.name
            if not dest.exists():
                shutil.move(str(item), str(dest))
        if not any(duplicated_unicode.iterdir()):
            duplicated_unicode.rmdir()
        logger.info("✅ Fixed nested unicode_utils/unicode_utils/ duplication")
    
    # 4. Create proper Python path configuration
    conftest_path = project_root / "tests" / "conftest.py"
    if not conftest_path.exists():
        conftest_content = '''"""Test configuration to fix import issues."""
import sys
from pathlib import Path

# Add src to Python path for proper imports
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
'''
        conftest_path.write_text(conftest_content)
        logger.info("✅ Created tests/conftest.py to fix import issues")
    
    # 5. Clean up .pytest_cache if it's large
    pytest_cache = project_root / ".pytest_cache"
    if pytest_cache.exists():
        try:
            shutil.rmtree(pytest_cache)
            logger.info("✅ Cleaned up .pytest_cache")
        except Exception as e:
            logger.error(f"⚠️  Could not clean .pytest_cache: {e}")
    
    # Final count
    final_dirs = [d.name for d in project_root.iterdir() if d.is_dir() and not d.name.startswith('.')]
    hidden_dirs = [d.name for d in project_root.iterdir() if d.is_dir() and d.name.startswith('.')]
    
    logger.info("🎉 EMERGENCY STABILIZATION COMPLETE!")
    logger.info(f"📁 Visible root directories: {len(final_dirs)} - {final_dirs}")
    logger.info(f"🔍 Hidden directories: {len(hidden_dirs)} - {hidden_dirs}")
    
    return len(final_dirs) + len(hidden_dirs)

if __name__ == "__main__":
    total_dirs = emergency_stabilization()
    print(f"\n📊 CURRENT STATE:")
    print(f"   Total root directories: {total_dirs}")
    print(f"   Target: 8 (src, tests, config, docs, tools, data, build, .archive)")
    print(f"   Improvement needed: {max(0, total_dirs - 8)} directories to consolidate")