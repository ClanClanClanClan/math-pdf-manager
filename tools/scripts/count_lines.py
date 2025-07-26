#!/usr/bin/env python3

import os

files_to_check = [
    'pdf_parser.py',
    'filename_checker.py', 
    'metadata_fetcher.py',
    'auth_manager.py',
    'my_spellchecker.py',
    'scanner.py',
    'reporter.py',
    'duplicate_detector.py'
]

print("=== MAIN FILE LINE COUNTS ===")
for filename in files_to_check:
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            line_count = len(f.readlines())
        print(f"{filename}: {line_count} lines")
    else:
        print(f"{filename}: FILE NOT FOUND")

print("\n=== NEW MODULE VERIFICATION ===")
new_modules = [
    'parsers/base_parser.py',
    'parsers/text_extractor.py',
    'api/arxiv_client.py',
    'api/xml_parser.py',
    'enhanced_pdf_parser.py'
]

for module in new_modules:
    if os.path.exists(module):
        with open(module, 'r') as f:
            line_count = len(f.readlines())
        print(f"{module}: {line_count} lines - EXISTS")
    else:
        print(f"{module}: FILE NOT FOUND")