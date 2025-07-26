import os
import sys
import yaml
import csv
from pathlib import Path
from collections import defaultdict
from typing import Dict, Set, List
import shutil

# Optionally import jinja2 for HTML reporting
try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def write_yaml(data, path):
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

def resolve_base(base):
    return os.path.abspath(os.path.expanduser(base))

def walk_tree(base_dir):
    """Return a set of all subfolder paths relative to base_dir (dirs only, not files)."""
    all_folders = set()
    for root, dirs, files in os.walk(base_dir):
        for d in dirs:
            folder_path = os.path.join(root, d)
            rel_path = os.path.relpath(folder_path, base_dir)
            rel_path = rel_path.replace("\\", "/")
            all_folders.add(rel_path)
    return all_folders

def flatten_config_folders(config_folders):
    """Flatten all folder paths listed in config to a set."""
    flat = set()
    if isinstance(config_folders, dict):
        for key, v in config_folders.items():
            if v is None:
                continue
            if isinstance(v, list):
                for entry in v:
                    if isinstance(entry, dict):
                        flat.add(entry.get('path', '').strip())
                    elif entry:
                        flat.add(entry.strip())
            elif isinstance(v, str):
                flat.add(v.strip())
    elif isinstance(config_folders, list):
        for entry in config_folders:
            if isinstance(entry, dict):
                flat.add(entry.get('path', '').strip())
            elif entry:
                flat.add(entry.strip())
    return flat

def get_subfolders(base_dir, rel_path):
    abs_path = os.path.join(base_dir, rel_path)
    if not os.path.exists(abs_path):
        return []
    return [d for d in os.listdir(abs_path) if os.path.isdir(os.path.join(abs_path, d))]

def compare_trees(actual, config_expected, base_dir):
    config_dup = [x for x in config_expected if list(config_expected).count(x) > 1]
    missing_on_disk = sorted([x for x in config_expected if x not in actual])
    missing_in_config = sorted([x for x in actual if x not in config_expected])
    config_lower = set(x.lower() for x in config_expected)
    actual_lower = set(x.lower() for x in actual)
    typo_case_mismatches = [x for x in config_expected if x.lower() not in actual_lower]
    return {
        "duplicates": config_dup,
        "missing_on_disk": missing_on_disk,
        "missing_in_config": missing_in_config,
        "typo_case_mismatches": typo_case_mismatches
    }

def check_subfolder_structure(base_dir, published_paper_folders):
    folder_structures = []
    for pub in published_paper_folders:
        abs_pub = os.path.join(base_dir, pub)
        if not os.path.exists(abs_pub):
            continue
        subfolders = get_subfolders(base_dir, pub)
        letter_folders = [sf for sf in subfolders if len(sf) == 1 and sf.isalpha() and sf.isupper()]
        if letter_folders:
            folder_structures.append((pub, "lettered", sorted(letter_folders)))
        else:
            folder_structures.append((pub, "flat", sorted(subfolders)))
    return folder_structures

def check_not_fully_published(config, base_dir):
    nfpub_config = flatten_config_folders(config['folder_categories'].get('not_fully_published_version', []))
    found_nfp = set()
    for rel in nfpub_config:
        abs_path = os.path.join(base_dir, rel)
        if os.path.exists(abs_path):
            found_nfp.add(rel)
    return nfpub_config, found_nfp

def generate_csv_report(audit_results, folder_structures, nfp_config, found_nfp, out_path="folder_audit_report.csv"):
    with open(out_path, "w", encoding="utf-8", newline='') as f:
        w = csv.writer(f)
        w.writerow(["Type", "Path", "Details"])
        for t, field in audit_results.items():
            if not isinstance(field, list): continue
            for entry in field:
                w.writerow([t, entry, ""])
        for pub, mode, subs in folder_structures:
            w.writerow(["published_subfolders", pub, f"{mode} | {','.join(subs)}"])
        for nfp in nfp_config:
            status = "found" if nfp in found_nfp else "missing"
            w.writerow(["not_fully_published", nfp, status])

def generate_html_report(audit_results, folder_structures, nfp_config, found_nfp, out_path="folder_audit_report.html", template_dir="templates"):
    if not JINJA2_AVAILABLE:
        print("[ERROR] Jinja2 not installed. Skipping HTML report.")
        return
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(['html', 'xml'])
    )
    try:
        template = env.get_template("tree_audit_template.html")
    except Exception:
        template = Environment().from_string(_DEFAULT_TEMPLATE)
    html = template.render(
        audit_results=audit_results,
        folder_structures=folder_structures,
        nfp_config=nfp_config,
        found_nfp=found_nfp
    )
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[INFO] HTML report written to {out_path}")

# HTML fallback template (minimal, you can style further)
_DEFAULT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>Maths Folder Audit</title></head>
<body>
    <h1>Maths Folder Tree Audit</h1>
    <h2>Discrepancies</h2>
    <ul>
    {% for t, entries in audit_results.items() %}
        {% if entries %}
            <li><b>{{ t }}</b>
                <ul>
                {% for entry in entries %}
                    <li>{{ entry }}</li>
                {% endfor %}
                </ul>
            </li>
        {% endif %}
    {% endfor %}
    </ul>
    <h2>Published Folders Subfolder Structure</h2>
    <ul>
    {% for pub, mode, subs in folder_structures %}
        <li><b>{{ pub }}</b> : {{ mode }} | [{{ subs|join(', ') }}]</li>
    {% endfor %}
    </ul>
    <h2>Not Fully Published Version Folders</h2>
    <ul>
    {% for nfp in nfp_config %}
        <li>{{ nfp }} : {{ 'found' if nfp in found_nfp else 'MISSING' }}</li>
    {% endfor %}
    </ul>
</body>
</html>
"""

def prompt_add_missing_folders(missing, config, config_path):
    """Prompt to add missing folders to config."""
    if not missing:
        return False
    print("\n[ADD] The following folders are missing from config.yaml:")
    for m in missing:
        print(f"  - {m}")
    do_update = input("Add these missing folders to config.yaml [y/N]? ").strip().lower() == "y"
    if do_update:
        # Try to guess category (add to extra list at end if unsure)
        folder_categories = config.get('folder_categories', {})
        if not folder_categories.get('extra'):
            folder_categories['extra'] = []
        for m in missing:
            folder_categories['extra'].append(m)
        config['folder_categories'] = folder_categories
        write_yaml(config, config_path)
        print("[UPDATE] Config.yaml updated.")
        return True
    return False

def prompt_add_missing_on_disk(missing, base_dir):
    if not missing:
        return
    print("\n[WARN] These folders are listed in config.yaml but missing on disk:")
    for m in missing:
        print(f"  - {m}  (should exist at {os.path.join(base_dir, m)})")
    # Optional: prompt to create them?
    # Uncomment below to create empty dirs
    # do_create = input("Create missing folders on disk? [y/N]: ").strip().lower() == "y"
    # if do_create:
    #     for m in missing:
    #         os.makedirs(os.path.join(base_dir, m), exist_ok=True)
    #     print("[UPDATE] Folders created on disk.")

def audit_and_fix_config(config_path="config.yaml", auto_update=False, csv_out="folder_audit_report.csv", html_out="folder_audit_report.html", template_dir="templates"):
    config = load_yaml(config_path)
    base_dir = resolve_base(config.get('base_maths_folder'))
    print(f"[INFO] Scanning base maths folder: {base_dir}")

    # Build actual tree (dirs only, relative to base)
    actual_tree = walk_tree(base_dir)
    expected_tree = set()
    for cat in config.get('folder_categories', {}):
        expected_tree.update(flatten_config_folders(config['folder_categories'][cat]))

    # Compare
    audit_results = compare_trees(actual_tree, expected_tree, base_dir)

    # Subfolder (author-initial) structure check
    published_paper_folders = flatten_config_folders(config['folder_categories'].get('published_papers', []))
    folder_structures = check_subfolder_structure(base_dir, published_paper_folders)

    # Not fully published version
    nfp_config, found_nfp = check_not_fully_published(config, base_dir)

    # Save reports
    generate_csv_report(audit_results, folder_structures, nfp_config, found_nfp, out_path=csv_out)
    if JINJA2_AVAILABLE:
        generate_html_report(audit_results, folder_structures, nfp_config, found_nfp, out_path=html_out, template_dir=template_dir)
    else:
        print("[WARN] Jinja2 not available, HTML report skipped.")

    # Optionally update config
    missing_in_config = audit_results.get("missing_in_config", [])
    missing_on_disk = audit_results.get("missing_on_disk", [])

    if auto_update and missing_in_config:
        print("[AUTO-UPDATE] Adding missing folders to config.yaml under 'extra'.")
        folder_categories = config.get('folder_categories', {})
        if not folder_categories.get('extra'):
            folder_categories['extra'] = []
        for m in missing_in_config:
            if m not in folder_categories['extra']:
                folder_categories['extra'].append(m)
        config['folder_categories'] = folder_categories
        write_yaml(config, config_path)
        print("[AUTO-UPDATE] Config.yaml updated.")
    elif not auto_update and missing_in_config:
        prompt_add_missing_folders(missing_in_config, config, config_path)

    if not auto_update and missing_on_disk:
        prompt_add_missing_on_disk(missing_on_disk, base_dir)

    print("\n[INFO] Audit complete.")
    print(f"CSV report: {csv_out}")
    if JINJA2_AVAILABLE:
        print(f"HTML report: {html_out}")

# --- For integration in your pipeline ---

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Audit and optionally repair Maths folder tree vs config.yaml")
    parser.add_argument('--config', type=str, default='config.yaml')
    parser.add_argument('--auto-update', action="store_true", help="Automatically add missing folders to config.yaml")
    parser.add_argument('--csv', type=str, default='folder_audit_report.csv')
    parser.add_argument('--html', type=str, default='folder_audit_report.html')
    parser.add_argument('--template_dir', type=str, default='templates')
    args = parser.parse_args()

    audit_and_fix_config(
        config_path=args.config,
        auto_update=args.auto_update,
        csv_out=args.csv,
        html_out=args.html,
        template_dir=args.template_dir
    )