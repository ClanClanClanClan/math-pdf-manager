#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pdfmgr - Simple, Fast Academic PDF Manager
A clean command-line tool without over-engineering.

Usage:
    pdfmgr check <file_or_directory>    Check filename validity
    pdfmgr fix <file_or_directory>      Fix filenames (with preview)
    pdfmgr download <identifier>        Download paper (ArXiv ID, DOI, URL)
    pdfmgr --help                       Show help
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional
import asyncio
import os

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import our improved configuration manager
from core.config_manager import get_config

# Import the excellent academic filename validation
from validators.filename_checker.core import check_filename

# Import proper downloader - only working implementations
try:
    from downloader.proper_downloader import ProperAcademicDownloader, DownloadResult
    DOWNLOAD_AVAILABLE = True
except ImportError as e:
    DOWNLOAD_AVAILABLE = False
    DOWNLOAD_ERROR = str(e)


class SimplePDFManager:
    """Simple PDF manager without dependency injection complexity."""
    
    def __init__(self):
        """Initialize with configuration."""
        print("Loading configuration...")
        self.config = get_config()
        print(f"✓ Loaded {len(self.config.capitalization_whitelist)} academic terms")
    
    def check_file(self, file_path: Path) -> bool:
        """Check a single file's validity."""
        if not file_path.suffix.lower() == '.pdf':
            return True  # Skip non-PDF files
        
        filename = file_path.name
        result = check_filename(
            filename,
            known_words=set(),  # Could load from files if needed
            whitelist_pairs=[],
            exceptions=set(self.config.capitalization_whitelist),
            compound_terms=set(self.config.compound_terms),
            capitalization_whitelist=set(self.config.capitalization_whitelist),
            multiword_surnames=set(),  # Could load if needed
            name_dash_whitelist=set(),
            debug=False
        )
        
        # Display results
        if result.is_valid:
            print(f"✓ {filename}")
        else:
            print(f"✗ {filename}")
            for msg in result.messages:
                if msg.type == "error":
                    print(f"  ERROR: {msg.message}")
                elif msg.type == "warning":
                    print(f"  WARN: {msg.message}")
        
        # Show suggested fix if available
        if result.corrected_filename and result.corrected_filename != filename:
            print(f"  SUGGESTED: {result.corrected_filename}")
        
        return result.is_valid
    
    def check_directory(self, directory: Path) -> int:
        """Check all PDFs in a directory."""
        pdf_files = list(directory.glob("*.pdf"))
        
        if not pdf_files:
            print(f"No PDF files found in {directory}")
            return 0
        
        print(f"\nChecking {len(pdf_files)} PDF files...")
        print("=" * 60)
        
        valid_count = 0
        for pdf_file in sorted(pdf_files):
            if self.check_file(pdf_file):
                valid_count += 1
            print()  # Blank line between files
        
        # Summary
        print("=" * 60)
        print(f"Summary: {valid_count}/{len(pdf_files)} files are valid")
        
        invalid_count = len(pdf_files) - valid_count
        if invalid_count > 0:
            print(f"Found {invalid_count} files with issues")
        
        return invalid_count
    
    def fix_file(self, file_path: Path, dry_run: bool = True) -> bool:
        """Fix a single file's name."""
        if not file_path.suffix.lower() == '.pdf':
            return True
        
        filename = file_path.name
        result = check_filename(
            filename,
            known_words=set(),
            whitelist_pairs=[],
            exceptions=set(self.config.capitalization_whitelist),
            compound_terms=set(self.config.compound_terms),
            capitalization_whitelist=set(self.config.capitalization_whitelist),
            multiword_surnames=set(),
            name_dash_whitelist=set(),
            debug=False,
            auto_fix_nfc=True,
            auto_fix_authors=True
        )
        
        if result.corrected_filename and result.corrected_filename != filename:
            new_path = file_path.parent / result.corrected_filename
            
            if dry_run:
                print(f"Would rename:")
                print(f"  FROM: {filename}")
                print(f"  TO:   {result.corrected_filename}")
            else:
                # Actual rename
                if new_path.exists():
                    print(f"✗ Cannot rename: {result.corrected_filename} already exists")
                    return False
                
                file_path.rename(new_path)
                print(f"✓ Renamed: {filename} → {result.corrected_filename}")
            
            return True
        else:
            if not result.is_valid:
                print(f"✗ Cannot auto-fix: {filename}")
                for msg in result.messages:
                    if msg.type == "error":
                        print(f"  {msg.message}")
            return False
    
    def download(self, identifier: str, output_dir: Optional[Path] = None) -> bool:
        """Download a paper by identifier (ArXiv ID, DOI, URL)."""
        if not DOWNLOAD_AVAILABLE:
            print(f"✗ Download feature not available: {DOWNLOAD_ERROR}")
            print("\nInstall required dependencies:")
            print("  pip install aiohttp aiofiles")
            return False
        
        # Set output directory
        if output_dir is None:
            output_dir = Path.cwd()
        
        print(f"🔍 Searching for: {identifier}")
        
        # Run integrated download in sync context
        try:
            # Create event loop if needed
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Create proper downloader with custom directory
            downloader = ProperAcademicDownloader(str(output_dir))
            
            # Run download - uses real open access sources + existing institutional system
            result = loop.run_until_complete(downloader.download(identifier))
            
            # Clean up
            loop.run_until_complete(downloader.close())
            
            if result.success:
                print(f"\n✓ Downloaded successfully!")
                print(f"  Source: {result.source_used}")
                print(f"  File: {result.file_path}")
                print(f"  Size: {result.file_size:,} bytes")
                print(f"  Time: {result.download_time:.1f}s")
                
                # Check filename validity
                downloaded_path = Path(result.file_path)
                print(f"\n📋 Checking filename...")
                if self.check_file(downloaded_path):
                    print("✓ Filename is valid")
                else:
                    print("\n🔧 Filename needs fixing")
                    if self.fix_file(downloaded_path, dry_run=False):
                        print("✓ Fixed filename")
                
                return True
            else:
                print(f"\n✗ Download failed: {result.error}")
                return False
                
        except Exception as e:
            print(f"\n✗ Download error: {str(e)}")
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Simple Academic PDF Manager - Fast filename validation and fixing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  pdfmgr check paper.pdf                   Check a single file
  pdfmgr check /path/to/papers/            Check all PDFs in directory
  pdfmgr fix --dry-run /path/to/papers/    Preview fixes without applying
  pdfmgr fix --apply /path/to/papers/      Actually rename files
  pdfmgr download arxiv:2301.07041         Download from ArXiv
  pdfmgr download 10.1038/nature12373      Download by DOI
  pdfmgr download "https://arxiv.org/..."  Download by URL
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Check command
    check_parser = subparsers.add_parser('check', help='Check filename validity')
    check_parser.add_argument('path', type=Path, help='File or directory to check')
    
    # Fix command
    fix_parser = subparsers.add_parser('fix', help='Fix filenames')
    fix_parser.add_argument('path', type=Path, help='File or directory to fix')
    fix_parser.add_argument('--dry-run', action='store_true', default=True,
                          help='Preview changes without applying (default)')
    fix_parser.add_argument('--apply', action='store_true',
                          help='Actually rename files')
    
    # Download command
    download_parser = subparsers.add_parser('download', help='Download papers')
    download_parser.add_argument('identifier', help='ArXiv ID, DOI, or URL')
    download_parser.add_argument('-o', '--output', type=Path, 
                               help='Output directory (default: current)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Initialize manager
    try:
        manager = SimplePDFManager()
    except Exception as e:
        print(f"Failed to initialize: {e}")
        return 1
    
    # Execute command
    if args.command == 'check':
        if args.path.is_file():
            valid = manager.check_file(args.path)
            return 0 if valid else 1
        elif args.path.is_dir():
            invalid_count = manager.check_directory(args.path)
            return min(invalid_count, 255)  # Exit code max is 255
        else:
            print(f"Error: {args.path} is not a file or directory")
            return 1
    
    elif args.command == 'fix':
        dry_run = not args.apply
        
        if dry_run:
            print("🔍 DRY RUN MODE - No files will be renamed")
            print()
        
        if args.path.is_file():
            success = manager.fix_file(args.path, dry_run)
            return 0 if success else 1
        elif args.path.is_dir():
            fixed_count = 0
            pdf_files = list(args.path.glob("*.pdf"))
            
            for pdf_file in sorted(pdf_files):
                if manager.fix_file(pdf_file, dry_run):
                    fixed_count += 1
                print()
            
            print(f"\nFixed {fixed_count}/{len(pdf_files)} files")
            return 0
        else:
            print(f"Error: {args.path} is not a file or directory")
            return 1
    
    elif args.command == 'download':
        success = manager.download(args.identifier, args.output)
        return 0 if success else 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())