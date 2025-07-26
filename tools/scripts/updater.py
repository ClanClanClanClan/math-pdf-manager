# updater.py

import os
import shutil
import datetime
from metadata_fetcher import batch_metadata_lookup
from downloader import download_file_with_login
from utils import read_arxiv_id

def move_file(src, dst_folder, dry_run=False):
    """
    Move file to dst_folder, creating folder if needed.
    If dry_run=True, only log the action without performing it.
    """
    dst = os.path.join(dst_folder, os.path.basename(src))
    if dry_run:
        print(f"[DRY RUN] Would move: {src} -> {dst}")
        return dst
    os.makedirs(dst_folder, exist_ok=True)
    shutil.move(src, dst)
    return dst

def should_move_to_unpublished(meta, cutoff_years=5, exceptions=[]):
    """
    Returns True if paper has not had a new version in strictly more than cutoff_years.
    """
    if not meta or not meta.get("published"):
        return True
    try:
        # Parse publication year
        year = None
        if isinstance(meta["published"], list) and meta["published"]:
            # Crossref: [['2019', ...]]
            year = int(meta["published"][0][0])
        elif isinstance(meta["published"], str):
            # arXiv: "2016-05-21T18:19:17Z"
            year = int(meta["published"][:4])
        # Compare years
        now = datetime.datetime.now().year
        if year and now - year > cutoff_years:
            # Check exceptions
            title = meta.get("title", "")
            if any(exc in title for exc in exceptions):
                return False
            return True
    except Exception as e:
        print(f"Year parse failed: {e}")
    return False

def handle_working_papers(files, meta_dict, folders, exceptions, login_creds=None, dry_run=False):
    """
    For working papers: check for newer versions or published versions.
    Move or replace as needed.
    """
    for info in files:
        meta = meta_dict.get(info["path"])
        if not meta:
            continue
        arxiv_id = read_arxiv_id(info["name"])
        if meta.get("DOI"):
            # Published version found
            if meta.get("source") == "crossref":
                # Download published version if available
                url = f"https://doi.org/{meta['DOI']}"
                if dry_run:
                    print(f"[DRY RUN] Would download published version: {url}")
                else:
                    pdf_path = download_file_with_login(url, info["folder"], login_creds)
                # Move original to /Published/
                move_file(info["path"], folders["published"], dry_run=dry_run)
            else:
                # arXiv version: check if newer
                # (Assume arXiv IDs are enough to decide newer/older)
                # For simplicity, just move if arXiv version is newer
                pass
        else:
            # Not found or still preprint
            if should_move_to_unpublished(meta, exceptions=exceptions):
                move_file(info["path"], folders["unpublished"], dry_run=dry_run)

def handle_unpublished_papers(files, meta_dict, folders, login_creds=None, dry_run=False):
    """
    For unpublished papers: aggressively look for published versions and move/flag as needed.
    """
    for info in files:
        meta = meta_dict.get(info["path"])
        if meta and meta.get("DOI"):
            # Published version now found
            url = f"https://doi.org/{meta['DOI']}"
            if dry_run:
                print(f"[DRY RUN] Would download published version: {url}")
            else:
                pdf_path = download_file_with_login(url, info["folder"], login_creds)
            move_file(info["path"], folders["published"], dry_run=dry_run)

def handle_to_download(files, meta_dict, folders, login_creds=None, dry_run=False):
    """
    For 'Papers to be downloaded'—try to download from publisher or open archives.
    """
    for info in files:
        meta = meta_dict.get(info["path"])
        if meta and meta.get("DOI"):
            url = f"https://doi.org/{meta['DOI']}"
            if dry_run:
                print(f"[DRY RUN] Would download paper: {url}")
                continue
            pdf_path = download_file_with_login(url, info["folder"], login_creds)
            if pdf_path:
                move_file(pdf_path, folders["published"], dry_run=dry_run)

def scan_and_update(root_folder, folder_structure, exceptions, login_creds=None, dry_run=False):
    """
    Main function: scan all subfolders, fetch metadata, move/update as needed.
    """
    from scanner import scan_directory

    working = scan_directory(folder_structure["working"])
    unpublished = scan_directory(folder_structure["unpublished"])
    to_download = scan_directory(folder_structure["to_download"])

    # Fetch metadata for all files in parallel
    all_files = working + unpublished + to_download
    meta_dict = batch_metadata_lookup(all_files)

    handle_working_papers(working, meta_dict, folder_structure, exceptions, login_creds, dry_run=dry_run)
    handle_unpublished_papers(unpublished, meta_dict, folder_structure, login_creds, dry_run=dry_run)
    handle_to_download(to_download, meta_dict, folder_structure, login_creds, dry_run=dry_run)

if __name__ == "__main__":
    # Example: call with folder paths and simple login credentials
    import sys
    if len(sys.argv) < 5:
        print("Usage: updater.py <working_dir> <unpublished_dir> <to_download_dir> <published_dir>")
        sys.exit(1)
    folders = {
        "working": sys.argv[1],
        "unpublished": sys.argv[2],
        "to_download": sys.argv[3],
        "published": sys.argv[4],
    }
    exceptions = []  # Could load from config if needed
    scan_and_update(".", folders, exceptions, login_creds=None)