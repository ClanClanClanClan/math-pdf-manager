#!/usr/bin/env python3
"""
Script to audit, deduplicate, and sort language YAML files.
Keeps the most complete entries when duplicates are found.
"""

import os
import sys
import yaml
import shutil
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Set, Any

def create_backup(data_dir: Path) -> Path:
    """Create a timestamped backup of all files in the data directory."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = data_dir / "backups" / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy all YAML files to backup
    for yaml_file in data_dir.glob("*.yaml"):
        shutil.copy2(yaml_file, backup_dir / yaml_file.name)
    
    print(f"Created backup in: {backup_dir}")
    return backup_dir

def calculate_completeness_score(entry: Dict[str, Any]) -> int:
    """Calculate a completeness score for an entry. Higher score = more complete."""
    score = 0
    
    # Award points for non-empty fields
    for field, value in entry.items():
        if value:
            if isinstance(value, str) and value.strip():
                score += 1
                # Extra points for longer comments
                if field == "Comments":
                    score += len(value) // 50  # 1 extra point per 50 chars
            elif isinstance(value, list) and len(value) > 0:
                score += len(value)  # Points for each variant
    
    return score

def normalize_name(name: str) -> str:
    """Normalize a name for comparison (lowercase, no spaces/punctuation)."""
    return ''.join(c.lower() for c in name if c.isalnum())

def find_duplicates(entries: Dict[str, Dict[str, Any]]) -> Dict[str, List[str]]:
    """Find potential duplicates based on various criteria."""
    duplicates = defaultdict(list)
    
    # Build indices for different fields
    canonical_latin_index = defaultdict(list)
    mathscinet_index = defaultdict(list)
    variant_index = defaultdict(list)
    
    for key, entry in entries.items():
        # Index by CanonicalLatin
        if canonical_latin := entry.get("CanonicalLatin", "").strip():
            canonical_latin_index[normalize_name(canonical_latin)].append(key)
        
        # Index by MathSciNet
        if mathscinet := entry.get("MathSciNet", "").strip():
            mathscinet_index[normalize_name(mathscinet)].append(key)
        
        # Index by all variants
        if variants := entry.get("AllCommonVariants", []):
            for variant in variants:
                if isinstance(variant, str):
                    variant_index[normalize_name(variant)].append(key)
    
    # Collect duplicate groups
    seen_keys = set()
    
    for index in [canonical_latin_index, mathscinet_index, variant_index]:
        for normalized_name, keys in index.items():
            if len(keys) > 1:
                # Create a unique group ID from sorted keys
                group_id = tuple(sorted(keys))
                if group_id not in seen_keys:
                    seen_keys.add(group_id)
                    duplicates[group_id[0]] = list(group_id)
    
    return duplicates

def deduplicate_entries(entries: Dict[str, Dict[str, Any]], duplicates: Dict[str, List[str]]) -> Dict[str, Dict[str, Any]]:
    """Remove duplicates, keeping the most complete entry."""
    processed_keys = set()
    cleaned_entries = {}
    
    for primary_key, duplicate_keys in duplicates.items():
        if any(key in processed_keys for key in duplicate_keys):
            continue
        
        # Find the most complete entry
        best_key = None
        best_score = -1
        
        for key in duplicate_keys:
            if key in entries:
                score = calculate_completeness_score(entries[key])
                if score > best_score:
                    best_score = score
                    best_key = key
        
        if best_key:
            cleaned_entries[best_key] = entries[best_key]
            processed_keys.update(duplicate_keys)
            
            if len(duplicate_keys) > 1:
                print(f"  Merged duplicates: {', '.join(duplicate_keys)} -> kept {best_key} (score: {best_score})")
    
    # Add all non-duplicate entries
    for key, entry in entries.items():
        if key not in processed_keys:
            cleaned_entries[key] = entry
    
    return cleaned_entries

def process_yaml_file(file_path: Path) -> Tuple[int, int]:
    """Process a single YAML file: deduplicate and sort."""
    print(f"\nProcessing: {file_path.name}")
    
    try:
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        
        original_count = len(data)
        
        # Find and remove duplicates
        duplicates = find_duplicates(data)
        cleaned_data = deduplicate_entries(data, duplicates)
        
        # Sort alphabetically by key
        sorted_data = dict(sorted(cleaned_data.items(), key=lambda x: x[0].lower()))
        
        # Write back to file with nice formatting
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(sorted_data, f, 
                      default_flow_style=False, 
                      allow_unicode=True,
                      sort_keys=False,  # We already sorted
                      width=120)
        
        final_count = len(sorted_data)
        removed_count = original_count - final_count
        
        print(f"  Original entries: {original_count}")
        print(f"  Final entries: {final_count}")
        print(f"  Removed: {removed_count}")
        
        return original_count, final_count
        
    except yaml.YAMLError as e:
        print(f"  ERROR: Failed to parse YAML file - {e}")
        print(f"  Skipping file due to syntax errors. Please fix manually.")
        return 0, 0
    except Exception as e:
        print(f"  ERROR: Unexpected error - {e}")
        print(f"  Skipping file.")
        return 0, 0

def main():
    """Main function to process all language files."""
    # Set up the data directory
    data_dir = Path.home() / "Dropbox" / "Work" / "Maths" / "Scripts" / "data" / "languages"
    
    if not data_dir.exists():
        print(f"Error: Directory not found: {data_dir}")
        sys.exit(1)
    
    # Create backup
    print("Creating backup of all files...")
    backup_dir = create_backup(data_dir)
    
    # Process all YAML files
    yaml_files = sorted(data_dir.glob("*.yaml"))
    
    if not yaml_files:
        print("No YAML files found in the directory.")
        return
    
    print(f"\nFound {len(yaml_files)} YAML files to process.")
    
    total_original = 0
    total_final = 0
    processed_files = 0
    skipped_files = []
    
    for yaml_file in yaml_files:
        original, final = process_yaml_file(yaml_file)
        if original == 0 and final == 0:
            skipped_files.append(yaml_file.name)
        else:
            processed_files += 1
            total_original += original
            total_final += final
    
    # Summary
    print("\n" + "="*50)
    print("SUMMARY:")
    print(f"Files found: {len(yaml_files)}")
    print(f"Files successfully processed: {processed_files}")
    if skipped_files:
        print(f"Files skipped due to errors: {', '.join(skipped_files)}")
    print(f"Total original entries: {total_original}")
    print(f"Total final entries: {total_final}")
    print(f"Total removed: {total_original - total_final}")
    print(f"Backup location: {backup_dir}")
    print("="*50)

if __name__ == "__main__":
    main()