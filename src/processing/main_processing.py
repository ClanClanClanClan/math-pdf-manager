#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main Processing Module
Phase 1, Week 2: Extracted from main.py to reduce file size

Contains the core processing logic for the Math-PDF manager.
"""

from pathlib import Path
from typing import List, Any

from src.core.utils.service_registry import get_logging_service
from src.core.config.config_loader import ConfigurationData
from src.validators.filename_checker import batch_check_filenames, enable_debug as enable_filename_debug
from src.core.text_processing.my_spellchecker import SpellChecker, SpellCheckerConfig
from utils import canonicalize, is_canonically_equivalent
from reporter import generate_html_report, generate_csv_report
from scanner import scan_directory
from file_operations import resolve_path, normalize_file_metadata, safe_file_rename
from duplicate_detector import find_duplicates


def process_files(args, config_data: ConfigurationData, script_dir: Path) -> None:
    """
    Main file processing logic extracted from main function.
    
    Args:
        args: Command line arguments
        config_data: Loaded configuration data
        script_dir: Script directory path
    """
    logging_service = get_logging_service()
    
    # Scan directories
    logging_service.info("=== SCANNING DIRECTORIES ===")
    
    # Resolve root paths
    base_folder = config_data.config.get("base_maths_folder", script_dir)
    roots = []
    
    if args.root:
        # Check if it's a shortcut from config
        shortcuts = config_data.config.get("folder_shortcuts", {})
        if args.root in shortcuts:
            shortcut_paths = shortcuts[args.root]
            if isinstance(shortcut_paths, list):
                roots = [resolve_path(p, base_folder) for p in shortcut_paths]
            else:
                logging_service.error(
                    f"Invalid shortcut format for '{args.root}': {type(shortcut_paths)}"
                )
                roots = [args.root]
        else:
            roots = [args.root]
    else:
        # Default to base folder
        roots = [str(base_folder)]
    
    # Validate roots exist
    from os.path import exists
    for r in roots:
        if not r or not exists(r):
            logging_service.error("Folder not found: %s", r)
            return
    
    # Scan all roots
    files: List[dict[str, Any]] = []
    for r in roots:
        logging_service.info(f"Scanning directory: {r}")
        dir_files = scan_directory(r)
        logging_service.info(f"  Found {len(dir_files)} files in {r}")
        files.extend(dir_files)
    
    logging_service.info(f"Total files found: {len(files)}")
    
    # Check max-files limit (security enhancement)
    if hasattr(args, 'max_files') and len(files) > args.max_files:
        logging_service.warning(
            f"Found {len(files)} files, exceeding max-files limit of {args.max_files}. "
            f"Processing only the first {args.max_files} files."
        )
        files = files[:args.max_files]
    
    # Normalize file metadata
    logging_service.info("Normalizing file metadata...")
    files = normalize_file_metadata(files)
    
    # Count files with valid filenames
    files_with_filename = sum(
        1 for f in files if f.get("filename") and f["filename"] != "UNKNOWN"
    )
    logging_service.info(f"Files with valid filenames: {files_with_filename}")
    
    # Check pattern matches
    if args.debug:
        pattern_matches = 0
        for f in files:
            filename = f.get("filename", "")
            if " - " in filename:
                pattern_matches += 1
                if args.debug:
                    logging_service.debug(f"  Pattern match: {filename}")
            else:
                if args.debug:
                    logging_service.debug(f"  NO pattern match: {filename}")
        
        logging_service.info(
            f"Files matching 'Author - Title' pattern: {pattern_matches}/{len(files)}"
        )
    
    # Run duplicate detection if requested
    if not args.problems_only:
        logging_service.info("=== RUNNING DUPLICATE DETECTION ===")
        duplicates = find_duplicates(files)
        
        if duplicates:
            logging_service.info(f"Found {len(duplicates)} sets of duplicates:")
            for i, dup_set in enumerate(duplicates[:10]):  # Show first 10
                logging_service.info(f"  Set {i+1}:")
                for file_info in dup_set[:3]:  # Show first 3 in each set
                    logging_service.info(f"    - {file_info['filename']}")
                if len(dup_set) > 3:
                    logging_service.info(f"    ... and {len(dup_set) - 3} more")
        else:
            logging_service.info("No duplicates found")
    
    # Run filename checks
    logging_service.info("=== RUNNING FILENAME CHECKS ===")
    
    # Enable debug mode for filename checker if requested
    if args.debug or args.verbose:
        enable_filename_debug()
    
    # Create spell checker configuration
    # Note: SpellCheckerConfig doesn't accept multiword_surnames or exceptions
    spell_config = SpellCheckerConfig(
        known_words=config_data.known_words | config_data.compound_terms,
        capitalization_whitelist=config_data.capitalization_whitelist,
        name_dash_whitelist=config_data.name_dash_whitelist,
    )
    spell_checker = SpellChecker(spell_config)
    
    # Run batch checks
    checks = batch_check_filenames(
        files,
        checker=spell_checker,
        check_unicode_normalization=not args.ignore_nfc_macos,
        check_author_format=True,
        auto_fix_authors=args.fix_auth,
        auto_fix_nfc=args.fix_nfc,
        verbose=args.debug or args.verbose,
    )
    
    logging_service.info(f"Checked {len(checks)} files")
    
    # Count results
    files_with_errors = sum(1 for r in checks if r.get("errors"))
    files_with_suggestions = sum(1 for r in checks if r.get("suggestions"))
    files_with_fixes = sum(1 for r in checks if r.get("fixed_filename"))
    logging_service.info(f"Files with errors: {files_with_errors}")
    logging_service.info(f"Files with suggestions: {files_with_suggestions}")
    logging_service.info(f"Files with proposed fixes: {files_with_fixes}")
    
    # Auto-fix if requested
    rename_count = 0
    if args.fix_nfc or args.fix_auth:
        logging_service.info("=== AUTO-FIX MODE ===")
        
        for result in checks:
            if not result.get("fixed_filename"):
                continue
            
            old_name = result["filename"]
            new_name = result["fixed_filename"]
            
            # Skip if no actual change
            if old_name == new_name:
                continue
            
            # Check what type of fix this is
            is_nfc_fix = is_canonically_equivalent(old_name, new_name)
            is_author_fix = result.get("fixed_author") is not None
            
            # Decide if we should apply this fix
            should_fix = False
            if args.fix_nfc and is_nfc_fix:
                should_fix = True
            if args.fix_auth and is_author_fix:
                should_fix = True
            
            if should_fix and not args.dry_run:
                # Perform the rename
                old_path = Path(result["path"])
                new_path = old_path.parent / new_name
                
                # Check if backup is requested
                create_backup = hasattr(args, 'backup') and args.backup
                if safe_file_rename(old_path, new_path, create_backup):
                    rename_count += 1
            elif should_fix and args.dry_run:
                logging_service.info(f"[DRY RUN] Would rename: {old_name} → {new_name}")
    
    if rename_count > 0:
        logging_service.info(f"✅ Renamed {rename_count} files")
    
    # Generate reports
    logging_service.info("=== GENERATING REPORTS ===")
    generate_html_report(
        checks,
        output_path=args.output,
        template_dir=args.template_dir,
        hide_clean=bool(args.problems_only),
    )
    generate_csv_report(checks, output_path=args.csv_output)
    
    # Generate JSON output if requested
    if hasattr(args, 'json') and args.json:
        import json
        json_output = {
            "total_files": len(files),
            "files_with_errors": files_with_errors,
            "files_with_suggestions": files_with_suggestions,
            "files_with_fixes": files_with_fixes,
            "files_renamed": rename_count,
            "checks": [
                {
                    "filename": check.get("filename", ""),
                    "path": check.get("path", ""),
                    "errors": check.get("errors", []),
                    "suggestions": check.get("suggestions", []),
                    "fixed_filename": check.get("fixed_filename", None)
                }
                for check in checks if check.get("errors") or check.get("suggestions")
            ] if args.problems_only else checks
        }
        
        json_output_path = Path(args.output).parent / "mathpdf_results.json"
        with open(json_output_path, "w", encoding="utf-8") as f:
            json.dump(json_output, f, indent=2, ensure_ascii=False)
        logging_service.info(f"JSON output written to: {json_output_path}")
    
    logging_service.info("All done ✅")
    
    # Return statistics for debugging
    if args.debug:
        logging_service.debug("=== FINAL DEBUG SUMMARY ===")
        logging_service.debug(f"Total files processed: {len(files)}")
        logging_service.debug(f"Files with errors: {files_with_errors}")
        logging_service.debug(f"Files with suggestions: {files_with_suggestions}")
        logging_service.debug(f"Files renamed: {rename_count}")
        logging_service.debug("=== END DEBUG MODE ===")


def verify_configuration(config_data: ConfigurationData) -> List[str]:
    """
    Verify configuration and word lists are loaded correctly.
    
    Returns:
        List of validation error messages
    """
    validation_errors = []
    
    if not config_data.known_words:
        validation_errors.append("No known words loaded! This will cause many false positives.")
    if not config_data.capitalization_whitelist:
        validation_errors.append("No capitalization whitelist loaded! This will cause many errors.")
    if len(config_data.compound_terms) < 10:
        validation_errors.append("Very few compound terms loaded! Many hyphenated words will be flagged.")
    
    return validation_errors


def check_word_in_lists(word: str, config_data: ConfigurationData) -> tuple[bool, str]:
    """
    Check if a word exists in any of the configured word lists.
    
    Args:
        word: Word to check
        config_data: Configuration data with word lists
        
    Returns:
        Tuple of (found, location) where location describes which list contained the word
    """
    from unicodedata import normalize
    
    word_normalized = normalize("NFC", word)
    
    # First check exact match against case-sensitive lists
    case_sensitive_lists = (
        config_data.capitalization_whitelist | 
        config_data.name_dash_whitelist | 
        config_data.exceptions
    )
    if word_normalized in case_sensitive_lists:
        return True, "case-sensitive lists (exact match)"
    
    # Check with dash variations for name_dash_whitelist
    if "-" in word or "–" in word:
        # Try with both hyphen and en-dash
        word_hyphen = word.replace("–", "-")
        word_endash = word.replace("-", "–")
        for variant in [word_hyphen, word_endash]:
            variant_normalized = normalize("NFC", variant)
            if variant_normalized in config_data.name_dash_whitelist:
                return True, f"name_dash_whitelist (dash variant: {variant})"
    
    # Check compound terms
    if word_normalized in config_data.compound_terms:
        return True, "compound_terms"
    
    # Check canonicalized match against known_words (case-insensitive)
    word_canon = canonicalize(word_normalized)
    known_words_canon = {canonicalize(normalize("NFC", w)) for w in config_data.known_words}
    if word_canon in known_words_canon:
        return True, "known_words (canonicalized)"
    
    return False, "NOT FOUND"