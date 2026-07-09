#!/usr/bin/env python3
"""
ph-auth.py — Publishing House API key manager.
Opens the PH portal so you can generate a key, then saves it locally.

Usage:
  python ph-auth.py              # Open portal + prompt to paste key
  python ph-auth.py --paste      # Just prompt to paste key (skip browser)
  python ph-auth.py --show       # Show current key info (masked)
  python ph-auth.py --reset      # Open portal for a new key, replace saved one
"""

import argparse
import json
import os
import sys
import webbrowser
from pathlib import Path

CENTRAL_URL = os.environ.get(
    "PH_CENTRAL_URL",
    "https://ph-central.apps.cluster-v27ps.dynamic2.redhatworkshops.io",
)
KEYS_PAGE = f"{CENTRAL_URL}/auth/keys"
CRED_FILE = Path.home() / ".config" / "publishing-house" / "auth.json"


def _load() -> dict | None:
    if CRED_FILE.exists():
        try:
            return json.loads(CRED_FILE.read_text())
        except Exception:
            return None
    return None


def _save(raw_key: str) -> None:
    CRED_FILE.parent.mkdir(parents=True, exist_ok=True)
    CRED_FILE.write_text(json.dumps({"credential": raw_key, "portal": CENTRAL_URL}, indent=2))
    CRED_FILE.chmod(0o600)


def _prompt_paste() -> str:
    print()
    print(f"  Portal: {KEYS_PAGE}")
    print("  1. Click 'Generate New Key' (or 'Refresh' on an existing key)")
    print("  2. Copy the full key from the modal")
    print()
    key = input("  Paste your key here: ").strip()
    if not key:
        print("ERROR: No key entered.", file=sys.stderr)
        sys.exit(1)
    return key


def main() -> None:
    parser = argparse.ArgumentParser(description="Publishing House API key manager")
    parser.add_argument("--paste", action="store_true", help="Skip browser, just prompt for key")
    parser.add_argument("--show", action="store_true", help="Show current key info")
    parser.add_argument("--reset", action="store_true", help="Replace saved key with a new one")
    args = parser.parse_args()

    if args.show:
        creds = _load()
        if not creds:
            print("Not authenticated. Run: python ph-auth.py", file=sys.stderr)
            sys.exit(1)
        key = creds.get("credential", "")
        masked = f"{key[:8]}...{key[-8:]}" if len(key) > 16 else "***"
        print(f"Key:    {masked}")
        print(f"Portal: {creds.get('portal', CENTRAL_URL)}")
        print(f"File:   {CRED_FILE}")
        return

    existing = _load()
    if existing and not args.reset and not args.paste:
        print(f"✅ Already have a saved key ({CRED_FILE})")
        print("   Use --reset to replace it, --show to display info.")
        return

    if not args.paste:
        print(f"🔑 Opening Publishing House portal...")
        webbrowser.open(KEYS_PAGE)

    raw_key = _prompt_paste()
    _save(raw_key)
    print()
    print(f"✅ Key saved to {CRED_FILE}")
    print("   You can now use Claude Code in this project.")


if __name__ == "__main__":
    main()
