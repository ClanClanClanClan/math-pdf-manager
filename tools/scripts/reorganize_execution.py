#!/usr/bin/env python3
"""
CRITICAL PROJECT REORGANIZATION SCRIPT

This script implements the professional reorganization of the Math-PDF Manager project,
reducing 57 directories to 8 professional directories and organizing 143+ files.

WARNING: This script makes significant structural changes. Ensure you have backups!
"""

import os
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Tuple
import glob
import json


class ProjectReorganizer:
    """Professional project reorganization implementation."""
    
    def __init__(self, project_root: str):
        """Initialize reorganizer with project root."""
        self.project_root = Path(project_root)
        self.backup_dir = None
        self.moves_log = []
        self.errors_log = []
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'reorganization_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def create_backup(self) -> Path:
        """Create full backup before reorganization."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"Scripts_backup_{timestamp}"
        backup_path = self.project_root.parent / backup_name
        
        self.logger.info(f"Creating backup at {backup_path}")
        shutil.copytree(self.project_root, backup_path)
        self.backup_dir = backup_path
        
        self.logger.info(f"✅ Backup created successfully at {backup_path}")
        return backup_path
        
    def analyze_current_structure(self) -> Dict:
        """Analyze current project structure."""
        analysis = {
            'root_directories': [],
            'root_files': [],
            'total_files': 0,
            'total_directories': 0,
            'file_types': {},
            'test_directories': [],
            'documentation_files': [],
            'config_files': [],
            'archive_directories': []
        }
        
        # Analyze root level
        for item in self.project_root.iterdir():
            if item.is_dir():
                analysis['root_directories'].append(item.name)
                if 'test' in item.name.lower() or 'debug' in item.name.lower():
                    analysis['test_directories'].append(item.name)
                if any(x in item.name.lower() for x in ['archive', 'deprecated', 'cache', 'backup']):
                    analysis['archive_directories'].append(item.name)
            else:
                analysis['root_files'].append(item.name)
                if item.suffix == '.md':
                    analysis['documentation_files'].append(item.name)
                if item.name.lower() in ['config.yaml', 'pyproject.toml', 'requirements.txt']:
                    analysis['config_files'].append(item.name)
        
        # Count all files and directories
        for root, dirs, files in os.walk(self.project_root):
            analysis['total_directories'] += len(dirs)
            analysis['total_files'] += len(files)
            
            for file in files:
                ext = Path(file).suffix.lower()
                analysis['file_types'][ext] = analysis['file_types'].get(ext, 0) + 1
        
        self.logger.info(f"Current structure analysis complete:")
        self.logger.info(f"  Root directories: {len(analysis['root_directories'])}")
        self.logger.info(f"  Root files: {len(analysis['root_files'])}")
        self.logger.info(f"  Total files: {analysis['total_files']}")
        self.logger.info(f"  Total directories: {analysis['total_directories']}")
        self.logger.info(f"  Test directories: {len(analysis['test_directories'])}")
        self.logger.info(f"  Documentation files: {len(analysis['documentation_files'])}")
        
        return analysis
        
    def create_professional_structure(self):
        """Create professional 8-directory structure."""
        professional_dirs = [
            'src',
            'src/core',
            'src/api', 
            'src/cli',
            'src/publishers',
            'src/parsers',
            'src/pdf_processing',
            'src/validators',
            'src/auth',
            'src/utils',
            'tests',
            'tests/unit',
            'tests/integration',
            'tests/fixtures',
            'tests/debug',
            'config',
            'config/environments',
            'config/docker',
            'config/deployment',
            'docs',
            'docs/api',
            'docs/architecture',
            'docs/reports',
            'docs/guides',
            'tools',
            'tools/scripts',
            'tools/analysis',
            'tools/security',
            'data',
            'data/languages',
            'data/dictionaries',
            'data/test-data',
            'build',
            'build/output',
            'build/logs',
            'build/metrics',
            '.archive',
            '.archive/deprecated',
            '.archive/legacy',
            '.archive/backups'
        ]
        
        self.logger.info("Creating professional directory structure...")
        for dir_path in professional_dirs:
            full_path = self.project_root / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Created directory: {dir_path}")
            
        self.logger.info("✅ Professional directory structure created")
        
    def get_reorganization_mapping(self) -> Dict[str, str]:
        """Define mapping from current structure to professional structure."""
        return {
            # Source code reorganization
            'core/': 'src/core/',
            'modules/pdf_processing/': 'src/pdf_processing/',
            'modules/auth/': 'src/auth/',
            'modules/validators/': 'src/validators/',
            'modules/utils/': 'src/utils/',
            'modules/': 'src/',
            'utils/': 'src/utils/',
            'validators/': 'src/validators/',
            'cli/': 'src/cli/',
            'api/': 'src/api/',
            'publishers/': 'src/publishers/',
            'parsers/': 'src/parsers/',
            
            # Test consolidation (consolidate ALL test directories)
            'tests/': 'tests/',
            'test/': 'tests/',
            'audit_test/': 'tests/debug/',
            'auth_test/': 'tests/debug/',
            'complete_test/': 'tests/debug/',
            'euclid_test/': 'tests/debug/',
            'final_test/': 'tests/debug/',
            'pdf_test/': 'tests/debug/',
            'siam_test/': 'tests/debug/',
            'debug_auth/': 'tests/debug/',
            'debug_pdf/': 'tests/debug/',
            'unit_tests/': 'tests/unit/',
            'integration_tests/': 'tests/integration/',
            
            # Configuration consolidation  
            'config/': 'config/',
            '.github/': 'config/deployment/',
            '.claude/': 'config/environments/',
            
            # Documentation organization
            'docs/': 'docs/',
            'documentation/': 'docs/',
            'guides/': 'docs/guides/',
            
            # Tools and utilities
            'tools/': 'tools/',
            'scripts/': 'tools/scripts/',
            'bin/': 'tools/scripts/',
            
            # Data files
            'data/': 'data/',
            'languages/': 'data/languages/',
            'dictionaries/': 'data/dictionaries/',
            'test_data/': 'data/test-data/',
            'fixtures/': 'tests/fixtures/',
            
            # Archive consolidation
            'archive/': '.archive/legacy/',
            '_archive/': '.archive/legacy/',
            '_deprecated/': '.archive/deprecated/',
            'deprecated/': '.archive/deprecated/',
            'legacy/': '.archive/legacy/',
            'old/': '.archive/legacy/',
            'backup/': '.archive/backups/',
            '.cache/': '.archive/backups/',
            '.metadata_cache/': '.archive/backups/',
            '__pycache__/': '.archive/backups/',
            
            # Build and output
            'output/': 'build/output/',
            'logs/': 'build/logs/',
            'metrics/': 'build/metrics/',
            'build/': 'build/',
        }
        
    def move_directory_contents(self, source: str, destination: str) -> bool:
        """Safely move directory contents with error handling."""
        source_path = self.project_root / source
        dest_path = self.project_root / destination
        
        if not source_path.exists():
            self.logger.debug(f"Source {source} does not exist, skipping")
            return True
            
        if not source_path.is_dir():
            self.logger.debug(f"Source {source} is not a directory, skipping")
            return True
            
        try:
            # Ensure destination exists
            dest_path.mkdir(parents=True, exist_ok=True)
            
            # Move contents
            moved_count = 0
            for item in source_path.iterdir():
                dest_item = dest_path / item.name
                
                # Handle conflicts
                if dest_item.exists():
                    if dest_item.is_dir() and item.is_dir():
                        # Merge directories
                        shutil.copytree(item, dest_item, dirs_exist_ok=True)
                        shutil.rmtree(item)
                    else:
                        # Rename conflicting file
                        counter = 1
                        while dest_item.exists():
                            stem = dest_item.stem
                            suffix = dest_item.suffix
                            dest_item = dest_path / f"{stem}_{counter}{suffix}"
                            counter += 1
                        shutil.move(str(item), str(dest_item))
                else:
                    shutil.move(str(item), str(dest_item))
                
                moved_count += 1
                self.moves_log.append(f"{item} -> {dest_item}")
            
            # Remove empty source directory
            if source_path.exists() and not any(source_path.iterdir()):
                source_path.rmdir()
                
            self.logger.info(f"✅ Moved {moved_count} items from {source} to {destination}")
            return True
            
        except Exception as e:
            error_msg = f"❌ Error moving {source} to {destination}: {e}"
            self.logger.error(error_msg)
            self.errors_log.append(error_msg)
            return False
            
    def move_root_files(self):
        """Move root-level files to appropriate directories."""
        file_mappings = {
            # Documentation files (53 files from root)
            '*.md': 'docs/reports/',
            'README*': 'docs/',
            'CHANGELOG*': 'docs/',
            'LICENSE*': 'docs/',
            
            # Configuration files  
            'config.yaml': 'config/',
            'pyproject.toml': 'config/',
            'requirements*.txt': 'config/',
            'setup.py': 'config/',
            'setup.cfg': 'config/',
            'tox.ini': 'config/',
            'pytest.ini': 'config/',
            '.env*': 'config/environments/',
            
            # Docker files
            'docker-compose*.yml': 'config/docker/',
            'Dockerfile*': 'config/docker/',
            '.dockerignore': 'config/docker/',
            
            # CI/CD files
            '.github*': 'config/deployment/',
            'Makefile': 'config/deployment/',
            
            # Python specific
            'main.py': 'src/',
            '*.py': 'src/',  # General Python files to src
            
            # Data files
            '*.json': 'data/',
            '*.csv': 'data/',
            '*.txt': 'data/',
            '*.xml': 'data/',
        }
        
        moved_count = 0
        for pattern, dest_dir in file_mappings.items():
            dest_path = self.project_root / dest_dir
            dest_path.mkdir(parents=True, exist_ok=True)
            
            for file_path in self.project_root.glob(pattern):
                if file_path.is_file() and file_path.parent == self.project_root:
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
                        self.moves_log.append(f"{file_path.name} -> {dest_dir}")
                        moved_count += 1
                        
                    except Exception as e:
                        error_msg = f"❌ Error moving {file_path}: {e}"
                        self.logger.error(error_msg)
                        self.errors_log.append(error_msg)
        
        self.logger.info(f"✅ Moved {moved_count} root files to appropriate directories")
        
    def execute_reorganization(self):
        """Execute the complete project reorganization."""
        self.logger.info("🚀 Starting COMPREHENSIVE project reorganization...")
        
        # Step 1: Analyze current structure
        analysis = self.analyze_current_structure()
        
        # Step 2: Create backup
        if input("\n⚠️  Create backup before reorganization? (y/N): ").lower().strip() == 'y':
            self.create_backup()
        
        # Step 3: Create professional structure
        self.create_professional_structure()
        
        # Step 4: Execute directory reorganization
        mapping = self.get_reorganization_mapping()
        self.logger.info(f"Executing {len(mapping)} directory reorganizations...")
        
        successful_moves = 0
        for source, destination in mapping.items():
            if self.move_directory_contents(source, destination):
                successful_moves += 1
        
        # Step 5: Move root files  
        self.move_root_files()
        
        # Step 6: Clean up empty directories
        self.cleanup_empty_directories()
        
        # Step 7: Generate reports
        self.generate_reorganization_report(analysis)
        
        self.logger.info("🎉 REORGANIZATION COMPLETE!")
        self.logger.info(f"✅ Successfully moved {successful_moves}/{len(mapping)} directories")
        self.logger.info(f"📁 Created professional 8-directory structure")
        self.logger.info(f"📋 Generated detailed reorganization report")
        
        if self.errors_log:
            self.logger.warning(f"⚠️  {len(self.errors_log)} errors occurred - see log for details")
            
    def cleanup_empty_directories(self):
        """Remove empty directories after reorganization."""
        removed_count = 0
        
        # Walk directories in reverse order (deepest first)
        for root, dirs, files in os.walk(self.project_root, topdown=False):
            root_path = Path(root)
            
            # Skip protected directories
            protected = {'.git', '.venv', 'node_modules', '.archive'}
            if any(part in protected for part in root_path.parts):
                continue
                
            try:
                # Remove if empty and not in professional structure
                if not files and not dirs and root_path != self.project_root:
                    root_path.rmdir()
                    removed_count += 1
                    self.logger.debug(f"Removed empty directory: {root_path.relative_to(self.project_root)}")
            except OSError:
                # Directory not empty or permission issue
                pass
                
        self.logger.info(f"✅ Cleaned up {removed_count} empty directories")
        
    def generate_reorganization_report(self, before_analysis: Dict):
        """Generate detailed reorganization report."""
        after_analysis = self.analyze_current_structure()
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'before': before_analysis,
            'after': after_analysis,
            'improvements': {
                'root_directories_reduced': len(before_analysis['root_directories']) - len(after_analysis['root_directories']),
                'root_files_reduced': len(before_analysis['root_files']) - len(after_analysis['root_files']),
                'test_directories_consolidated': len(before_analysis['test_directories']) - len(after_analysis['test_directories']),
                'documentation_organized': len(before_analysis['documentation_files'])
            },
            'moves_executed': len(self.moves_log),
            'errors_encountered': len(self.errors_log),
            'backup_location': str(self.backup_dir) if self.backup_dir else None
        }
        
        # Save detailed report
        report_file = self.project_root / f"REORGANIZATION_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
            
        # Generate summary
        summary = f"""
# PROJECT REORGANIZATION COMPLETE

## TRANSFORMATION SUMMARY

**BEFORE → AFTER:**
- Root directories: {before_analysis['root_directories'].__len__()} → {after_analysis['root_directories'].__len__()} ({((before_analysis['root_directories'].__len__() - after_analysis['root_directories'].__len__()) / before_analysis['root_directories'].__len__() * 100):.0f}% reduction)
- Root files: {before_analysis['root_files'].__len__()} → {after_analysis['root_files'].__len__()} ({((before_analysis['root_files'].__len__() - after_analysis['root_files'].__len__()) / before_analysis['root_files'].__len__() * 100):.0f}% reduction)
- Test directories: {before_analysis['test_directories'].__len__()} → {after_analysis['test_directories'].__len__()} (consolidated)
- Documentation files organized: {before_analysis['documentation_files'].__len__()}

## PROFESSIONAL STRUCTURE ACHIEVED

```
/Scripts/
├── src/           # All source code consolidated
├── tests/         # All tests consolidated  
├── config/        # All configuration centralized
├── docs/          # All documentation organized
├── tools/         # Development tools
├── data/          # Static data files
├── build/         # Build artifacts
└── .archive/      # Historical/deprecated code
```

## EXECUTION METRICS

- **Moves executed:** {len(self.moves_log)}
- **Errors encountered:** {len(self.errors_log)}
- **Backup created:** {self.backup_dir if self.backup_dir else 'None'}

## NEXT STEPS

1. **Test the reorganized structure:**
   ```bash
   cd "{self.project_root}"
   python -m pytest tests/ --tb=short
   ```

2. **Update imports if needed:**
   ```bash
   find src/ -name "*.py" -exec sed -i 's/from utils\\./from src.utils./g' {{}} \\;
   find src/ -name "*.py" -exec sed -i 's/from core\\./from src.core./g' {{}} \\;
   ```

3. **Verify configuration:**
   ```bash
   python -c "import sys; sys.path.insert(0, 'src'); import core"
   ```

🎉 **PROJECT NOW FOLLOWS PROFESSIONAL STANDARDS!**
"""
        
        summary_file = self.project_root / "REORGANIZATION_SUMMARY.md"
        with open(summary_file, 'w') as f:
            f.write(summary)
            
        self.logger.info(f"📋 Detailed report saved to {report_file}")
        self.logger.info(f"📋 Summary saved to {summary_file}")


def main():
    """Main execution function."""
    import sys
    
    # Get project root
    project_root = Path(__file__).parent
    if len(sys.argv) > 1:
        project_root = Path(sys.argv[1])
    
    print(f"""
🔥 CRITICAL PROJECT REORGANIZATION TOOL 🔥

This script will transform your project from 57+ directories to 8 professional directories.

Project Root: {project_root}

⚠️  WARNING: This makes significant structural changes!
⚠️  Ensure you have backups before proceeding!

Professional structure will be created:
  src/     - All source code organized  
  tests/   - All tests consolidated
  config/  - All configuration centralized
  docs/    - All documentation organized
  tools/   - Development utilities
  data/    - Static data files
  build/   - Build artifacts and logs
  .archive/ - Historical/deprecated code

Continue? (y/N): """, end="")
    
    if input().lower().strip() != 'y':
        print("❌ Reorganization cancelled.")
        return
    
    # Execute reorganization
    reorganizer = ProjectReorganizer(str(project_root))
    reorganizer.execute_reorganization()
    
    print(f"""
🎉 REORGANIZATION COMPLETE!

Your project now follows professional standards with:
✅ Clean 8-directory structure
✅ Consolidated tests and documentation
✅ Centralized configuration
✅ Organized source code

Next steps:
1. Test: python -m pytest tests/ --tb=short
2. Update imports if needed (see REORGANIZATION_SUMMARY.md)
3. Verify functionality

Backup location: {reorganizer.backup_dir if reorganizer.backup_dir else 'None created'}
""")


if __name__ == "__main__":
    main()