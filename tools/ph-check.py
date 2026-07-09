#!/usr/bin/env python3
"""
ph-check.py — Publishing House local compliance checker.
Runs deterministic checks against the project repo.
Policy data (OCP version, vocabulary) fetched from Central API, cached 24h.

Usage:
  python tools/ph-check.py              # Run all checks
  python tools/ph-check.py --offline    # Force stale-cache path (air-gapped)
  python tools/ph-check.py --verbose    # Show all pass results too
"""

import sys
import os
import json
import ssl
import argparse
import datetime
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
CACHE_DIR = Path.home() / ".cache" / "ph-check"
CACHE_TTL_HOURS = 24

# SSL context — OCP cluster certs may not be in macOS trust store
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


def log(msg, level="INFO"):
    symbols = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️ ", "INFO": "ℹ️ ", "SKIP": "⏭️ "}
    print(f"{symbols.get(level, '  ')} [{level}] {msg}")


def fetch_json(url, timeout=10):
    try:
        with urllib.request.urlopen(url, timeout=timeout, context=_SSL_CTX) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def load_cache(key):
    path = CACHE_DIR / f"{key}.json"
    if not path.exists():
        return None, 999
    try:
        data = json.loads(path.read_text())
        cached_at = datetime.datetime.fromisoformat(data["cached_at"])
        age_hours = (datetime.datetime.now() - cached_at).total_seconds() / 3600
        return data["payload"], age_hours
    except Exception:
        return None, 999


def save_cache(key, payload):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{key}.json"
    path.write_text(json.dumps({
        "cached_at": datetime.datetime.now().isoformat(),
        "payload": payload
    }))


def get_policy(key, endpoint, offline=False):
    cached, age = load_cache(key)
    if cached and age < CACHE_TTL_HOURS:
        return cached, None
    if offline:
        if cached:
            return cached, f"offline mode — using {age:.0f}h old cache"
        return None, f"offline mode and no cache for {key}"
    data = fetch_json(f"{CENTRAL_URL}{endpoint}")
    if data:
        save_cache(key, data)
        return data, None
    elif cached:
        warn = f"Central unreachable, using {age:.0f}h old cache"
        if age > 48:
            return None, f"cache too stale ({age:.0f}h) — reconnect to Central"
        return cached, warn if age > CACHE_TTL_HOURS else None
    return None, "Central unreachable and no local cache"


def load_manifest():
    path = Path("publishing-house/manifest.yaml")
    if not path.exists():
        return None, "publishing-house/manifest.yaml not found"
    try:
        return yaml.safe_load(path.read_text()), None
    except Exception as e:
        return None, f"manifest.yaml parse error: {e}"


def run_checks(offline=False, verbose=False):
    passed = failed = warned = skipped = 0

    def record(check, level, msg):
        nonlocal passed, failed, warned, skipped
        if level == "PASS":
            passed += 1
            if verbose:
                log(f"{check}: {msg}", level)
        elif level == "FAIL":
            failed += 1
            log(f"{check}: {msg}", level)
        elif level == "WARN":
            warned += 1
            log(f"{check}: {msg}", level)
        elif level == "SKIP":
            skipped += 1
            if verbose:
                log(f"{check}: {msg}", level)

    manifest, err = load_manifest()
    if err:
        log(f"Cannot load manifest: {err}", "FAIL")
        return 1

    spec = manifest.get("spec", {})
    stage = manifest.get("stage", {}).get("current", "unknown")
    modules_in_spec = spec.get("modules", [])
    objectives = spec.get("learning_objectives", [])
    ocp_version = spec.get("environment", {}).get("ocp_version", "")

    log(f"Stage: {stage} | Modules: {len(modules_in_spec)} | Objectives: {len(objectives)}")
    print()

    content_dir = Path("content/modules/ROOT/pages")
    if content_dir.exists():
        content_files = list(content_dir.glob("module-*.adoc"))
        expected = len(modules_in_spec)
        actual = len(content_files)
        if expected == 0:
            record("module-count", "SKIP", "No modules in spec yet")
        elif actual == expected:
            record("module-count", "PASS", f"{actual} modules match spec")
        else:
            record("module-count", "FAIL",
                   f"Spec declares {expected} modules but found {actual} in content/modules/ROOT/pages/")
    else:
        record("module-count", "SKIP", "No content directory yet")

    nav = Path("content/modules/ROOT/nav.adoc")
    if nav.exists():
        record("nav-adoc", "PASS", "nav.adoc found")
        nav_content = nav.read_text()
        missing = [m.get("id", "") for m in modules_in_spec
                   if m.get("id") and m["id"] not in nav_content]
        if missing:
            record("nav-modules", "FAIL", f"Modules not in nav.adoc: {', '.join(missing)}")
        elif modules_in_spec:
            record("nav-modules", "PASS", "All modules in nav.adoc")
    else:
        record("nav-adoc", "SKIP", "nav.adoc not yet created")

    if Path("content/antora.yml").exists():
        record("antora-yml", "PASS", "antora.yml found")
    else:
        record("antora-yml", "SKIP", "antora.yml not yet created")

    policy, warn = get_policy("ocp-policy", "/api/v1/reference/ocp-policy", offline)
    if warn:
        log(f"OCP policy: {warn}", "WARN")
        warned += 1
    if policy and ocp_version:
        minimum = policy.get("ocp_version_minimum", "4.20")
        try:
            if [int(x) for x in ocp_version.split(".")] >= [int(x) for x in minimum.split(".")]:
                record("ocp-version", "PASS", f"OCP {ocp_version} meets minimum {minimum}")
            else:
                record("ocp-version", "FAIL", f"OCP {ocp_version} below minimum {minimum}")
        except ValueError:
            record("ocp-version", "WARN", f"Cannot parse OCP version '{ocp_version}'")
    elif not ocp_version:
        record("ocp-version", "SKIP", "OCP version not set in spec yet")

    if objectives and content_dir.exists():
        all_content = " ".join(f.read_text() for f in content_dir.glob("*.adoc")).lower()
        missing_obj = [obj[:50] for obj in objectives
                       if not any(w in all_content for w in obj.lower().split() if len(w) > 4)]
        if missing_obj:
            record("learning-objectives", "FAIL",
                   f"{len(missing_obj)} objectives not found in content")
        else:
            record("learning-objectives", "PASS",
                   f"All {len(objectives)} objectives referenced in content")
    elif not objectives:
        record("learning-objectives", "SKIP", "No objectives in spec yet")
    else:
        record("learning-objectives", "SKIP", "No content yet")

    print()
    print("─" * 50)
    print(f"Results: {passed} passed, {failed} failed, {warned} warned, {skipped} skipped")
    if failed > 0:
        print("❌ Compliance check FAILED")
        return 1
    elif warned > 0:
        print("⚠️  Compliance check passed with warnings")
        return 0
    elif skipped > 0:
        print(f"✅ Checks passed ({skipped} skipped — fill in spec to enable all checks)")
        return 0
    else:
        print("✅ All checks PASSED")
        return 0


def main():
    parser = argparse.ArgumentParser(description="Publishing House compliance checker")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if not Path("publishing-house/manifest.yaml").exists():
        print("ERROR: Run from a Publishing House project directory.", file=sys.stderr)
        sys.exit(2)

    sys.exit(run_checks(offline=args.offline, verbose=args.verbose))


if __name__ == "__main__":
    main()
