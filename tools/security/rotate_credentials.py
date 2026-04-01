#!/usr/bin/env python3
"""
Credential Rotation Utility
---------------------------

Re-encrypt file-based credentials with a fresh key and optionally migrate to
OS keyring for production.

Usage:
  python tools/security/rotate_credentials.py --to keyring
  python tools/security/rotate_credentials.py --reencrypt
"""

from __future__ import annotations

import argparse
from pathlib import Path

from mathpdf.secure_credential_manager import SecureCredentialManager


def rotate_to_keyring(cm: SecureCredentialManager) -> None:
    for name in ["eth_username", "eth_password"]:
        value = cm.get_credential(name)
        if value:
            cm.store_credential(name, value, method="keyring")
            print(f"Migrated {name} to keyring")
        else:
            print(f"No value for {name}; skipping")


def reencrypt_files(cm: SecureCredentialManager) -> None:
    # Naive approach: read, then write back via 'file' method (uses current key)
    for name in ["eth_username", "eth_password"]:
        value = cm.get_credential(name)
        if value:
            cm.store_credential(name, value, method="file")
            print(f"Re-encrypted {name} file credential")
        else:
            print(f"No value for {name}; skipping")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--to", choices=["keyring"], help="Migrate credentials to backend")
    parser.add_argument(
        "--reencrypt", action="store_true", help="Re-encrypt file credentials with current key"
    )
    args = parser.parse_args()

    cm = SecureCredentialManager()

    if args.to == "keyring":
        rotate_to_keyring(cm)
    if args.reencrypt:
        reencrypt_files(cm)

    if not args.to and not args.reencrypt:
        parser.print_help()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
