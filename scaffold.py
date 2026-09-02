#!/usr/bin/env python3
"""Set up this project for a specific lab pattern.

Requires Python 3.8+.  No external dependencies — stdlib only.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

SCAFFOLD_DIR = Path(".scaffolds")
COMMON_DIR = SCAFFOLD_DIR / "common"
MANIFEST = Path("publishing-house/spec.yaml")

PATTERN_DIRS = [
    Path("runtime-automation"),
    Path("setup-automation"),
    Path("config"),
]

MIGRATION_SUFFIX = "-migration"

# Files that document the scaffold source dir itself (not shippable project content) —
# excluded when a `<pattern>-migration/` dir is overlaid onto the project root.
MIGRATION_OVERLAY_IGNORE = shutil.ignore_patterns("README.md")

AUTOMATION_DIR = Path("automation")
AUTOMATION_SCAFFOLD_DIR = SCAFFOLD_DIR / "automation"

AUTOMATION_TYPES = ["ansible", "gitops", "both"]
TOPOLOGIES = ["shared-cluster", "per-student", "cnv-pool"]

PATTERNS: dict[str, tuple[str, str]] = {
    #  pattern-name   : (showroom_type, infrastructure)
    "agd-open":   ("classic", "agd_v2"),
    "agd-guided": ("guided",  "agd_v2"),
    "zt-guided":  ("guided",  "zt"),
}

MENU = """\
Which lab pattern?

  1. AgD v2 Open      — AgnosticD v2 infra, classic Showroom (no solve/validate)
  2. AgD v2 Guided    — AgnosticD v2 infra, guided Showroom (solve/validate buttons)
  3. ZT Guided        — Project Zero infra, guided Showroom (solve/validate buttons)
"""

MENU_MAP = {"1": "agd-open", "2": "agd-guided", "3": "zt-guided"}


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the scaffold CLI."""
    parser = argparse.ArgumentParser(
        description="Set up this project for a specific lab pattern.",
    )
    parser.add_argument(
        "--pattern",
        choices=list(PATTERNS),
        help="Lab pattern to scaffold (skips interactive menu)",
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Skip confirmation prompt on re-scaffold",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without touching the filesystem",
    )
    parser.add_argument(
        "--automation",
        choices=AUTOMATION_TYPES,
        default=None,
        help="Automation type to scaffold from `.scaffolds/automation/` into `automation/` "
             "(omit to skip automation scaffolding)",
    )
    parser.add_argument(
        "--topology",
        choices=TOPOLOGIES,
        default=None,
        help="Cluster topology — only affects gitops/both automation, where "
             "`shared-cluster` also copies bootstrap-tenant/",
    )
    parser.add_argument(
        "--migration",
        action="store_true",
        help="Migration mode — the project already has real content imported from a source "
             "repo (content/, runtime-automation/, setup-automation/, config/, ui-config.yml). "
             "Never overwrite existing files. runtime-automation/, setup-automation/, and "
             "config/ are fully hands-off — never scanned for fill-in at all, since a migrated "
             "repo structures them completely differently (shell scripts in real module "
             "folders, not ansible-playbook-per-module placeholders). Other pattern files "
             "(e.g. site.yml, ui-config.yml) still get filled in from `common/` and the "
             "pattern dir if genuinely missing, then `.scaffolds/<pattern>-migration/` (if "
             "present) is overlaid on top — e.g. this is what swaps in the "
             "legacy-script-aware qa-automation/ for `zt-guided-migration`.",
    )
    return parser


def interactive_menu() -> str:
    """Present the interactive pattern selection menu."""
    print(MENU)
    while True:
        choice = input("Enter choice [1-3]: ").strip()
        if choice in MENU_MAP:
            return MENU_MAP[choice]
        print(f"Invalid choice: {choice!r}. Enter 1, 2, or 3.")


def update_manifest(path: Path, showroom_type: str, infrastructure: str) -> None:
    """Update showroom_type and infrastructure in the manifest YAML.

    Uses regex replacement to preserve comments and formatting.
    """
    text = path.read_text(encoding="utf-8")
    text = re.sub(
        r'^(\s*showroom_type:\s*)""',
        rf'\g<1>"{showroom_type}"',
        text,
        count=1,
        flags=re.MULTILINE,
    )
    text = re.sub(
        r'^(\s*infrastructure:\s*)""',
        rf'\g<1>"{infrastructure}"',
        text,
        count=1,
        flags=re.MULTILINE,
    )
    path.write_text(text, encoding="utf-8")


def automation_copy_pairs(
    automation: str, topology: str | None
) -> list[tuple[Path, Path]]:
    """Resolve which `.scaffolds/automation/` subdirectories to copy for an automation type.

    Returns (source, dest) pairs — both relative to `.scaffolds/automation/` and `automation/`
    respectively; the layouts mirror each other (`gitops/bootstrap-infra/`,
    `gitops/bootstrap-tenant/`, `ansible/`).

    `bootstrap-tenant/` is only included when topology is `shared-cluster`. Topology is usually
    unknown at initial scaffold time — it's decided later during intake — so it's opt-in via
    `--topology` rather than inferred.
    """
    pairs: list[tuple[Path, Path]] = []
    if automation in ("ansible", "both"):
        pairs.append((Path("ansible"), Path("ansible")))
    if automation in ("gitops", "both"):
        pairs.append((Path("gitops/bootstrap-infra"), Path("gitops/bootstrap-infra")))
        if topology == "shared-cluster":
            pairs.append((Path("gitops/bootstrap-tenant"), Path("gitops/bootstrap-tenant")))
    return pairs


def plan_copy_no_overwrite(
    src: Path, dst: Path, exclude_dirs: set[str] | None = None
) -> tuple[list[Path], list[Path]]:
    """Preview a no-overwrite copy of `src` into `dst`.

    Returns `(to_copy, skipped_existing)` — file paths relative to `src`/`dst`. Files that
    already exist at the destination are never touched; only genuinely missing files would
    be copied.

    `exclude_dirs`, if given, is a set of top-level relative directory names (e.g.
    `{"runtime-automation"}`) that are skipped entirely — not copied, not reported as
    skipped, not touched at all. Used for dirs a migrated repo manages with its own,
    completely different convention (e.g. shell scripts instead of ansible playbooks),
    where "genuinely missing by filename" doesn't mean the scaffold stub is wanted.
    """
    to_copy: list[Path] = []
    skipped: list[Path] = []
    for item in sorted(src.rglob("*")):
        if item.is_dir():
            continue
        rel = item.relative_to(src)
        if exclude_dirs and rel.parts[0] in exclude_dirs:
            continue
        (skipped if (dst / rel).exists() else to_copy).append(rel)
    return to_copy, skipped


def copy_tree_no_overwrite(
    src: Path, dst: Path, exclude_dirs: set[str] | None = None
) -> list[Path]:
    """Copy files from `src` into `dst`, skipping any file that already exists at `dst`.

    Used in `--migration` mode so real, already-imported content (content/, runtime-automation/,
    setup-automation/, config/, ui-config.yml, etc.) is never clobbered by placeholder stubs —
    only genuinely missing files get filled in. Returns the list of paths actually copied
    (relative to `src`/`dst`).

    `exclude_dirs` is forwarded to `plan_copy_no_overwrite()` — see its docstring. Pass the
    `PATTERN_DIRS` names in `--migration` mode so those dirs are never touched at all, not just
    protected from overwrite.
    """
    to_copy, _skipped = plan_copy_no_overwrite(src, dst, exclude_dirs)
    for rel in to_copy:
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src / rel, target)
    return to_copy


def scaffold(
    root: Path,
    pattern: str,
    *,
    force: bool,
    dry_run: bool,
    automation: str | None = None,
    topology: str | None = None,
    migration: bool = False,
) -> int:
    """Run the scaffolding process.  Returns 0 on success, 1 on error."""
    scaffold_dir = root / SCAFFOLD_DIR
    common_src = root / COMMON_DIR
    pattern_src = scaffold_dir / pattern
    migration_src = scaffold_dir / f"{pattern}{MIGRATION_SUFFIX}"
    manifest = root / MANIFEST

    # --- Pre-flight checks ---
    if not scaffold_dir.is_dir():
        print(
            "Error: This project has already been scaffolded. "
            f"The `{SCAFFOLD_DIR}/` directory was removed after initial scaffolding.",
            file=sys.stderr,
        )
        return 1

    if not (root / "publishing-house").is_dir():
        print(
            "Error: scaffold.py must be run from the template root — "
            f"expected to find `{SCAFFOLD_DIR}/` and `publishing-house/` in the current directory.",
            file=sys.stderr,
        )
        return 1

    if not pattern_src.is_dir():
        print(
            f"Error: Pattern {pattern!r} not found in `{SCAFFOLD_DIR}/`.",
            file=sys.stderr,
        )
        return 1

    showroom_type, infrastructure = PATTERNS[pattern]

    if topology and automation not in ("gitops", "both"):
        print(
            f"Warning: --topology {topology!r} has no effect without "
            "--automation gitops or --automation both (ignoring).",
            file=sys.stderr,
        )

    has_migration_overlay = migration_src.is_dir()
    if migration and not has_migration_overlay:
        print(
            f"Note: --migration was passed but no `{migration_src}/` overlay exists for "
            f"pattern {pattern!r} — no pattern-specific overlay will be applied. Existing "
            "files are still preserved (no-overwrite fill-in only).",
            file=sys.stderr,
        )

    automation_src = root / AUTOMATION_SCAFFOLD_DIR
    automation_pairs: list[tuple[Path, Path]] = []
    if automation:
        automation_pairs = automation_copy_pairs(automation, topology)
        missing = [src for src, _dest in automation_pairs if not (automation_src / src).is_dir()]
        if missing:
            names = ", ".join(str(automation_src / m) for m in missing)
            print(f"Error: Automation source(s) not found: {names}.", file=sys.stderr)
            return 1

    # --- Check for existing pattern/automation dirs ---
    # Automation dirs are checked per top-level type (automation/ansible/, automation/gitops/)
    # rather than the whole automation/ tree, so re-running for one type doesn't clobber a
    # different type that's already in place.
    #
    # In migration mode, PATTERN_DIRS are never wiped (they hold real imported content), so
    # they're excluded from this check entirely — only automation dirs are still subject to it.
    automation_top_dirs = sorted(
        {AUTOMATION_DIR / dest.parts[0] for _src, dest in automation_pairs}
    )
    pattern_dirs_to_wipe: list[Path] = [] if migration else list(PATTERN_DIRS)
    dirs_to_check = pattern_dirs_to_wipe + automation_top_dirs

    # In migration mode, PATTERN_DIRS (runtime-automation/, setup-automation/, config/) are
    # author/migration-owned and structured completely differently from the fresh scaffold's
    # stubs (shell scripts in real module folders vs. ansible-playbook-per-module placeholders).
    # They're excluded from the no-overwrite fill-in entirely — not just protected from
    # overwrite by filename, since "genuinely missing by filename" doesn't mean a placeholder
    # stub is wanted there.
    migration_exclude_dirs = {d.name for d in PATTERN_DIRS} if migration else None
    existing = [d for d in dirs_to_check if (root / d).is_dir()]
    if existing and not force:
        if dry_run:
            print(f"Would remove existing directories: {', '.join(str(d) for d in existing)}")
        else:
            names = ", ".join(str(d) for d in existing)
            print(f"Existing pattern directories found: {names}")
            confirm = input("Re-scaffolding will clear and recreate them. Continue? [y/N] ").strip()
            if confirm.lower() not in ("y", "yes"):
                print("Aborted.")
                return 1

    # --- Dry-run summary ---
    if dry_run:
        print(f"\n--- Dry run: pattern={pattern}{' (migration)' if migration else ''} ---")
        if migration:
            print(
                "  Migration mode: existing files (content/, runtime-automation/, "
                "setup-automation/, config/, ui-config.yml, etc.) are preserved — only "
                "missing files are filled in from common/ and the pattern dir."
            )
            print(
                f"  {', '.join(sorted(migration_exclude_dirs))} are fully hands-off — never "
                "scanned for fill-in at all, not just protected from overwrite."
            )
        for label, src in (("common", common_src), (f"pattern ({pattern})", pattern_src)):
            if not src.is_dir():
                continue
            if migration:
                to_copy, skipped = plan_copy_no_overwrite(src, root, migration_exclude_dirs)
                print(f"  Fill in from {src}/ ({len(skipped)} already-existing files skipped):")
                for f in to_copy:
                    print(f"    → {f}")
            else:
                files = sorted(p.relative_to(src) for p in src.rglob("*") if p.is_file())
                print(f"  Copy from {src}/:")
                for f in files:
                    print(f"    → {f}")
        if migration:
            if has_migration_overlay:
                overlay_files = sorted(
                    p.relative_to(migration_src)
                    for p in migration_src.rglob("*")
                    if p.is_file() and p.name != "README.md"
                )
                print(f"  Overlay (always overwrite) from {migration_src}/:")
                for f in overlay_files:
                    print(f"    → {f}")
            else:
                print(f"  No migration overlay at {migration_src}/ — skipping.")
        if automation_pairs:
            print(f"  Copy from {automation_src}/:")
            for src, dest in automation_pairs:
                print(f"    {src} → {AUTOMATION_DIR / dest}")
        if manifest.is_file():
            print(
                f"  Update {manifest}: "
                f"showroom_type={showroom_type!r}, infrastructure={infrastructure!r}"
            )
        else:
            print(f"  Skip {manifest} update (file not present yet)")
        print(f"  Remove {scaffold_dir}/")
        print("No changes made.")
        return 0

    # --- Execute ---
    overlay_copied: list[Path] = []
    try:
        # 1. Remove any existing pattern-specific / automation directories (skipped for
        #    PATTERN_DIRS in migration mode — see dirs_to_check above)
        for d in dirs_to_check:
            target = root / d
            if target.is_dir():
                shutil.rmtree(target)

        # 2. Copy common files (shared by every pattern) into project root
        # 3. Copy pattern-specific files into project root
        # In migration mode, never overwrite files that already exist (real imported content),
        # and never fill in PATTERN_DIRS at all — see migration_exclude_dirs above.
        if migration:
            if common_src.is_dir():
                copy_tree_no_overwrite(common_src, root, migration_exclude_dirs)
            copy_tree_no_overwrite(pattern_src, root, migration_exclude_dirs)
        else:
            if common_src.is_dir():
                shutil.copytree(common_src, root, dirs_exist_ok=True)
            shutil.copytree(pattern_src, root, dirs_exist_ok=True)

        # 3b. Migration overlay — always overwrites. This is what swaps in the
        #     migration-aware qa-automation/ (driving the legacy runtime-automation shell
        #     scripts a migrated repo already ships) in place of whatever the no-overwrite
        #     common/pattern copy just filled in above.
        if migration and has_migration_overlay:
            shutil.copytree(
                migration_src, root, dirs_exist_ok=True, ignore=MIGRATION_OVERLAY_IGNORE
            )
            overlay_copied = sorted(
                p.relative_to(migration_src)
                for p in migration_src.rglob("*")
                if p.is_file() and p.name != "README.md"
            )

        # 4. Copy automation files into automation/ (before .scaffolds/ is removed —
        #    this must happen in the same run since automation_type is known up front
        #    but topology usually isn't yet)
        for src, dest in automation_pairs:
            shutil.copytree(automation_src / src, root / AUTOMATION_DIR / dest, dirs_exist_ok=True)

        # 5. Update manifest (spec.yaml is populated by skeleton substitution;
        #    skip if it doesn't exist yet — fields will be set at instantiation)
        if manifest.is_file():
            update_manifest(manifest, showroom_type, infrastructure)

        # 6. Remove .scaffolds/
        shutil.rmtree(scaffold_dir)

    except OSError as exc:
        print(f"Error during scaffolding: {exc}", file=sys.stderr)
        print(
            "The project may be in a partial state. "
            "Re-run with --force to attempt recovery.",
            file=sys.stderr,
        )
        return 1

    # --- Summary ---
    print(f"\nScaffolded: {pattern}{' (migration)' if migration else ''}")
    print(f"  showroom_type:  {showroom_type}")
    print(f"  infrastructure: {infrastructure}")

    existing_pattern_dirs = [d for d in PATTERN_DIRS if (root / d).is_dir()]
    if existing_pattern_dirs:
        label = "preserved:      " if migration else "created:        "
        print(f"  {label}{', '.join(str(d) for d in existing_pattern_dirs)}")
    if migration and overlay_copied:
        print(f"  overlay:        {', '.join(str(f) for f in overlay_copied)}")
    if automation_pairs:
        automation_created = sorted(str(AUTOMATION_DIR / dest) for _src, dest in automation_pairs)
        print(f"  automation:     {', '.join(automation_created)}")
    print("\nNext: run /rhdp-publishing-house to start intake, or edit files directly.")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point.  Parse args, resolve pattern, and run scaffold."""
    args = build_parser().parse_args(argv)

    root = Path.cwd()

    if args.pattern:
        pattern = args.pattern
    else:
        try:
            pattern = interactive_menu()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            return 1

    return scaffold(
        root,
        pattern,
        force=args.force,
        dry_run=args.dry_run,
        automation=args.automation,
        topology=args.topology,
        migration=args.migration,
    )


if __name__ == "__main__":
    raise SystemExit(main())
