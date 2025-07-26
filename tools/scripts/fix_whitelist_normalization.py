#!/usr/bin/env python3
"""Fix Unicode normalization in name_dash_whitelist.txt"""

import unicodedata
import shutil
from datetime import datetime

# Backup the original file
backup_name = f"name_dash_whitelist.txt.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
shutil.copy('name_dash_whitelist.txt', backup_name)
print(f"Created backup: {backup_name}")

# Read and normalize all lines
with open('name_dash_whitelist.txt', "r", encoding="utf-8") as f:
    lines = f.readlines()

normalized_lines = []
changes = 0

for i, line in enumerate(lines):
    original = line.rstrip('\n')
    if original and not original.startswith('#'):
        normalized = unicodedata.normalize('NFC', original)
        if original != normalized:
            changes += 1
            print(f"Line {i+1}: '{original}' → '{normalized}'")
        normalized_lines.append(normalized + '\n')
    else:
        normalized_lines.append(line)

# Write back the normalized content
with open('name_dash_whitelist.txt', "w", encoding="utf-8") as f:
    f.writelines(normalized_lines)

print(f"\nFixed {changes} lines with Unicode normalization issues.")
print("name_dash_whitelist.txt has been updated with NFC normalization.")