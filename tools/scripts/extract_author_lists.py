import os
import regex as re
from pathlib import Path

def is_canonical_author_block(author_block):
    # At least one comma, no digits, likely initials present
    if not author_block or ',' not in author_block or re.search(r'\d', author_block):
        return False
    # Heuristic: at least one "Lastname, I." present
    return bool(re.search(r'[A-Za-z][a-z\']+, [A-Z](\.|[A-Z]\.)+', author_block))

def scan_library_for_author_lists(base_folder, multiword_out="multiword_familynames.txt", author_out="known_authors.txt"):
    multiword_fams = set()
    known_authors = set()
    count_files = 0
    for dirpath, _, files in os.walk(base_folder):
        for file in files:
            if not file.lower().endswith((".pdf", ".tex")):
                continue
            base = os.path.splitext(os.path.basename(file))[0]
            if ' - ' not in base:
                continue
            author_block = base.split(' - ', 1)[0]
            if not is_canonical_author_block(author_block):
                continue
            authors = [a.strip() for a in author_block.split(',') if a.strip()]
            # Join all initial parts into canonical form, e.g. "Abi Jaber, E." or "Nguyen Van, P.T."
            for i in range(0, len(authors)-1, 2):
                fam = authors[i]
                initial = authors[i+1] if (i+1)<len(authors) else ''
                full = (fam + (', ' + initial if initial else '')).strip()
                if full:
                    known_authors.add(full)
                    # If fam has multiple words, not hyphenated, it's a multiword family name
                    fam_words = fam.split()
                    if len(fam_words) > 1 and '-' not in fam:
                        multiword_fams.add(fam)
    print(f"Scanned {count_files} files, found {len(multiword_fams)} multi-word family names, {len(known_authors)} authors.")
    with open(multiword_out, "w", encoding="utf-8") as f:
        for name in sorted(multiword_fams):
            f.write(name + "\n")
    with open(author_out, "w", encoding="utf-8") as f:
        for author in sorted(known_authors):
            f.write(author + "\n")
    print(f"Wrote: {multiword_out}, {author_out}")

if __name__ == "__main__":
    import sys
    folder = sys.argv[1] if len(sys.argv) > 1 else "."
    scan_library_for_author_lists(folder)