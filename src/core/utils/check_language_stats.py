#!/usr/bin/env python3
"""
Language Files Statistics
========================

Quick script to show statistics about the language files.
"""

import yaml
from pathlib import Path
from collections import Counter


def analyze_language_files(languages_dir: str):
    """Analyze and report statistics on language files."""
    languages_dir = Path(languages_dir).expanduser()
    
    print(f"📊 Analyzing language files in: {languages_dir}")
    print("="*60)
    
    total_entries = 0
    file_stats = []
    all_fields = Counter()
    
    yaml_files = sorted(languages_dir.glob("*.yaml"))
    
    for yaml_file in yaml_files:
        if yaml_file.parent.name == "backups":
            continue
            
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            
            entry_count = len(data)
            total_entries += entry_count
            
            # Count fields used
            fields_in_file = set()
            empty_fields = 0
            total_fields = 0
            
            for entry in data.values():
                for field, value in entry.items():
                    fields_in_file.add(field)
                    all_fields[field] += 1
                    total_fields += 1
                    
                    if isinstance(value, str) and not value.strip():
                        empty_fields += 1
                    elif isinstance(value, list) and not value:
                        empty_fields += 1
            
            file_stats.append({
                'file': yaml_file.name,
                'entries': entry_count,
                'unique_fields': len(fields_in_file),
                'empty_fields': empty_fields,
                'total_fields': total_fields,
                'completeness': f"{((total_fields - empty_fields) / total_fields * 100):.1f}%" if total_fields > 0 else "0%"
            })
            
        except Exception as e:
            print(f"❌ Error reading {yaml_file.name}: {e}")
    
    # Report file statistics
    print("\n📁 FILE STATISTICS:")
    print(f"{'File':<20} {'Entries':<10} {'Fields':<10} {'Completeness':<15}")
    print("-"*60)
    
    for stat in file_stats:
        print(f"{stat['file']:<20} {stat['entries']:<10} {stat['unique_fields']:<10} {stat['completeness']:<15}")
    
    print(f"\n📊 TOTAL ENTRIES: {total_entries}")
    
    # Report field usage
    print("\n📋 FIELD USAGE ACROSS ALL FILES:")
    for field, count in all_fields.most_common():
        print(f"  {field:<25} {count:>6} times")
    
    # Look for potential issues
    print("\n⚠️  POTENTIAL ISSUES:")
    
    # Check for entries with same canonical names
    canonical_names = {}
    for yaml_file in yaml_files:
        if yaml_file.parent.name == "backups":
            continue
            
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            
            for key, entry in data.items():
                canon = entry.get('CanonicalLatin', '')
                if canon:
                    if canon in canonical_names:
                        print(f"  Duplicate canonical name '{canon}':")
                        print(f"    - {yaml_file.name}: {key}")
                        print(f"    - {canonical_names[canon]}")
                    else:
                        canonical_names[canon] = f"{yaml_file.name}: {key}"
                        
        except Exception:
            pass


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        dir_path = sys.argv[1]
    else:
        dir_path = "~/Dropbox/Work/Maths/Scripts/data/languages"
    
    analyze_language_files(dir_path)