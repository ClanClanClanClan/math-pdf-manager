#!/usr/bin/env python3
"""
Find and analyze duplicate files in Math-PDF Manager project.
Uses content hashing to identify true duplicates.

Usage: python find_duplicates.py [--remove-duplicates] [--keep-newest]
"""

import os
import hashlib
import json
from pathlib import Path
from collections import defaultdict
import argparse
from datetime import datetime

class DuplicateFinder:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.duplicates = defaultdict(list)
        self.stats = {
            'files_scanned': 0,
            'duplicates_found': 0,
            'space_wasted': 0
        }
        
    def calculate_hash(self, file_path, chunk_size=8192):
        """Calculate MD5 hash of file."""
        hasher = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                while chunk := f.read(chunk_size):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            print(f"Error hashing {file_path}: {e}")
            return None
            
    def find_duplicates(self):
        """Find all duplicate files in project."""
        print("Scanning for duplicate files...")
        
        # Common file patterns to check
        patterns = ['*.py', '*.md', '*.txt', '*.yaml', '*.yml', '*.json']
        
        file_hashes = defaultdict(list)
        
        for pattern in patterns:
            for file_path in self.project_root.rglob(pattern):
                # Skip virtual env and special directories
                if any(skip in file_path.parts for skip in ['.venv', '.git', '__pycache__']):
                    continue
                    
                if file_path.is_file():
                    self.stats['files_scanned'] += 1
                    
                    # Calculate hash
                    file_hash = self.calculate_hash(file_path)
                    if file_hash:
                        file_info = {
                            'path': file_path,
                            'size': file_path.stat().st_size,
                            'modified': file_path.stat().st_mtime
                        }
                        file_hashes[file_hash].append(file_info)
                        
        # Identify duplicates
        for file_hash, files in file_hashes.items():
            if len(files) > 1:
                self.duplicates[file_hash] = files
                self.stats['duplicates_found'] += len(files) - 1
                self.stats['space_wasted'] += sum(f['size'] for f in files[1:])
                
    def analyze_duplicate_patterns(self):
        """Analyze patterns in duplicate files."""
        patterns = {
            'backup_files': [],
            'test_duplicates': [],
            'archive_duplicates': [],
            'implementation_duplicates': [],
            'config_duplicates': [],
            'doc_duplicates': []
        }
        
        for file_hash, files in self.duplicates.items():
            paths = [f['path'] for f in files]
            
            # Categorize duplicates
            if any('.bak' in str(p) or '.backup' in str(p) for p in paths):
                patterns['backup_files'].append(files)
            elif any('test' in str(p) for p in paths):
                patterns['test_duplicates'].append(files)
            elif any('archive' in str(p) or 'deprecated' in str(p) for p in paths):
                patterns['archive_duplicates'].append(files)
            elif any(p.suffix == '.py' for p in paths):
                patterns['implementation_duplicates'].append(files)
            elif any(p.suffix in ['.yaml', '.yml', '.json'] for p in paths):
                patterns['config_duplicates'].append(files)
            elif any(p.suffix == '.md' for p in paths):
                patterns['doc_duplicates'].append(files)
                
        return patterns
        
    def generate_report(self):
        """Generate detailed duplicate report."""
        patterns = self.analyze_duplicate_patterns()
        
        report = {
            'scan_time': datetime.now().isoformat(),
            'stats': self.stats,
            'duplicate_groups': len(self.duplicates),
            'patterns': {}
        }
        
        # Create detailed pattern report
        for pattern_name, groups in patterns.items():
            if groups:
                report['patterns'][pattern_name] = {
                    'count': len(groups),
                    'examples': []
                }
                
                for group in groups[:3]:  # First 3 examples
                    example = {
                        'files': [str(f['path'].relative_to(self.project_root)) for f in group],
                        'size': group[0]['size'],
                        'newest': max(group, key=lambda x: x['modified'])['path'].name
                    }
                    report['patterns'][pattern_name]['examples'].append(example)
                    
        # Save report
        report_path = self.project_root / 'duplicate_analysis.json'
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
            
        return report
        
    def print_summary(self):
        """Print analysis summary."""
        print("\n" + "="*60)
        print("DUPLICATE FILE ANALYSIS")
        print("="*60)
        print(f"Files scanned: {self.stats['files_scanned']:,}")
        print(f"Duplicate files found: {self.stats['duplicates_found']:,}")
        print(f"Space wasted: {self.stats['space_wasted'] / 1024 / 1024:.2f} MB")
        print(f"Duplicate groups: {len(self.duplicates)}")
        
        patterns = self.analyze_duplicate_patterns()
        
        print("\nDuplicate patterns:")
        for pattern, groups in patterns.items():
            if groups:
                print(f"  - {pattern}: {len(groups)} groups")
                
        print("\nTop duplicate files by size:")
        sorted_dups = sorted(
            [(h, files) for h, files in self.duplicates.items()],
            key=lambda x: x[1][0]['size'] * len(x[1]),
            reverse=True
        )
        
        for _, files in sorted_dups[:10]:
            size = files[0]['size']
            total_size = size * len(files)
            print(f"\n  Size: {size:,} bytes x {len(files)} copies = {total_size:,} bytes")
            for f in files:
                print(f"    - {f['path'].relative_to(self.project_root)}")
                
    def suggest_removals(self):
        """Suggest which duplicates to remove."""
        suggestions = []
        
        for file_hash, files in self.duplicates.items():
            # Sort by path to identify canonical vs duplicate
            sorted_files = sorted(files, key=lambda x: str(x['path']))
            
            # Identify canonical file (prefer non-archive, non-backup)
            canonical = None
            for f in sorted_files:
                path_str = str(f['path'])
                if not any(bad in path_str for bad in ['archive', 'backup', '.bak', '_old', 'deprecated']):
                    canonical = f
                    break
                    
            if not canonical:
                canonical = sorted_files[0]  # Default to first
                
            # Mark others for removal
            for f in files:
                if f != canonical:
                    suggestions.append({
                        'remove': f['path'],
                        'keep': canonical['path'],
                        'reason': self.get_removal_reason(f['path'], canonical['path'])
                    })
                    
        return suggestions
        
    def get_removal_reason(self, remove_path, keep_path):
        """Get reason for removing duplicate."""
        remove_str = str(remove_path)
        
        if 'archive' in remove_str:
            return "File in archive directory"
        elif '.bak' in remove_str or '.backup' in remove_str:
            return "Backup file"
        elif 'deprecated' in remove_str:
            return "Deprecated file"
        elif '_old' in remove_str:
            return "Old version"
        elif 'test' in remove_str and 'test' not in str(keep_path):
            return "Test duplicate of main file"
        else:
            return "Duplicate file"
            

def main():
    parser = argparse.ArgumentParser(description='Find duplicate files in project')
    parser.add_argument('--remove-duplicates', action='store_true',
                        help='Remove duplicate files (keeping one copy)')
    parser.add_argument('--keep-newest', action='store_true',
                        help='When removing, keep the newest file')
    parser.add_argument('--project-root', type=str,
                        default=os.path.dirname(os.path.abspath(__file__)),
                        help='Project root directory')
    
    args = parser.parse_args()
    
    finder = DuplicateFinder(args.project_root)
    finder.find_duplicates()
    
    report = finder.generate_report()
    finder.print_summary()
    
    # Get removal suggestions
    suggestions = finder.suggest_removals()
    
    if suggestions:
        print(f"\n\nFound {len(suggestions)} files that could be removed:")
        
        # Group by reason
        by_reason = defaultdict(list)
        for s in suggestions:
            by_reason[s['reason']].append(s)
            
        for reason, items in by_reason.items():
            print(f"\n{reason}: {len(items)} files")
            for item in items[:3]:  # Show first 3
                print(f"  - Remove: {item['remove'].relative_to(finder.project_root)}")
                print(f"    Keep: {item['keep'].relative_to(finder.project_root)}")
                
        if args.remove_duplicates:
            response = input("\nRemove these duplicates? (yes/no): ")
            if response.lower() == 'yes':
                removed = 0
                for s in suggestions:
                    try:
                        s['remove'].unlink()
                        removed += 1
                    except Exception as e:
                        print(f"Error removing {s['remove']}: {e}")
                print(f"\nRemoved {removed} duplicate files")
                
    print(f"\nDetailed report saved to: duplicate_analysis.json")
    

if __name__ == '__main__':
    main()