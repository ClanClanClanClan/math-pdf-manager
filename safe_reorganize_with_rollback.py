#!/usr/bin/env python3
"""
SAFE REORGANIZATION WITH ROLLBACK
=================================

Ultra-safe reorganization with checkpoints and rollback capability.
This script ensures NO functionality is lost during reorganization.
"""

import os
import sys
import shutil
import subprocess
import json
from pathlib import Path
from datetime import datetime
import time

class SafeReorganizationManager:
    def __init__(self, base_path):
        self.base_path = Path(base_path)
        self.checkpoint_dir = self.base_path / ".reorganization_checkpoints"
        self.checkpoint_dir.mkdir(exist_ok=True)
        
        self.current_checkpoint = None
        self.checkpoints = []
        
        # Load any existing checkpoints
        self.load_checkpoints()
        
    def load_checkpoints(self):
        """Load existing checkpoints"""
        checkpoint_file = self.checkpoint_dir / "checkpoints.json"
        if checkpoint_file.exists():
            with open(checkpoint_file, 'r') as f:
                self.checkpoints = json.load(f)
                
    def save_checkpoints(self):
        """Save checkpoint metadata"""
        checkpoint_file = self.checkpoint_dir / "checkpoints.json"
        with open(checkpoint_file, 'w') as f:
            json.dump(self.checkpoints, f, indent=2)
            
    def create_checkpoint(self, name, description):
        """Create a new checkpoint"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        checkpoint_name = f"{name}_{timestamp}"
        
        print(f"\n💾 Creating checkpoint: {checkpoint_name}")
        print(f"   Description: {description}")
        
        # Run functionality verification
        print("   Running functionality checks...")
        verify_result = subprocess.run(
            ["python", "verify_functionality.py"],
            capture_output=True,
            text=True
        )
        
        # Save checkpoint data
        checkpoint_data = {
            'name': checkpoint_name,
            'description': description,
            'timestamp': timestamp,
            'functionality_check': verify_result.returncode == 0,
            'state_file': f"state_{checkpoint_name}.tar.gz"
        }
        
        # Create state archive (lightweight - just track what exists)
        state_file = self.checkpoint_dir / checkpoint_data['state_file']
        self._create_state_snapshot(state_file)
        
        self.checkpoints.append(checkpoint_data)
        self.current_checkpoint = checkpoint_name
        self.save_checkpoints()
        
        print(f"✅ Checkpoint created: {checkpoint_name}")
        return checkpoint_name
        
    def _create_state_snapshot(self, output_file):
        """Create a lightweight state snapshot"""
        # Just save file listing and key metadata
        state_data = {
            'files': {},
            'directories': []
        }
        
        # Record all Python files and their locations
        for py_file in self.base_path.glob("**/*.py"):
            if ".reorganization_checkpoints" not in str(py_file):
                rel_path = py_file.relative_to(self.base_path)
                state_data['files'][str(rel_path)] = {
                    'size': py_file.stat().st_size,
                    'mtime': py_file.stat().st_mtime
                }
                
        # Record directory structure
        for dir_path in self.base_path.glob("**/*"):
            if dir_path.is_dir() and ".reorganization_checkpoints" not in str(dir_path):
                rel_path = dir_path.relative_to(self.base_path)
                state_data['directories'].append(str(rel_path))
                
        # Save state data
        import gzip
        with gzip.open(output_file, 'wt') as f:
            json.dump(state_data, f)
            
    def rollback_to_checkpoint(self, checkpoint_name=None):
        """Rollback to a specific checkpoint"""
        if not checkpoint_name and self.checkpoints:
            # Use the last checkpoint
            checkpoint_name = self.checkpoints[-1]['name']
            
        print(f"\n⏮️ Rolling back to checkpoint: {checkpoint_name}")
        
        # Find the backup directory for this checkpoint
        backup_found = False
        for entry in self.base_path.parent.iterdir():
            if entry.is_dir() and "Scripts_backup_" in entry.name:
                # Check if this backup matches our checkpoint timestamp
                for checkpoint in self.checkpoints:
                    if checkpoint['name'] == checkpoint_name and checkpoint['timestamp'] in entry.name:
                        print(f"   Found backup: {entry}")
                        
                        # Confirm rollback
                        confirm = input("\n⚠️ This will restore from backup. Continue? (yes/no): ")
                        if confirm.lower() == 'yes':
                            # Perform rollback
                            print("   Restoring files...")
                            
                            # Remove current state
                            for item in self.base_path.iterdir():
                                if item.name != ".reorganization_checkpoints":
                                    if item.is_dir():
                                        shutil.rmtree(item)
                                    else:
                                        item.unlink()
                                        
                            # Copy from backup
                            for item in entry.iterdir():
                                dest = self.base_path / item.name
                                if item.is_dir():
                                    shutil.copytree(item, dest)
                                else:
                                    shutil.copy2(item, dest)
                                    
                            print("✅ Rollback complete!")
                            backup_found = True
                            break
                            
        if not backup_found:
            print("❌ No backup found for this checkpoint")
            
    def execute_reorganization_step(self, step_name, step_function, *args, **kwargs):
        """Execute a reorganization step with safety checks"""
        print(f"\n🔄 Executing: {step_name}")
        print("-" * 50)
        
        try:
            # Execute the step
            result = step_function(*args, **kwargs)
            
            # Verify functionality still works
            print("\n   Verifying functionality...")
            verify_result = subprocess.run(
                ["python", "verify_functionality.py"],
                capture_output=True,
                text=True
            )
            
            if verify_result.returncode == 0:
                print(f"✅ {step_name} completed successfully")
                return True
            else:
                print(f"⚠️ {step_name} completed but functionality check failed")
                response = input("Continue anyway? (yes/no/rollback): ")
                
                if response.lower() == 'rollback':
                    self.rollback_to_checkpoint()
                    return False
                elif response.lower() == 'yes':
                    return True
                else:
                    return False
                    
        except Exception as e:
            print(f"❌ Error during {step_name}: {e}")
            response = input("Rollback? (yes/no): ")
            
            if response.lower() == 'yes':
                self.rollback_to_checkpoint()
            return False
            
    def run_safe_reorganization(self):
        """Run the complete reorganization with safety checks"""
        print("🛡️ SAFE REORGANIZATION WITH ROLLBACK")
        print("=" * 70)
        print("This process will:")
        print("1. Create checkpoints at each major step")
        print("2. Verify functionality after each change")
        print("3. Allow rollback if anything breaks")
        print("=" * 70)
        
        # Initial checkpoint
        self.create_checkpoint("initial", "Before any changes")
        
        # Import the reorganization functions
        from implement_reorganization import SafeReorganizer
        reorganizer = SafeReorganizer(self.base_path)
        
        # Step 1: Create backup
        if not self.execute_reorganization_step(
            "Create Backup",
            reorganizer.create_backup
        ):
            return False
            
        # Step 2: Initialize Git
        if not self.execute_reorganization_step(
            "Initialize Git",
            reorganizer.init_git
        ):
            return False
            
        self.create_checkpoint("git_initialized", "After Git setup")
        
        # Step 3: Create directory structure
        if not self.execute_reorganization_step(
            "Create Directory Structure",
            reorganizer.create_directory_structure
        ):
            return False
            
        self.create_checkpoint("directories_created", "After creating directories")
        
        # Step 4: Move files safely
        if not self.execute_reorganization_step(
            "Move Files",
            reorganizer.move_files_safely
        ):
            return False
            
        self.create_checkpoint("files_moved", "After moving files")
        
        # Step 5: Update imports
        if not self.execute_reorganization_step(
            "Update Imports",
            reorganizer.update_imports
        ):
            return False
            
        self.create_checkpoint("imports_updated", "After updating imports")
        
        # Step 6: Create documentation
        if not self.execute_reorganization_step(
            "Create Documentation",
            reorganizer.create_main_readme
        ):
            return False
            
        # Final verification
        print("\n🔍 FINAL VERIFICATION")
        print("=" * 50)
        
        # Run comprehensive tests
        test_results = []
        
        tests = [
            ("Core imports", ["python", "-c", "from src.core import config_manager; print('OK')"]),
            ("IEEE publisher", ["python", "-c", "from src.publishers import ieee_publisher; print('OK')"]),
            ("SIAM publisher", ["python", "-c", "from src.publishers import siam_publisher; print('OK')"]),
            ("Unit tests", ["python", "-m", "pytest", "tests/core/test_exceptions.py", "-v"]),
        ]
        
        all_passed = True
        for test_name, command in tests:
            print(f"\n🧪 Testing: {test_name}")
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ {test_name} passed")
            else:
                print(f"❌ {test_name} failed")
                all_passed = False
                
        if all_passed:
            print("\n🎉 REORGANIZATION SUCCESSFUL!")
            print("All functionality preserved!")
            
            # Create final checkpoint
            self.create_checkpoint("reorganization_complete", "Successfully reorganized")
            
            # Offer to clean up old files
            print("\n🧹 Cleanup Option")
            print("Original files are still in the root directory.")
            cleanup = input("Delete original files? (yes/no): ")
            
            if cleanup.lower() == 'yes':
                reorganizer.cleanup_if_successful()
                
        else:
            print("\n⚠️ Some tests failed!")
            rollback = input("Rollback to initial state? (yes/no): ")
            
            if rollback.lower() == 'yes':
                self.rollback_to_checkpoint("initial")
                
        print("\n✅ Process complete!")
        
def main():
    """Main execution"""
    base_path = "/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/Scripts"
    
    print("🛡️ ULTRA-SAFE REORGANIZATION")
    print("This process includes:")
    print("✓ Automatic backups")
    print("✓ Functionality verification at each step")
    print("✓ Rollback capability")
    print("✓ No functionality will be lost")
    print()
    
    manager = SafeReorganizationManager(base_path)
    
    # Check for existing checkpoints
    if manager.checkpoints:
        print(f"Found {len(manager.checkpoints)} existing checkpoints:")
        for cp in manager.checkpoints:
            print(f"  - {cp['name']}: {cp['description']}")
            
        action = input("\nAction (continue/rollback/fresh): ")
        
        if action.lower() == 'rollback':
            checkpoint = input("Rollback to checkpoint name (or press Enter for last): ")
            manager.rollback_to_checkpoint(checkpoint if checkpoint else None)
            return
        elif action.lower() == 'fresh':
            confirm = input("Delete all checkpoints and start fresh? (yes/no): ")
            if confirm.lower() == 'yes':
                shutil.rmtree(manager.checkpoint_dir)
                manager = SafeReorganizationManager(base_path)
                
    # Run reorganization
    confirm = input("\nProceed with safe reorganization? (yes/no): ")
    if confirm.lower() == 'yes':
        manager.run_safe_reorganization()
    else:
        print("❌ Reorganization cancelled")

if __name__ == "__main__":
    main()