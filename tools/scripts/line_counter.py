import os

def count_lines_in_file(filepath):
    """Count lines in a file"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return len(f.readlines())
    except Exception as e:
        return f"ERROR: {e}"

# Main files to check
main_files = [
    'pdf_parser.py',
    'filename_checker.py',
    'metadata_fetcher.py',
    'auth_manager.py',
    'my_spellchecker.py',
    'scanner.py',
    'reporter.py',
    'duplicate_detector.py'
]

# New modules to verify
new_modules = [
    'parsers/base_parser.py',
    'parsers/text_extractor.py',
    'api/arxiv_client.py',
    'api/xml_parser.py',
    'enhanced_pdf_parser.py'
]

print("=== MAIN FILE LINE COUNTS ===")
for filename in main_files:
    if os.path.exists(filename):
        count = count_lines_in_file(filename)
        print(f"{filename}: {count} lines")
    else:
        print(f"{filename}: FILE NOT FOUND")

print("\n=== NEW MODULE VERIFICATION ===")
for module in new_modules:
    if os.path.exists(module):
        count = count_lines_in_file(module)
        print(f"{module}: {count} lines - EXISTS")
    else:
        print(f"{module}: FILE NOT FOUND")

print("\n=== ADDITIONAL CHECKS ===")
# Check some other files for context
other_files = [
    'main.py',
    'config.yaml',
    'constants.py'
]

for filename in other_files:
    if os.path.exists(filename):
        count = count_lines_in_file(filename)
        print(f"{filename}: {count} lines")
    else:
        print(f"{filename}: FILE NOT FOUND")