#!/usr/bin/env python3
"""
ph-intake.py — Submit intake spec to Publishing House Central.
Reads design.md + module outlines + manifest, sends to Central,
which creates the Jira Epic with ph_payload + tasks per module.

Usage:
  python tools/ph-intake.py              # Submit intake
  python tools/ph-intake.py --dry-run   # Print payload without sending
"""
import sys
import os
import json
import ssl
import argparse
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

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
            return data.get("credential") or data.get("api_key") or data.get("token")
        except Exception:
            pass
    return None


def get_project_id():
    """Get Central project ID from ph-register output or by querying Central."""
    api_key = get_api_key()
    if not api_key:
        return None
    try:
        repo_url = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5
        ).stdout.strip()
        if repo_url.startswith("git@github.com:"):
            repo_url = "https://github.com/" + repo_url[len("git@github.com:"):]
        if repo_url.endswith(".git"):
            repo_url = repo_url[:-4]
    except Exception:
        return None

    req = urllib.request.Request(
        f"{CENTRAL_URL}/api/v1/projects",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10, context=_SSL_CTX) as r:
            projects = json.loads(r.read().decode())
            for p in projects:
                if p.get("repo_url", "").rstrip("/") == repo_url.rstrip("/"):
                    return p["id"]
    except Exception:
        pass
    return None


def load_manifest():
    path = Path("publishing-house/manifest.yaml")
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def load_design():
    path = Path("publishing-house/spec/design.md")
    return path.read_text() if path.exists() else ""


def load_module_outlines():
    modules_dir = Path("publishing-house/spec/modules")
    if not modules_dir.exists():
        return []
    outlines = []
    for f in sorted(modules_dir.glob("module-*.md")):
        outlines.append({"file": f.name, "content": f.read_text()})
    return outlines


def build_payload(manifest, design_md, module_outlines):
    proj = manifest.get("project", {})
    spec = manifest.get("spec", {})
    env = spec.get("environment", {})

    # Parse modules from manifest spec if available, else from outline file names
    modules = []
    for i, outline in enumerate(module_outlines, start=1):
        name = outline["file"].replace(".md", "").replace(f"module-{i:02d}-", "").replace("-", " ").title()
        spec_module = spec.get("modules", [{}])[i - 1] if i <= len(spec.get("modules", [])) else {}
        modules.append({
            "id": f"module-{i:02d}",
            "title": spec_module.get("title") or name,
            "duration_min": spec_module.get("duration_min", 20),
            "description": spec_module.get("description", ""),
        })

    return {
        "name": proj.get("name") or proj.get("slug") or "",
        "slug": proj.get("slug") or "",
        "content_type": proj.get("content_type") or "lab",
        "deployment_mode": proj.get("deployment_mode") or "self_published",
        "owner_email": proj.get("owner_email") or "",
        "reviewer_email": proj.get("reviewer_email") or "",
        "problem_statement": spec.get("problem_statement") or design_md[:500] if design_md else "",
        "audience_role": spec.get("audience") or "",
        "audience_experience": "intermediate",
        "learning_objectives": spec.get("learning_objectives") or [],
        "products": [],
        "modules": modules,
        "ocp_version": env.get("ocp_version") or spec.get("environment", {}).get("ocp_version", ""),
        "topology": env.get("topology") or spec.get("environment", {}).get("topology", "shared-cluster"),
        "duration_hours": spec.get("duration_hours") or 0,
        "environment": env.get("description") or "",
    }


def main():
    parser = argparse.ArgumentParser(description="Submit Publishing House intake to Central")
    parser.add_argument("--dry-run", action="store_true", help="Print payload without sending")
    args = parser.parse_args()

    if not Path("publishing-house/manifest.yaml").exists():
        print("ERROR: Not a Publishing House project directory.", file=sys.stderr)
        sys.exit(2)

    api_key = get_api_key()
    if not api_key:
        print("ERROR: No PH API key. Run: python ph-auth.py --paste", file=sys.stderr)
        sys.exit(2)

    project_id = get_project_id()
    if not project_id:
        print("ERROR: Project not registered with Central. Run: python tools/ph-register.py", file=sys.stderr)
        sys.exit(2)

    manifest = load_manifest()
    design_md = load_design()
    module_outlines = load_module_outlines()
    payload = build_payload(manifest, design_md, module_outlines)

    if args.dry_run:
        print(json.dumps(payload, indent=2))
        return

    req = urllib.request.Request(
        f"{CENTRAL_URL}/api/v1/projects/{project_id}/intake",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15, context=_SSL_CTX) as r:
            data = json.loads(r.read().decode())
            epic_key = data.get("epic_key", "")
            jira_url = data.get("jira_url", "")
            print(f"✅ Jira Epic created: {epic_key}")
            print(f"   {jira_url}")
            print(f"   Tasks created for {len(payload['modules'])} modules + automation + health check + e2e")
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        print(f"ERROR: Central returned {e.code}: {body}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"WARN: Could not reach Central ({e}) — continuing anyway", file=sys.stderr)


if __name__ == "__main__":
    main()
