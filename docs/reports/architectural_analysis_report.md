# Architectural Analysis Report
==================================================

## Summary
- **Files analyzed**: 135
- **Violations found**: 1753
- **Health score**: 0.0/100

## Top Violations
- **FORBIDDEN_PATTERN**: 1497 occurrences
- **DEPENDENCY_VIOLATION**: 110 occurrences
- **MULTIPLE_RESPONSIBILITIES**: 103 occurrences
- **FILE_TOO_LARGE**: 27 occurrences
- **TOO_MANY_FUNCTIONS**: 16 occurrences

## Largest Files
- **filename_checker.py**: 4779 lines, 10 responsibilities
- **filename_checker.py**: 2952 lines, 10 responsibilities
- **pdf_parser.py**: 2575 lines, 0 responsibilities
- **auth_manager.py**: 2306 lines, 10 responsibilities
- **pdf_parser.py**: 2269 lines, 0 responsibilities
- **main.py**: 2065 lines, 10 responsibilities
- **main.py**: 1795 lines, 0 responsibilities
- **utils.py**: 1235 lines, 10 responsibilities
- **hell_level_comprehensive.py**: 1086 lines, 9 responsibilities
- **downloader.py**: 995 lines, 10 responsibilities

## Improvement Suggestions
- Split 9 large files (>1000 lines) into smaller modules
- Extract responsibilities from 103 files with multiple concerns
- Auto-fix 1497 violations using automated refactoring