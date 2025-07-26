#!/usr/bin/env python3
"""
Structure reorganization script for Math-PDF Manager project.
This script analyzes and helps reorganize the project structure.

Usage: python reorganize_structure.py [--execute] [--module MODULE]
"""

import os
import sys
import shutil
from pathlib import Path
from collections import defaultdict
import json
import argparse

class ProjectReorganizer:
    def __init__(self, project_root, execute=False):
        self.project_root = Path(project_root)
        self.execute = execute
        self.moves = []
        self.issues = []
        
    def analyze_structure(self):
        """Analyze current structure and identify issues."""
        print("Analyzing project structure...\n")
        
        # Check for scattered test files
        self.find_scattered_tests()
        
        # Check for duplicate implementations
        self.find_duplicates()
        
        # Check for misplaced files
        self.find_misplaced_files()
        
        # Check module organization
        self.analyze_modules()
        
        # Generate reorganization plan
        self.generate_plan()
        
    def find_scattered_tests(self):
        """Find test files outside of tests directory."""
        print("Finding scattered test files...")
        test_files = []
        
        for py_file in self.project_root.rglob('test_*.py'):
            if '.venv' in py_file.parts:
                continue
            if 'tests' not in py_file.parts:
                test_files.append(py_file)
                
        if test_files:
            self.issues.append({
                'type': 'scattered_tests',
                'description': f'Found {len(test_files)} test files outside tests directory',
                'files': [str(f.relative_to(self.project_root)) for f in test_files[:10]]
            })
            
            # Plan moves
            for test_file in test_files:
                # Determine appropriate subdirectory
                if 'gmnap' in test_file.parts:
                    dest = self.project_root / 'tests' / 'integration' / 'gmnap' / test_file.name
                elif 'debug' in str(test_file):
                    dest = self.project_root / 'tests' / 'debug' / test_file.name
                else:
                    dest = self.project_root / 'tests' / 'unit' / test_file.name
                    
                self.moves.append({
                    'source': test_file,
                    'destination': dest,
                    'reason': 'Consolidate test files'
                })
                
    def find_duplicates(self):
        """Find duplicate implementations."""
        print("Finding duplicate implementations...")
        
        # Common duplicate patterns
        patterns = {
            'pdf_parser': ['*pdf*parser*.py', '*pdf*parsing*.py'],
            'filename_checker': ['*filename*checker*.py', '*filename*valid*.py'],
            'auth_manager': ['*auth*manager*.py', '*authentication*.py'],
            'downloader': ['*download*.py', '*fetcher*.py']
        }
        
        for category, file_patterns in patterns.items():
            files = []
            for pattern in file_patterns:
                for f in self.project_root.rglob(pattern):
                    if '.venv' not in f.parts and f.is_file():
                        files.append(f)
                        
            if len(files) > 1:
                self.issues.append({
                    'type': 'duplicate_implementation',
                    'category': category,
                    'description': f'Found {len(files)} potential duplicate {category} implementations',
                    'files': [str(f.relative_to(self.project_root)) for f in files]
                })
                
    def find_misplaced_files(self):
        """Find files in wrong directories."""
        print("Finding misplaced files...")
        
        # Check root directory for files that should be elsewhere
        root_files = [f for f in self.project_root.iterdir() 
                     if f.is_file() and f.suffix == '.py' 
                     and f.name not in ['setup.py', 'main.py']]
        
        for f in root_files:
            if 'test' in f.name:
                self.moves.append({
                    'source': f,
                    'destination': self.project_root / 'tests' / 'unit' / f.name,
                    'reason': 'Test file in root directory'
                })
            elif any(word in f.name for word in ['parser', 'extractor', 'scanner']):
                self.moves.append({
                    'source': f,
                    'destination': self.project_root / 'src' / 'parsers' / f.name,
                    'reason': 'Parser/extractor in root directory'
                })
            elif any(word in f.name for word in ['valid', 'check']):
                self.moves.append({
                    'source': f,
                    'destination': self.project_root / 'src' / 'validators' / f.name,
                    'reason': 'Validator in root directory'
                })
                
    def analyze_modules(self):
        """Analyze module organization issues."""
        print("Analyzing module organization...")
        
        # Check for spaces in directory names
        for path in self.project_root.rglob('*'):
            if path.is_dir() and ' ' in path.name:
                self.issues.append({
                    'type': 'invalid_module_name',
                    'description': f'Module with spaces in name: {path.name}',
                    'path': str(path.relative_to(self.project_root))
                })
                
                # Plan rename
                new_name = path.name.replace(' ', '_')
                new_path = path.parent / new_name
                self.moves.append({
                    'source': path,
                    'destination': new_path,
                    'reason': 'Remove spaces from module name'
                })
                
    def generate_plan(self):
        """Generate reorganization plan."""
        print("\nGenerating reorganization plan...")
        
        # Proposed new structure
        new_structure = {
            'src/': {
                'core/': 'Core functionality (models, exceptions, constants)',
                'parsers/': 'All parsing logic (PDF, XML, text)',
                'validators/': 'All validation logic',
                'publishers/': 'Publisher-specific integrations',
                'auth/': 'Authentication and credential management',
                'utils/': 'Shared utilities and helpers',
                'api/': 'External API integrations'
            },
            'tests/': {
                'unit/': 'Unit tests organized by module',
                'integration/': 'Integration tests',
                'fixtures/': 'Test data and fixtures'
            },
            'config/': 'Configuration files',
            'docs/': 'Documentation',
            'scripts/': 'Utility scripts',
            'data/': 'Static data files'
        }
        
        # Save plan
        plan = {
            'issues': self.issues,
            'moves': [
                {
                    'source': str(m['source'].relative_to(self.project_root)),
                    'destination': str(m['destination'].relative_to(self.project_root)),
                    'reason': m['reason']
                }
                for m in self.moves
            ],
            'new_structure': new_structure
        }
        
        plan_path = self.project_root / 'reorganization_plan.json'
        with open(plan_path, 'w') as f:
            json.dump(plan, f, indent=2)
            
        print(f"\nReorganization plan saved to: {plan_path}")
        
    def execute_moves(self):
        """Execute the planned moves."""
        if not self.execute:
            print("\nDry run mode. Use --execute to perform moves.")
            return
            
        print(f"\nExecuting {len(self.moves)} file moves...")
        
        for move in self.moves:
            source = move['source']
            dest = move['destination']
            
            if not source.exists():
                print(f"Source no longer exists: {source}")
                continue
                
            # Create destination directory
            dest.parent.mkdir(parents=True, exist_ok=True)
            
            # Move file/directory
            try:
                shutil.move(str(source), str(dest))
                print(f"Moved: {source.relative_to(self.project_root)} -> {dest.relative_to(self.project_root)}")
            except Exception as e:
                print(f"Error moving {source}: {e}")
                
    def print_summary(self):
        """Print analysis summary."""
        print("\n" + "="*60)
        print("STRUCTURE ANALYSIS SUMMARY")
        print("="*60)
        
        if self.issues:
            print(f"\nFound {len(self.issues)} structural issues:")
            for issue in self.issues:
                print(f"\n- {issue['type'].upper()}: {issue['description']}")
                if 'files' in issue and issue['files']:
                    for f in issue['files'][:5]:
                        print(f"  • {f}")
                    if len(issue['files']) > 5:
                        print(f"  ... and {len(issue['files']) - 5} more")
                        
        print(f"\nPlanned {len(self.moves)} file/directory moves")
        
        
def create_ideal_structure(project_root):
    """Create ideal directory structure."""
    project_root = Path(project_root)
    
    directories = [
        'src/core',
        'src/parsers',
        'src/validators', 
        'src/publishers',
        'src/auth',
        'src/utils',
        'src/api',
        'tests/unit/core',
        'tests/unit/parsers',
        'tests/unit/validators',
        'tests/unit/publishers',
        'tests/integration',
        'tests/fixtures',
        'config',
        'docs/api',
        'docs/guides',
        'scripts/maintenance',
        'scripts/analysis',
        'data/dictionaries',
        'data/rules'
    ]
    
    for dir_path in directories:
        full_path = project_root / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        
        # Create __init__.py for Python packages
        if 'src/' in dir_path or 'tests/' in dir_path:
            init_file = full_path / '__init__.py'
            if not init_file.exists():
                init_file.write_text('"""Package initialization."""\n')
                
    print("Created ideal directory structure")
    

def main():
    parser = argparse.ArgumentParser(description='Reorganize Math-PDF Manager project structure')
    parser.add_argument('--execute', action='store_true',
                        help='Execute the reorganization (default is dry run)')
    parser.add_argument('--create-structure', action='store_true',
                        help='Create ideal directory structure')
    parser.add_argument('--project-root', type=str,
                        default=os.path.dirname(os.path.abspath(__file__)),
                        help='Project root directory')
    
    args = parser.parse_args()
    
    if args.create_structure:
        create_ideal_structure(args.project_root)
        print("Ideal structure created. Now run without --create-structure to analyze.")
        return
        
    reorganizer = ProjectReorganizer(
        project_root=args.project_root,
        execute=args.execute
    )
    
    reorganizer.analyze_structure()
    reorganizer.print_summary()
    
    if args.execute:
        response = input("\nProceed with reorganization? (yes/no): ")
        if response.lower() == 'yes':
            reorganizer.execute_moves()
        else:
            print("Reorganization cancelled.")
            

if __name__ == '__main__':
    main()