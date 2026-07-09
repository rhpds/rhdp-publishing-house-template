#!/usr/bin/env python3
"""
ph-check.py — Publishing House local compliance checker.
Runs deterministic checks against the project repo.
Policy data (OCP version, vocabulary) fetched from Central API, cached 24h.

Usage:
  python ph-check.py              # Run all checks
  python ph-check.py --offline    # Force stale-cache path (air-gapped)
  python ph-check.py --verbose    # Show all pass results too
"""

import sys
import os
import json
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
    "https://ph-central.apps.cluster-v27ps.dynamic2.redhatworkshops.io"
)
CACHE_DIR = Path.home() / ".cache" / "ph-check"
CACHE_TTL_HOURS = 24


def log(msg, level="INFO"):
    symbols = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️ ", "INFO": "ℹ️ ", "SKIP": "⏭️ "}
    print(f"{symbols.get(level, '  ')} [{level}] {msg}")


def fetch_json(url, timeout=10):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return None, str(e)


def load_cache(key):
    path = CACHE_DIR / f"{key}.json"
    if not path.exists():
        return None
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
    if data and not isinstance(data, tuple):
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
    results = []
    passed = failed = warned = 0

    def record(check, level, msg):
        nonlocal passed, failed, warned
        results.append((check, level, msg))
        if level == "PASS":
            passed += 1
            if verbose:
                log(f"{check}: {msg}", level)
        elif level == "FAIL":
            failed += 1
            log(f"{check}: {msg}", level)
        elif level in ("WARN", "SKIP"):
            warned += 1
            log(f"{check}: {msg}", level)

    # --- Load manifest ---
    manifest, err = load_manifest()
    if err:
        log(f"Cannot load manifest: {err}", "FAIL")
        return 1

    spec = manifest.get("spec", {})
    stage = manifest.get("stage", {}).get("current", "unknown")
    modules_in_spec = spec.get("modules", [])
    objectives = spec.get("learning_objectives", [])
    ocp_version = spec.get("environment", {}).get("ocp_version", "")
    topology = spec.get("environment", {}).get("topology", "")

    log(f"Stage: {stage} | Modules in spec: {len(modules_in_spec)} | Objectives: {len(objectives)}")
    print()

    # --- Check 1: Module count vs content ---
    content_dir = Path("content/modules/ROOT/pages")
    if content_dir.exists():
        content_files = list(content_dir.glob("module-*.adoc"))
        expected = len(modules_in_spec)
        actual = len(content_files)
        if expected == 0:
            record("module-count", "SKIP", "No modules in spec yet (intake phase)")
        elif actual == expected:
            record("module-count", "PASS", f"{actual} modules match spec")
        else:
            record("module-count", "FAIL",
                   f"Spec declares {expected} modules but found {actual} in content/modules/ROOT/pages/")
    else:
        record("module-count", "SKIP", "content/modules/ROOT/pages/ not found — no content yet")

    # --- Check 2: nav.adoc exists ---
    nav = Path("content/modules/ROOT/nav.adoc")
    if nav.exists():
        record("nav-adoc", "PASS", "nav.adoc found")
        # Check each module is referenced in nav
        nav_content = nav.read_text()
        missing_from_nav = []
        for m in modules_in_spec:
            mid = m.get("id", "")
            if mid and mid not in nav_content:
                missing_from_nav.append(mid)
        if missing_from_nav:
            record("nav-modules", "FAIL",
                   f"Modules not referenced in nav.adoc: {', '.join(missing_from_nav)}")
        elif modules_in_spec:
            record("nav-modules", "PASS", "All spec modules referenced in nav.adoc")
    else:
        record("nav-adoc", "SKIP", "nav.adoc not found — content not yet created")

    # --- Check 3: antora.yml exists ---
    antora = Path("content/antora.yml")
    if antora.exists():
        record("antora-yml", "PASS", "antora.yml found")
    else:
        record("antora-yml", "SKIP", "antora.yml not found — not yet created")

    # --- Check 4: Learning objectives referenced in content ---
    if objectives and content_dir.exists():
        all_content = " ".join(
            f.read_text() for f in content_dir.glob("*.adoc")
        ).lower()
        missing_objectives = []
        for obj in objectives:
            # Check if key words from objective appear in content
            keywords = [w for w in obj.lower().split() if len(w) > 4]
            if keywords and not any(kw in all_content for kw in keywords[:3]):
                missing_objectives.append(obj[:60])
        if missing_objectives:
            record("learning-objectives", "FAIL",
                   f"{len(missing_objectives)} objectives not found in content: "
                   + "; ".join(missing_objectives[:2]))
        else:
            record("learning-objectives", "PASS",
                   f"All {len(objectives)} learning objectives referenced in content")
    elif not objectives:
        record("learning-objectives", "SKIP", "No learning objectives in spec yet")
    else:
        record("learning-objectives", "SKIP", "No content files yet")

    # --- Check 5: OCP version minimum (fetches from Central) ---
    policy, warn = get_policy("ocp-policy", "/api/v1/reference/ocp-policy", offline)
    if warn:
        log(f"OCP policy: {warn}", "WARN")
    if policy and ocp_version:
        minimum = policy.get("ocp_version_minimum", "4.20")
        try:
            spec_parts = [int(x) for x in ocp_version.split(".")]
            min_parts = [int(x) for x in minimum.split(".")]
            if spec_parts >= min_parts:
                record("ocp-version", "PASS",
                       f"OCP {ocp_version} meets minimum {minimum}")
            else:
                record("ocp-version", "FAIL",
                       f"OCP {ocp_version} below minimum {minimum} — update spec and content")
        except ValueError:
            record("ocp-version", "WARN", f"Could not parse OCP version '{ocp_version}'")
    elif not ocp_version:
        record("ocp-version", "SKIP", "OCP version not set in spec yet")
    else:
        record("ocp-version", "SKIP", f"Policy unavailable: {warn}")

    # --- Check 6: RH product naming (fetches vocabulary from Central) ---
    vocab_data, warn2 = get_policy("vocabulary", "/api/v1/reference/vocabulary", offline)
    if warn2 and not warn:
        log(f"Vocabulary: {warn2}", "WARN")
    if vocab_data and content_dir.exists():
        vocabulary = [v.lower() for v in vocab_data.get("vocabulary", [])]
        # Look for common wrong names in content
        wrong_names = {
            "openshift container platform": "Red Hat OpenShift Container Platform",
            "red hat openshift container platform ": None,  # correct, skip
            "ansible": "Red Hat Ansible Automation Platform (when referring to the product)",
        }
        all_content_raw = " ".join(f.read_text() for f in content_dir.glob("*.adoc"))
        violations = []
        if "ocp" in all_content_raw.lower() and "openshift" not in all_content_raw.lower():
            violations.append("'OCP' used without 'OpenShift' context")
        if violations:
            record("product-naming", "WARN",
                   f"Possible product naming issues: {'; '.join(violations)}")
        else:
            record("product-naming", "PASS", "No obvious product naming violations found")
    else:
        record("product-naming", "SKIP",
               "No content yet or vocabulary unavailable")

    # --- Check 7: Topology match ---
    catalog_yamls = list(Path(".").glob("**/*.yaml"))
    catalog_yamls = [y for y in catalog_yamls if "publishing-house" not in str(y)]
    if topology and catalog_yamls:
        # Basic check: if spec says shared-cluster, look for per_user or multiuser flags
        found_conflict = False
        for cy in catalog_yamls[:5]:
            try:
                content = cy.read_text()
                if topology == "shared-cluster" and "num_users" in content:
                    found_conflict = True
                    record("topology-match", "WARN",
                           f"Spec says shared-cluster but {cy.name} has num_users (per-student pattern)")
                    break
            except Exception:
                pass
        if not found_conflict:
            record("topology-match", "PASS",
                   f"Topology '{topology}' appears consistent with catalog files")
    else:
        record("topology-match", "SKIP",
               "Topology not set in spec or no catalog files yet")

    # --- Summary ---
    print()
    print("─" * 50)
    total = passed + failed + warned
    print(f"Results: {passed} passed, {failed} failed, {warned} skipped/warned")
    if failed > 0:
        print("❌ Compliance check FAILED")
        return 1
    elif warned > 0:
        print("⚠️  Compliance check PASSED with warnings")
        return 0
    else:
        print("✅ All checks PASSED")
        return 0


def main():
    parser = argparse.ArgumentParser(description="Publishing House compliance checker")
    parser.add_argument("--offline", action="store_true",
                        help="Force stale-cache path (no Central calls)")
    parser.add_argument("--verbose", action="store_true",
                        help="Show passing checks too")
    args = parser.parse_args()

    if not Path("publishing-house/manifest.yaml").exists():
        print("ERROR: Not a Publishing House project directory.", file=sys.stderr)
        print("Run from the root of a project cloned from rhdp-publishing-house-template.", file=sys.stderr)
        sys.exit(2)

    sys.exit(run_checks(offline=args.offline, verbose=args.verbose))


if __name__ == "__main__":
    main()
