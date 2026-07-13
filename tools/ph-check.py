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
    "https://central-api-backstage.apps.cluster-v27ps.dynamic2.redhatworkshops.io"
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
    # spec.yaml is the new name (renamed from manifest.yaml)
    for candidate in ["publishing-house/spec.yaml", "publishing-house/manifest.yaml"]:
        path = Path(candidate)
        if path.exists():
            try:
                return yaml.safe_load(path.read_text()), None
            except Exception as e:
                return None, f"{candidate} parse error: {e}"
    return None, "publishing-house/spec.yaml not found"


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
        elif actual == 0:
            # Content not started yet — expected at intake stage
            record("module-count", "SKIP", f"Spec declares {expected} modules — content not written yet")
        elif actual == expected:
            record("module-count", "PASS", f"{actual} modules match spec")
        else:
            # Some content written but incomplete — warn, not fail
            record("module-count", "WARN",
                   f"Spec declares {expected} modules, {actual} written so far")
    else:
        record("module-count", "SKIP", "No content directory yet")

    nav = Path("content/modules/ROOT/nav.adoc")
    if nav.exists():
        record("nav-adoc", "PASS", "nav.adoc found")
        nav_content = nav.read_text()
        missing = [m.get("id", "") for m in modules_in_spec
                   if m.get("id") and m["id"] not in nav_content]
        if missing:
            # nav.adoc may be auto-generated — warn rather than fail
            record("nav-modules", "WARN", f"Modules not yet in nav.adoc: {', '.join(missing)}")
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
        adoc_files = list(content_dir.glob("*.adoc"))
        if not adoc_files:
            # Content not written yet — skip rather than fail
            record("learning-objectives", "SKIP", "No content written yet")
        else:
            all_content = " ".join(f.read_text() for f in adoc_files).lower()
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

    # ── Nate's Part 1 checks (RHDPCD-170) ────────────────────────────────────

    # Check 8: Vocabulary — content_type
    content_type = manifest.get("project", {}).get("content_type", "")
    valid_content_types = {"lab", "demo", "workshop", "onboarding"}
    if content_type:
        if content_type.lower() in valid_content_types:
            record("content-type", "PASS", f"Content type '{content_type}' is valid")
        else:
            record("content-type", "FAIL",
                   f"Content type '{content_type}' is not valid. Must be one of: {', '.join(sorted(valid_content_types))}")
    else:
        record("content-type", "SKIP", "Content type not set in spec yet")

    # Check 9: Vocabulary — deployment_mode
    deployment_mode = manifest.get("project", {}).get("deployment_mode", "")
    valid_modes = {"self_published", "rhdp_published"}
    if deployment_mode:
        if deployment_mode.lower() in valid_modes:
            record("deployment-mode", "PASS", f"Deployment mode '{deployment_mode}' is valid")
        else:
            record("deployment-mode", "FAIL",
                   f"Deployment mode '{deployment_mode}' is not valid. Must be: rhdp_published or self_published")
    else:
        record("deployment-mode", "SKIP", "Deployment mode not set in spec yet")

    # Check 10: Module spec sections — required headings per module outline
    modules_dir = Path("publishing-house/spec/modules")
    required_sections = ["Brief Overview", "Audience", "Learning Objectives", "Lab Structure", "Key Takeaways"]
    if modules_dir.exists():
        module_files = sorted(modules_dir.glob("module-*.md"))
        if module_files:
            all_ok = True
            for mf in module_files:
                content = mf.read_text()
                missing = [s for s in required_sections if s.lower() not in content.lower()]
                if missing:
                    record("module-sections", "FAIL",
                           f"{mf.name}: missing required sections: {', '.join(missing)}")
                    all_ok = False
            if all_ok:
                record("module-sections", "PASS",
                       f"All {len(module_files)} module outlines have required sections")
        else:
            record("module-sections", "SKIP", "No module outlines written yet")
    else:
        record("module-sections", "SKIP", "No spec/modules directory yet")

    # Check 11: Template placeholders — detect unfilled template text
    import re
    placeholder_pattern = re.compile(r"\[PLACEHOLDER\]|\[TODO\]|PLACEHOLDER_HERE|REPLACE_ME|<.*?>", re.IGNORECASE)
    spec_dir = Path("publishing-house/spec")
    if spec_dir.exists():
        placeholder_files = []
        for spec_file in spec_dir.rglob("*.md"):
            if placeholder_pattern.search(spec_file.read_text()):
                placeholder_files.append(spec_file.name)
        if placeholder_files:
            record("no-placeholders", "FAIL",
                   f"Template placeholders found in: {', '.join(placeholder_files[:3])}")
        else:
            record("no-placeholders", "PASS", "No unfilled template placeholders detected")
    else:
        record("no-placeholders", "SKIP", "No spec files yet")

    # ── Summary ───────────────────────────────────────────────────────────────
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

    if not (Path("publishing-house/spec.yaml").exists() or Path("publishing-house/manifest.yaml").exists()):
        print("ERROR: Run from a Publishing House project directory.", file=sys.stderr)
        sys.exit(2)

    sys.exit(run_checks(offline=args.offline, verbose=args.verbose))


if __name__ == "__main__":
    main()
