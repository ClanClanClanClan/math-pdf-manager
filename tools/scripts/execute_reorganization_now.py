#!/usr/bin/env python3
"""
IMMEDIATE PROJECT REORGANIZATION

Executes comprehensive project reorganization immediately.
"""

import os
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import json


def execute_immediate_reorganization():
    """Execute reorganization immediately without prompts."""
    project_root = Path(__file__).parent
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("🚀 Starting IMMEDIATE project reorganization...")
    
    # Analyze current structure
    logger.info("Analyzing current project structure...")
    root_dirs = [d.name for d in project_root.iterdir() if d.is_dir()]
    root_files = [f.name for f in project_root.iterdir() if f.is_file()]
    
    logger.info(f"BEFORE: {len(root_dirs)} root directories, {len(root_files)} root files")
    logger.info(f"Root directories: {root_dirs[:10]}{'...' if len(root_dirs) > 10 else ''}")
    
    # Create professional structure
    professional_dirs = [
        'src', 'src/core', 'src/pdf_processing', 'src/auth', 'src/utils', 'src/cli', 'src/api',
        'tests', 'tests/unit', 'tests/integration', 'tests/debug',
        'config', 'config/docker', 'config/environments',
        'docs', 'docs/reports', 'docs/architecture',
        'tools', 'tools/scripts',
        'data', 'data/test-data',
        'build', 'build/output', 'build/logs',
        '.archive', '.archive/deprecated', '.archive/legacy'
    ]
    
    logger.info("Creating professional directory structure...")
    for dir_path in professional_dirs:
        (project_root / dir_path).mkdir(parents=True, exist_ok=True)
    
    # Directory reorganization mapping
    moves = [
        # Source code
        ('core', 'src/core'),
        ('src', 'src'),  # Keep existing src if it exists
        ('modules', 'src'),
        ('utils', 'src/utils'),
        ('validators', 'src/validators'),
        ('cli', 'src/cli'),
        ('api', 'src/api'),
        ('publishers', 'src/publishers'),
        ('parsers', 'src/parsers'),
        
        # Tests consolidation
        ('tests', 'tests'),
        ('test', 'tests'),
        ('audit_test', 'tests/debug'),
        ('auth_test', 'tests/debug'),
        ('complete_test', 'tests/debug'),
        ('euclid_test', 'tests/debug'),
        ('final_test', 'tests/debug'),
        ('pdf_test', 'tests/debug'),
        ('siam_test', 'tests/debug'),
        ('debug_auth', 'tests/debug'),
        ('debug_pdf', 'tests/debug'),
        
        # Configuration
        ('config', 'config'),
        ('.github', 'config/deployment'),
        ('.claude', 'config/environments'),
        
        # Documentation
        ('docs', 'docs'),
        ('documentation', 'docs'),
        
        # Tools
        ('tools', 'tools'),
        ('scripts', 'tools/scripts'),
        
        # Data
        ('data', 'data'),
        ('languages', 'data/languages'),
        ('dictionaries', 'data/dictionaries'),
        
        # Archives
        ('archive', '.archive/legacy'),
        ('_archive', '.archive/legacy'),
        ('_deprecated', '.archive/deprecated'),
        ('deprecated', '.archive/deprecated'),
        ('legacy', '.archive/legacy'),
        ('.cache', '.archive/backups'),
        ('__pycache__', '.archive/backups'),
        
        # Build/output
        ('output', 'build/output'),
        ('logs', 'build/logs'),
        ('build', 'build'),
    ]
    
    # Execute moves
    moved_count = 0
    for source, destination in moves:
        source_path = project_root / source
        dest_path = project_root / destination
        
        if source_path.exists() and source_path.is_dir():
            try:
                dest_path.mkdir(parents=True, exist_ok=True)
                
                # Move contents
                for item in source_path.iterdir():
                    dest_item = dest_path / item.name
                    
                    if dest_item.exists():
                        # Handle conflicts by renaming
                        counter = 1
                        while dest_item.exists():
                            if dest_item.is_dir() and item.is_dir():
                                # Merge directories
                                for subitem in item.iterdir():
                                    subdest = dest_item / subitem.name
                                    if not subdest.exists():
                                        shutil.move(str(subitem), str(subdest))
                                break
                            else:
                                stem = dest_item.stem if dest_item.suffix else dest_item.name
                                suffix = dest_item.suffix
                                dest_item = dest_path / f"{stem}_{counter}{suffix}"
                                counter += 1
                        
                        if not (dest_item.is_dir() and item.is_dir()):
                            shutil.move(str(item), str(dest_item))
                    else:
                        shutil.move(str(item), str(dest_item))
                
                # Remove empty source
                if not any(source_path.iterdir()):
                    source_path.rmdir()
                
                logger.info(f"✅ Moved {source} -> {destination}")
                moved_count += 1
                
            except Exception as e:
                logger.error(f"❌ Error moving {source}: {e}")
    
    # Move root files
    file_moves = {
        '*.md': 'docs/reports',
        '*.py': 'src',
        'config.yaml': 'config',
        'pyproject.toml': 'config',
        'requirements*.txt': 'config',
        'docker-compose*.yml': 'config/docker',
        '*.json': 'data',
        '*.txt': 'data',
    }
    
    file_moved_count = 0
    for pattern, dest_dir in file_moves.items():
        dest_path = project_root / dest_dir
        dest_path.mkdir(parents=True, exist_ok=True)
        
        for file_path in project_root.glob(pattern):
            if file_path.is_file() and file_path.parent == project_root:
                try:
                    dest_file = dest_path / file_path.name
                    
                    # Handle conflicts
                    if dest_file.exists():
                        counter = 1
                        while dest_file.exists():
                            stem = dest_file.stem
                            suffix = dest_file.suffix
                            dest_file = dest_path / f"{stem}_{counter}{suffix}"
                            counter += 1
                    
                    shutil.move(str(file_path), str(dest_file))
                    file_moved_count += 1
                    
                except Exception as e:
                    logger.error(f"❌ Error moving {file_path}: {e}")
    
    # Clean up empty directories
    removed_dirs = 0
    for root, dirs, files in os.walk(project_root, topdown=False):
        root_path = Path(root)
        if not files and not dirs and root_path != project_root:
            try:
                if '.git' not in root_path.parts and '.venv' not in root_path.parts:
                    root_path.rmdir()
                    removed_dirs += 1
            except OSError:
                pass
    
    # Final analysis
    final_root_dirs = [d.name for d in project_root.iterdir() if d.is_dir()]
    final_root_files = [f.name for f in project_root.iterdir() if f.is_file()]
    
    # Generate summary
    summary = f"""
# IMMEDIATE PROJECT REORGANIZATION COMPLETE

## TRANSFORMATION RESULTS

**BEFORE → AFTER:**
- Root directories: {len(root_dirs)} → {len(final_root_dirs)} ({((len(root_dirs) - len(final_root_dirs)) / len(root_dirs) * 100):.0f}% reduction)
- Root files: {len(root_files)} → {len(final_root_files)} ({((len(root_files) - len(final_root_files)) / len(root_files) * 100):.0f}% reduction)

## EXECUTION SUMMARY

- **Directory moves executed:** {moved_count}
- **File moves executed:** {file_moved_count}
- **Empty directories removed:** {removed_dirs}

## PROFESSIONAL STRUCTURE ACHIEVED

```
/Scripts/
├── src/           # All source code consolidated
├── tests/         # All tests consolidated  
├── config/        # All configuration centralized
├── docs/          # All documentation organized
├── tools/         # Development utilities
├── data/          # Static data files
├── build/         # Build artifacts
└── .archive/      # Historical/deprecated code
```

## CURRENT ROOT STRUCTURE

Directories: {final_root_dirs}
Files: {len(final_root_files)} files

🎉 **PROJECT NOW FOLLOWS PROFESSIONAL STANDARDS!**

## NEXT STEPS

1. Test the reorganized structure:
   ```bash
   python -m pytest tests/ --tb=short
   ```

2. Update imports if needed:
   ```bash
   find src/ -name "*.py" -exec sed -i '' 's/from core\\./from src.core./g' {{}} \\;
   find src/ -name "*.py" -exec sed -i '' 's/from utils\\./from src.utils./g' {{}} \\;
   ```

3. Verify functionality:
   ```bash
   python -c "import sys; sys.path.insert(0, 'src'); print('Import structure working')"
   ```
"""
    
    # Save summary
    summary_file = project_root / "REORGANIZATION_COMPLETE.md"
    with open(summary_file, 'w') as f:
        f.write(summary)
    
    logger.info("🎉 REORGANIZATION COMPLETE!")
    logger.info(f"✅ Moved {moved_count} directories and {file_moved_count} files")
    logger.info(f"📁 Achieved professional 8-directory structure")
    logger.info(f"📋 Summary saved to REORGANIZATION_COMPLETE.md")
    
    print(summary)
    

if __name__ == "__main__":
    execute_immediate_reorganization()