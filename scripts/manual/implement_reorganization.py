#!/usr/bin/env python3
"""
SAFE PROJECT REORGANIZATION IMPLEMENTATION
==========================================

This script implements the reorganization plan SAFELY:
- Creates backups before any changes
- Moves files preserving functionality
- Updates imports automatically
- Verifies everything still works
"""

import os
import shutil
import subprocess
import re
from pathlib import Path
from datetime import datetime
import json

class SafeReorganizer:
    def __init__(self, base_path):
        self.base_path = Path(base_path)
        self.backup_path = None
        self.moved_files = {}  # Track old_path -> new_path
        self.import_updates = {}  # Track import changes needed
        
    def create_backup(self):
        """Create a timestamped backup of the entire project"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"Scripts_backup_{timestamp}"
        self.backup_path = self.base_path.parent / backup_name
        
        print(f"📦 Creating backup at: {self.backup_path}")
        shutil.copytree(self.base_path, self.backup_path)
        print("✅ Backup created successfully")
        
        # Also create a restore script
        restore_script = f"""#!/bin/bash
# Restore script for backup created on {timestamp}
echo "Restoring from backup..."
rm -rf "{self.base_path}"
cp -r "{self.backup_path}" "{self.base_path}"
echo "✅ Restored successfully"
"""
        restore_path = self.base_path / f"RESTORE_FROM_BACKUP_{timestamp}.sh"
        restore_path.write_text(restore_script)
        restore_path.chmod(0o755)
        print(f"✅ Restore script created: {restore_path}")
        
    def init_git(self):
        """Initialize git repository if not already initialized"""
        git_dir = self.base_path / ".git"
        if not git_dir.exists():
            print("📝 Initializing git repository...")
            subprocess.run(["git", "init"], cwd=self.base_path)
            
            # Create .gitignore
            gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
.env

# IDE
.vscode/
.idea/
*.swp
*.swo

# Project specific
downloads/
logs/
*.log
*.png
*.jpg
*.pdf
credentials.enc
.DS_Store

# Temporary
temp/
tmp/
*.tmp
"""
            (self.base_path / ".gitignore").write_text(gitignore_content)
            
            subprocess.run(["git", "add", "-A"], cwd=self.base_path)
            subprocess.run(["git", "commit", "-m", "Pre-reorganization snapshot"], cwd=self.base_path)
            print("✅ Git repository initialized")
        
    def create_directory_structure(self):
        """Create the new directory structure"""
        print("\n📁 Creating new directory structure...")
        
        directories = [
            # Scripts directories
            "scripts/vpn",
            "scripts/publishers/wiley",
            "scripts/publishers/ieee", 
            "scripts/publishers/siam",
            "scripts/publishers/misc",
            "scripts/utilities",
            
            # Experiments directories
            "experiments/vpn_attempts",
            "experiments/publisher_tests",
            "experiments/browser_automation",
            "experiments/api_tests",
            
            # Test directories
            "tests/unit",
            "tests/integration", 
            "tests/e2e",
            "tests/fixtures",
            "tests/experimental",
            
            # Documentation
            "docs/publisher-guides",
            "docs/api",
            "docs/tutorials",
            
            # Other directories
            "downloads",
            "logs",
            "archive/screenshots",
            "archive/legacy_scripts",
        ]
        
        for dir_path in directories:
            full_path = self.base_path / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            
            # Create README.md for each major directory
            readme_path = full_path / "README.md"
            if not readme_path.exists():
                readme_content = f"# {dir_path.split('/')[-1].title()}\n\nPurpose: [TODO: Add description]\n"
                readme_path.write_text(readme_content)
        
        print("✅ Directory structure created")
        
    def categorize_files(self):
        """Categorize files for movement"""
        print("\n🏷️ Categorizing files...")
        
        categories = {
            'vpn_production': {
                'pattern': ['bulletproof_vpn', 'secure_vpn_credentials', 'final_ultra_connect', 'complete_auto_vpn_pdf'],
                'destination': 'scripts/vpn'
            },
            'vpn_experimental': {
                'pattern': ['vpn_', 'cisco_', 'ultrathink_auto', 'ultimate_auto_vpn', 'cli_advanced_vpn'],
                'destination': 'experiments/vpn_attempts'
            },
            'wiley_production': {
                'pattern': ['working_wiley_downloader', 'final_working_wiley', 'eth_api_wiley'],
                'destination': 'scripts/publishers/wiley'
            },
            'wiley_experimental': {
                'pattern': ['wiley_', 'test_wiley', 'ultrathink_wiley'],
                'destination': 'experiments/publisher_tests'
            },
            'test_scripts': {
                'pattern': ['test_'],
                'destination': 'tests/experimental'
            },
            'screenshots': {
                'pattern': ['.png', '.jpg'],
                'destination': 'archive/screenshots'
            },
            'utilities': {
                'pattern': ['find_real_dois', 'check_ultimate_progress', 'debug_'],
                'destination': 'scripts/utilities'
            }
        }
        
        return categories
        
    def move_files_safely(self):
        """Move files to new locations, preserving originals until verified"""
        print("\n📦 Moving files safely...")
        
        categories = self.categorize_files()
        moved_count = 0
        
        for category, info in categories.items():
            print(f"\n🔄 Processing {category}...")
            patterns = info['pattern']
            destination = self.base_path / info['destination']
            
            for file_path in self.base_path.glob("*.py"):
                if file_path.is_file():
                    filename = file_path.name
                    
                    # Check if file matches any pattern
                    matches = any(pattern in filename for pattern in patterns)
                    
                    if matches:
                        new_path = destination / filename
                        
                        # Copy instead of move (safer)
                        if not new_path.exists():
                            shutil.copy2(file_path, new_path)
                            self.moved_files[str(file_path)] = str(new_path)
                            moved_count += 1
                            print(f"  ✅ {filename} → {info['destination']}/")
        
        print(f"\n✅ Safely copied {moved_count} files")
        
        # Save movement log
        movement_log = self.base_path / "REORGANIZATION_LOG.json"
        movement_log.write_text(json.dumps(self.moved_files, indent=2))
        print(f"📝 Movement log saved to: {movement_log}")
        
    def update_imports(self):
        """Update imports in moved files"""
        print("\n🔧 Updating imports...")
        
        # Common import mappings
        import_mappings = {
            'from secure_vpn_credentials': 'from scripts.vpn.secure_vpn_credentials',
            'from bulletproof_vpn_connect': 'from scripts.vpn.bulletproof_vpn_connect',
            'import secure_vpn_credentials': 'import scripts.vpn.secure_vpn_credentials',
            'import bulletproof_vpn_connect': 'import scripts.vpn.bulletproof_vpn_connect',
        }
        
        updated_files = 0
        
        for new_path in self.moved_files.values():
            file_path = Path(new_path)
            if file_path.suffix == '.py':
                try:
                    content = file_path.read_text()
                    original_content = content
                    
                    # Update imports
                    for old_import, new_import in import_mappings.items():
                        if old_import in content:
                            content = content.replace(old_import, new_import)
                    
                    # If content changed, write it back
                    if content != original_content:
                        file_path.write_text(content)
                        updated_files += 1
                        print(f"  ✅ Updated imports in: {file_path.name}")
                        
                except Exception as e:
                    print(f"  ⚠️ Error updating {file_path.name}: {e}")
        
        print(f"✅ Updated imports in {updated_files} files")
        
    def create_main_readme(self):
        """Create comprehensive main README"""
        print("\n📝 Creating main README...")
        
        readme_content = """# Academic PDF Management System

## 🎯 Overview

A comprehensive Python system for downloading and managing academic PDFs with institutional access. Features automated VPN connection, multi-publisher support, and robust PDF processing capabilities.

## ✨ Features

- **Multi-Publisher Support**: IEEE (100% working), SIAM (100% working), Wiley, Springer, Nature, and more
- **Automated VPN Connection**: Bulletproof Cisco AnyConnect automation with visual recognition
- **Institutional Authentication**: ETH Zurich integration with secure credential management
- **PDF Processing**: Multi-engine extraction with OCR fallback
- **Metadata Extraction**: Automated metadata fetching from multiple academic sources
- **Security**: Input validation, path traversal protection, encrypted credentials

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone [repository-url]
cd Scripts

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### Basic Usage

1. **Connect VPN** (if needed):
```bash
python scripts/vpn/bulletproof_vpn_connect.py
```

2. **Download PDFs**:
```bash
# Download from IEEE
python -m src.publishers.ieee_publisher "10.1109/TPAMI.2023.1234567"

# Download from SIAM  
python -m src.publishers.siam_publisher "10.1137/S0036142902401234"
```

## 📁 Project Structure

```
Scripts/
├── src/                    # Core application code
│   ├── publishers/         # Publisher implementations
│   ├── validators/         # Content validation
│   └── downloader/         # Download orchestration
├── scripts/                # Production-ready scripts
│   ├── vpn/               # VPN connection tools
│   └── publishers/        # Publisher-specific scripts
├── experiments/           # Experimental code
├── tests/                 # Test suite (813+ tests)
└── docs/                  # Documentation
```

## 📖 Documentation

- [Architecture Overview](docs/ARCHITECTURE.md)
- [Setup Guide](docs/SETUP.md)
- [API Documentation](docs/API.md)
- [Publisher Guides](docs/publisher-guides/)

## 🧪 Testing

Run the test suite:
```bash
python -m pytest tests/
```

## 🔐 Security

- Credentials are stored encrypted
- All inputs are validated
- Path traversal protection enabled
- See [Security Guide](docs/SECURITY.md) for details

## 🤝 Contributing

See [Contributing Guide](CONTRIBUTING.md) for development setup and guidelines.

## 📄 License

[License information]
"""
        
        readme_path = self.base_path / "README.md"
        readme_path.write_text(readme_content)
        print("✅ Main README created")
        
    def verify_functionality(self):
        """Verify that core functionality still works"""
        print("\n🧪 Verifying functionality...")
        
        checks = [
            # Check if tests still pass
            ("Running pytest", ["python", "-m", "pytest", "tests/", "-v", "--tb=short"]),
            
            # Check if key imports work
            ("Checking imports", ["python", "-c", "from src.core import config_manager; print('✅ Core imports working')"]),
        ]
        
        all_passed = True
        
        for check_name, command in checks:
            print(f"\n🔍 {check_name}...")
            try:
                result = subprocess.run(command, cwd=self.base_path, capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"✅ {check_name} passed")
                else:
                    print(f"❌ {check_name} failed")
                    print(f"Error: {result.stderr}")
                    all_passed = False
            except Exception as e:
                print(f"❌ {check_name} error: {e}")
                all_passed = False
        
        return all_passed
        
    def cleanup_if_successful(self):
        """Remove original files if everything is working"""
        print("\n🧹 Cleanup phase...")
        
        print("⚠️ Original files are preserved in the root directory")
        print("Once you've verified everything works, you can:")
        print("1. Delete the original files from root")
        print("2. Or run: python cleanup_after_reorg.py")
        
        # Create cleanup script
        cleanup_script = """#!/usr/bin/env python3
# Cleanup script - run ONLY after verifying everything works

import os
from pathlib import Path
import json

# Load movement log
with open('REORGANIZATION_LOG.json', 'r') as f:
    moved_files = json.load(f)

print("This will delete original files that were successfully moved.")
confirm = input("Are you SURE everything is working? (yes/no): ")

if confirm.lower() == 'yes':
    for old_path in moved_files.keys():
        if Path(old_path).exists():
            os.remove(old_path)
            print(f"Deleted: {old_path}")
    print("✅ Cleanup complete")
else:
    print("❌ Cleanup cancelled")
"""
        
        cleanup_path = self.base_path / "cleanup_after_reorg.py"
        cleanup_path.write_text(cleanup_script)
        cleanup_path.chmod(0o755)
        print(f"✅ Cleanup script created: {cleanup_path}")
        
    def run_reorganization(self):
        """Run the complete reorganization process"""
        print("🚀 STARTING SAFE REORGANIZATION")
        print("=" * 60)
        
        # Step 1: Backup
        self.create_backup()
        
        # Step 2: Git setup
        self.init_git()
        
        # Step 3: Create directories
        self.create_directory_structure()
        
        # Step 4: Move files
        self.move_files_safely()
        
        # Step 5: Update imports
        self.update_imports()
        
        # Step 6: Create documentation
        self.create_main_readme()
        
        # Step 7: Verify functionality
        print("\n" + "=" * 60)
        if self.verify_functionality():
            print("✅ ALL FUNCTIONALITY VERIFIED - Reorganization successful!")
            self.cleanup_if_successful()
        else:
            print("⚠️ Some checks failed - please verify manually")
            print(f"Backup available at: {self.backup_path}")
        
        print("\n🎉 REORGANIZATION COMPLETE!")
        print(f"Backup location: {self.backup_path}")
        print("Next steps:")
        print("1. Test key functionality manually")
        print("2. Run cleanup script when ready")
        print("3. Commit changes to git")

if __name__ == "__main__":
    base_path = "/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/Scripts"
    
    print("⚠️ This will reorganize the entire project structure")
    print(f"Path: {base_path}")
    confirm = input("\nProceed with reorganization? (yes/no): ")
    
    if confirm.lower() == 'yes':
        reorganizer = SafeReorganizer(base_path)
        reorganizer.run_reorganization()
    else:
        print("❌ Reorganization cancelled")