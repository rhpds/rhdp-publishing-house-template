#!/usr/bin/env python3
"""
ph-register.py — Register this project with Publishing House Central.
Idempotent: safe to run multiple times (409 = already registered, that's fine).

Reads PH_API_KEY from environment or ~/.config/publishing-house/auth.json.
Reads repo URL from git remote origin.
"""

import sys
import os
import json
import ssl
import subprocess
import urllib.request
from pathlib import Path

CENTRAL_URL = os.environ.get(
    "PH_CENTRAL_URL",
    "https://ph-api.apps.cluster-v27ps.dynamic2.redhatworkshops.io"
)

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


def get_api_key():
    key = os.environ.get("PH_API_KEY")
    if key:
        return key
    auth_file = Path.home() / ".config" / "publishing-house" / "auth.json"
    if auth_file.exists():
        try:
            data = json.loads(auth_file.read_text())
            return data.get("api_key") or data.get("token")
        except Exception:
            pass
    return None


def get_repo_url():
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            url = result.stdout.strip()
            if url.startswith("git@github.com:"):
                url = "https://github.com/" + url[len("git@github.com:"):]
            return url.rstrip(".git")
    except Exception:
        pass
    return None


def get_branch():
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip() or "main"
    except Exception:
        pass
    return "main"


def main():
    api_key = get_api_key()
    if not api_key:
        print("ERROR: No PH API key found.", file=sys.stderr)
        print("Ask your admin for a personal key and add it to ~/.bashrc:", file=sys.stderr)
        print("  echo 'export PH_API_KEY=<your-key>' >> ~/.bashrc && source ~/.bashrc", file=sys.stderr)
        sys.exit(2)

    repo_url = get_repo_url()
    if not repo_url:
        print("ERROR: Could not determine git remote URL.", file=sys.stderr)
        sys.exit(2)

    branch = get_branch()
    payload = json.dumps({"repo_url": repo_url, "branch": branch}).encode()
    req = urllib.request.Request(
        f"{CENTRAL_URL}/api/v1/projects",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=10, context=_SSL_CTX) as r:
            data = json.loads(r.read().decode())
            print(f"✅ Registered with Central — id: {data.get('id', 'unknown')}")
    except urllib.error.HTTPError as e:
        if e.code == 409:
            print("✅ Already registered with Central")
        elif e.code == 401:
            print("ERROR: API key rejected — ask admin for a valid key", file=sys.stderr)
            sys.exit(1)
        else:
            print(f"WARN: Central registration failed ({e.code}) — continuing anyway", file=sys.stderr)
    except Exception as e:
        print(f"WARN: Could not reach Central ({e}) — continuing anyway", file=sys.stderr)


if __name__ == "__main__":
    main()
