#!/usr/bin/env python3
"""
Secrets Health Check
--------------------

Quick diagnostics for environment- and file-based credentials.

Usage:
  python tools/security/secrets_health.py
"""

from __future__ import annotations

import os
from pathlib import Path

from mathpdf.secure_credential_manager import get_credential_manager


def main() -> int:
    cm = get_credential_manager()
    status = cm.list_available_credentials()

    print("Secrets Health Summary")
    print("======================")
    print(f"ENVIRONMENT: {os.getenv('ENVIRONMENT', 'development')}")
    for k, v in status.items():
        print(f"- {k}: {v}")

    # Warn if encrypted files exist with world-readable perms
    creds_dir = Path.home() / ".academic_papers" / "credentials"
    if creds_dir.exists():
        for f in creds_dir.glob("*.enc"):
            try:
                mode = f.stat().st_mode
                if mode & 0o077:
                    print(f"WARNING: {f} permissions are too open (mode={oct(mode)})")
            except Exception:
                pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
