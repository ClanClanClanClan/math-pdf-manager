import sys
import shutil
import unicodedata
import regex as re
from ruamel.yaml import YAML
from pathlib import Path
from datetime import datetime

def backup_file(file_path):
    file_path = Path(file_path)
    if not file_path.exists():
        print(f"Warning: File not found, skipping backup: {file_path}")
        return False
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    backup_path = file_path.with_suffix(file_path.suffix + f".{timestamp}.bak")
    shutil.copy2(file_path, backup_path)
    print(f"Backup created: {backup_path}")
    return True

def is_nfc(s):
    return s == unicodedata.normalize("NFC", s)

def canonicalize_line(line):
    """Normalize for deduplication: NFC, strip BOM/invisibles, keep accents."""
    orig = line
    line = line.replace('\ufeff', '')
    line = re.sub(r'[\u200b-\u200f\u202a-\u202e\u2060-\u206f]', '', line)
    line = unicodedata.normalize('NFC', line)
    line = line.strip()
    if not is_nfc(orig):
        print(f"[warn] Fixed to NFC: '{orig}' -> '{line}'")
    return line

def deduplicate_and_sort_lines(lines):
    seen = set()
    deduped = []
    for line in lines:
        l_clean = canonicalize_line(line)
        dedup_key = l_clean.casefold()
        if l_clean and dedup_key not in seen:
            seen.add(dedup_key)
            deduped.append(l_clean)
    deduped_sorted = sorted(deduped, key=lambda s: s.casefold())
    return deduped_sorted

def sort_txt_file(file_path):
    file_path = Path(file_path)
    if not file_path.exists():
        print(f"File not found, skipping: {file_path}")
        return
    with file_path.open('r', encoding='utf-8-sig') as f:
        lines = [line.rstrip('\n\r') for line in f if line.strip()]
    if not lines:
        print(f"File empty, skipping: {file_path}")
        return

    backup_file(file_path)

    lines_sorted = deduplicate_and_sort_lines(lines)
    with file_path.open('w', encoding='utf-8') as f:
        for line in lines_sorted:
            f.write(line + '\n')
    print(f"Sorted, deduplicated, NFC-normalized file: {file_path}")

def canonicalize_yaml_item(item):
    """Normalize YAML string item for deduplication: NFC, keep accents."""
    if not isinstance(item, str):
        return item
    orig = item
    item = item.replace('\ufeff', '')
    item = re.sub(r'[\u200b-\u200f\u202a-\u202e\u2060-\u206f]', '', item)
    item = unicodedata.normalize('NFC', item)
    item = item.strip()
    if not is_nfc(orig):
        print(f"[warn] Fixed YAML item to NFC: '{orig}' -> '{item}'")
    return item

def deduplicate_and_sort_yaml_list(lst):
    seen = set()
    deduped = []
    for item in lst:
        key = canonicalize_yaml_item(item)
        if isinstance(key, str):
            compare_key = key.casefold()
        else:
            compare_key = str(key).casefold()
        if compare_key not in seen:
            seen.add(compare_key)
            deduped.append(key)
    deduped_sorted = sorted(deduped, key=lambda x: str(x).casefold())
    return deduped_sorted

def sort_lists_in_yaml(yaml_path):
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml_path = Path(yaml_path)
    if not yaml_path.exists():
        print(f"YAML config not found, skipping: {yaml_path}")
        return

    backup_file(yaml_path)

    with yaml_path.open('r', encoding='utf-8-sig') as f:
        data = yaml.safe_load(f)

    changed = False

    def sort_and_replace(key_path):
        nonlocal data, changed
        try:
            obj = data
            for k in key_path[:-1]:
                obj = obj.get(k, None)
                if obj is None:
                    return
            lst_key = key_path[-1]
            lst = obj.get(lst_key, None)
            if lst and isinstance(lst, list):
                new_lst = deduplicate_and_sort_yaml_list(lst)
                if new_lst != lst:
                    obj[lst_key] = new_lst
                    changed = True
        except Exception as e:
            print(f"Warning: Could not sort list {'.'.join(key_path)} due to: {e}")

    list_paths_to_sort = [
        ['exceptions', 'capitalization_whitelist'],
        ['exceptions', 'lowercase_whitelist'],
        ['compound_terms'],
    ]

    for path in list_paths_to_sort:
        sort_and_replace(path)

    if changed:
        with yaml_path.open('w', encoding='utf-8') as f:
            yaml.dump(data, f)
        print(f"Sorted, deduplicated, NFC-normalized lists and updated YAML: {yaml_path}")
    else:
        print(f"No changes needed in YAML: {yaml_path}")

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Sort, clean, and deduplicate known words, dash whitelist, and YAML lists with backup.')
    parser.add_argument('--known-words', required=True, help='Path to known_words.txt')
    parser.add_argument('--name-dash-whitelist', required=True, help='Path to name_dash_whitelist.txt')
    parser.add_argument('--config', required=True, help='Path to config.yaml')
    args = parser.parse_args()

    # Sort and clean/deduplicate the text files
    sort_txt_file(args.known_words)
    sort_txt_file(args.name_dash_whitelist)

    # Sort and clean/deduplicate the YAML lists
    sort_lists_in_yaml(args.config)