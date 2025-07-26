#!/usr/bin/env python3
"""
Comprehensive cleanup summary and execution script for Math-PDF Manager.
This script provides a complete overview of cleanup tasks and can execute them.

Usage: python cleanup_summary.py [--phase PHASE] [--execute]
"""

import os
import sys
import json
import subprocess
from pathlib import Path
import argparse
from datetime import datetime

class CleanupCoordinator:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.phases = {
            1: "Remove redundant files (backup files, __pycache__, etc.)",
            2: "Reorganize project structure", 
            3: "Remove duplicate files",
            4: "Optimize large directories",
            5: "Clean up documentation"
        }
        
    def show_current_state(self):
        """Show current project state."""
        print("CURRENT PROJECT STATE")
        print("="*60)
        
        # Get directory size
        result = subprocess.run(
            ['du', '-sh', str(self.project_root)],
            capture_output=True, text=True
        )
        print(f"Total size: {result.stdout.strip()}")
        
        # Count files
        py_files = len(list(self.project_root.rglob('*.py')))
        backup_files = len(list(self.project_root.rglob('*.bak'))) + \
                      len(list(self.project_root.rglob('*.backup')))
        pycache_dirs = len(list(self.project_root.rglob('__pycache__')))
        
        print(f"Python files: {py_files:,}")
        print(f"Backup files: {backup_files:,}")
        print(f"__pycache__ directories: {pycache_dirs:,}")
        
        # Check for problematic directories
        problems = []
        if (self.project_root / 'htmlcov').exists():
            problems.append("- htmlcov directory exists")
        if (self.project_root / '_archive').exists():
            problems.append("- _archive directory exists")
        if (self.project_root / 'archive').exists():
            problems.append("- archive directory exists")
            
        if problems:
            print("\nProblems found:")
            for p in problems:
                print(p)
                
    def execute_phase(self, phase):
        """Execute a specific cleanup phase."""
        if phase == 1:
            print("\nPHASE 1: Removing redundant files...")
            cmd = [sys.executable, 'cleanup_immediate.py', '--project-root', str(self.project_root)]
            subprocess.run(cmd)
            
        elif phase == 2:
            print("\nPHASE 2: Reorganizing structure...")
            cmd = [sys.executable, 'reorganize_structure.py', '--project-root', str(self.project_root)]
            subprocess.run(cmd)
            
        elif phase == 3:
            print("\nPHASE 3: Finding and removing duplicates...")
            cmd = [sys.executable, 'find_duplicates.py', '--project-root', str(self.project_root)]
            subprocess.run(cmd)
            
        elif phase == 4:
            print("\nPHASE 4: Optimizing large directories...")
            self.optimize_large_dirs()
            
        elif phase == 5:
            print("\nPHASE 5: Cleaning documentation...")
            self.clean_documentation()
            
    def optimize_large_dirs(self):
        """Handle large directory optimization."""
        print("\nLarge directories found:")
        
        # Check tools/grobid
        grobid_path = self.project_root / 'tools' / 'grobid'
        if grobid_path.exists():
            size = subprocess.run(
                ['du', '-sh', str(grobid_path)],
                capture_output=True, text=True
            ).stdout.strip()
            print(f"\n- tools/grobid: {size}")
            print("  Recommendation: Move to separate repository or use Docker")
            print("  This is a full Java application, not needed in Python repo")
            
        # Check modules with spaces
        modules_path = self.project_root / 'modules'
        if modules_path.exists():
            for item in modules_path.iterdir():
                if item.is_dir() and ' ' in item.name:
                    print(f"\n- Module with spaces: {item.name}")
                    print(f"  Recommendation: Rename to {item.name.replace(' ', '_')}")
                    
    def clean_documentation(self):
        """Clean up excessive documentation."""
        print("\nDocumentation analysis:")
        
        md_files = list(self.project_root.glob('*.md'))
        print(f"Found {len(md_files)} markdown files in root")
        
        # Categorize docs
        categories = {
            'audit': [],
            'report': [],
            'plan': [],
            'guide': [],
            'other': []
        }
        
        for md_file in md_files:
            name_lower = md_file.name.lower()
            if 'audit' in name_lower:
                categories['audit'].append(md_file)
            elif 'report' in name_lower:
                categories['report'].append(md_file)
            elif 'plan' in name_lower:
                categories['plan'].append(md_file)
            elif 'guide' in name_lower or 'readme' in name_lower:
                categories['guide'].append(md_file)
            else:
                categories['other'].append(md_file)
                
        print("\nDocumentation categories:")
        for cat, files in categories.items():
            if files:
                print(f"  {cat}: {len(files)} files")
                
        print("\nRecommendation: Move non-essential docs to docs/archive/")
        
    def create_cleanup_checklist(self):
        """Create a cleanup checklist."""
        checklist = {
            'timestamp': datetime.now().isoformat(),
            'phases': [],
            'manual_tasks': []
        }
        
        # Automated phases
        for phase_num, description in self.phases.items():
            checklist['phases'].append({
                'number': phase_num,
                'description': description,
                'command': f'python cleanup_summary.py --phase {phase_num} --execute'
            })
            
        # Manual tasks
        checklist['manual_tasks'] = [
            {
                'task': 'Review and commit changes after each phase',
                'reason': 'Ensure version control captures each step'
            },
            {
                'task': 'Move tools/grobid to separate repository',
                'reason': 'Large Java application (4.9GB) not needed in Python repo'
            },
            {
                'task': 'Rename "unicode_utils 2" to "unicode_utils_v2"',
                'reason': 'Spaces in module names cause import issues'
            },
            {
                'task': 'Review duplicate implementations and choose canonical versions',
                'reason': 'Multiple implementations create confusion'
            },
            {
                'task': 'Update all imports after reorganization',
                'reason': 'File moves will break existing imports'
            }
        ]
        
        # Save checklist
        checklist_path = self.project_root / 'cleanup_checklist.json'
        with open(checklist_path, 'w') as f:
            json.dump(checklist, f, indent=2)
            
        return checklist
        
    def print_summary(self):
        """Print comprehensive cleanup summary."""
        print("\n" + "="*60)
        print("CLEANUP SUMMARY AND RECOMMENDATIONS")
        print("="*60)
        
        print("\nCLEANUP PHASES:")
        for phase, desc in self.phases.items():
            print(f"  Phase {phase}: {desc}")
            
        print("\nEXPECTED RESULTS:")
        print("  - Current size: ~7.8GB")
        print("  - After Phase 1: ~7.3GB (remove cache and backups)")
        print("  - After Phase 2: ~7.3GB (reorganization)")
        print("  - After Phase 3: ~7.0GB (remove duplicates)")
        print("  - After Phase 4: ~2.0GB (remove grobid)")
        print("  - After Phase 5: ~1.8GB (clean docs)")
        
        print("\nCRITICAL ACTIONS:")
        print("  1. BACKUP everything before starting")
        print("  2. Work on a feature branch")
        print("  3. Test thoroughly after each phase")
        print("  4. Document all decisions")
        
        checklist = self.create_cleanup_checklist()
        print(f"\nChecklist saved to: cleanup_checklist.json")
        

def main():
    parser = argparse.ArgumentParser(description='Coordinate Math-PDF Manager cleanup')
    parser.add_argument('--phase', type=int, choices=[1, 2, 3, 4, 5],
                        help='Execute specific cleanup phase')
    parser.add_argument('--execute', action='store_true',
                        help='Execute the selected phase (default is dry run)')
    parser.add_argument('--project-root', type=str,
                        default=os.path.dirname(os.path.abspath(__file__)),
                        help='Project root directory')
    
    args = parser.parse_args()
    
    coordinator = CleanupCoordinator(args.project_root)
    
    print("MATH-PDF MANAGER CLEANUP COORDINATOR")
    print("="*60)
    
    coordinator.show_current_state()
    
    if args.phase:
        if args.execute:
            response = input(f"\nExecute Phase {args.phase}? (yes/no): ")
            if response.lower() == 'yes':
                coordinator.execute_phase(args.phase)
            else:
                print("Execution cancelled.")
        else:
            print(f"\nPhase {args.phase}: {coordinator.phases[args.phase]}")
            print("Use --execute to run this phase")
    else:
        coordinator.print_summary()
        

if __name__ == '__main__':
    main()