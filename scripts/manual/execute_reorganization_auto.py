#!/usr/bin/env python3
"""
AUTOMATIC REORGANIZATION EXECUTION
==================================

Non-interactive version for automatic execution
"""

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime
import subprocess
import json

# Import the reorganizer
from implement_reorganization import SafeReorganizer

def main():
    base_path = Path("/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/Scripts")
    
    print("🧠 ULTRATHINKING: EXECUTING AUTOMATIC REORGANIZATION")
    print("=" * 70)
    print("This will:")
    print("1. Create a full backup")
    print("2. Reorganize the project structure")
    print("3. Update all imports")
    print("4. Verify functionality")
    print("=" * 70)
    
    # Create the reorganizer
    reorganizer = SafeReorganizer(base_path)
    
    # Step 1: Create backup
    print("\n📦 Step 1: Creating backup...")
    reorganizer.create_backup()
    
    # Step 2: Initialize git
    print("\n📝 Step 2: Initializing git...")
    reorganizer.init_git()
    
    # Step 3: Create directory structure
    print("\n📁 Step 3: Creating new directory structure...")
    reorganizer.create_directory_structure()
    
    # Step 4: Move files safely
    print("\n🚚 Step 4: Moving files to new locations...")
    reorganizer.move_files_safely()
    
    # Step 5: Update imports
    print("\n🔧 Step 5: Updating imports...")
    reorganizer.update_imports()
    
    # Step 6: Create documentation
    print("\n📚 Step 6: Creating documentation...")
    reorganizer.create_main_readme()
    
    # Step 7: Verify functionality
    print("\n🧪 Step 7: Verifying functionality...")
    reorganizer.verify_functionality()
    
    print("\n" + "=" * 70)
    print("🎉 REORGANIZATION COMPLETE!")
    print(f"✅ Backup created at: {reorganizer.backup_path}")
    print("✅ Files moved to new locations")
    print("✅ Imports updated")
    print("✅ Documentation created")
    
    print("\n📋 Next steps:")
    print("1. Review the changes")
    print("2. Test key functionality:")
    print("   - python scripts/vpn/bulletproof_vpn_connect.py")
    print("   - python -m src.publishers.ieee_publisher")
    print("3. If everything works, run cleanup_after_reorg.py")
    print("4. If issues, use restore script")
    
    # Create a summary report
    summary = {
        'timestamp': datetime.now().isoformat(),
        'backup_path': str(reorganizer.backup_path),
        'moved_files': len(reorganizer.moved_files),
        'new_structure': {
            'scripts/': 'Production-ready scripts',
            'experiments/': 'Experimental code',
            'tests/': 'Organized test suite',
            'archive/': 'Old code and screenshots'
        }
    }
    
    summary_path = base_path / "REORGANIZATION_SUMMARY.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n📊 Summary saved to: {summary_path}")

if __name__ == "__main__":
    main()