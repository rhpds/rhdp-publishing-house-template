# zt-guided-migration

This directory is **not** in `PATTERNS` and never appears in the interactive menu or
`--pattern` choices — it's not a pattern you scaffold directly. It's an **overlay** that
`scaffold.py` applies on top of the `zt-guided` pattern when `--migration` is passed.

## Why this isn't a normal scaffold pattern

A migrated repo (`project.intake_type: migration`) already has real content imported from
the source repo before `scaffold.py` ever runs — including working
`runtime-automation/<module>/{solve,validation}-<host>.sh` shell scripts and a populated
`ui-config.yml`. Blindly copying the `zt-guided` pattern's placeholder stubs on top of that
would destroy it.

When `--migration` is passed, `scaffold.py`:

1. Never wipes or overwrites `runtime-automation/`, `setup-automation/`, or `config/` —
   and, unlike other pattern files, these three are fully hands-off: they're never even
   scanned for fill-in. A migrated repo structures them completely differently from the
   fresh `zt-guided` scaffold (shell scripts in real `module-NN-<slug>/` folders, not
   `module-01/{setup,solve,validate}.yml` ansible-playbook-per-module placeholders), so
   "missing by filename" doesn't mean the placeholder stub belongs there — copying it in
   would just leave an unused extra file/folder alongside the real automation.
2. Everything else (e.g. `site.yml`, `ui-config.yml`) still only fills in files that are
   genuinely missing from `common/` and `zt-guided/` — real, already-existing files are
   never overwritten.
3. After that fill-in pass, overlays this directory (`zt-guided-migration/`) on top,
   **overwriting** whatever it touches. Today that's just `qa-automation/` — the one thing
   a migrated repo doesn't already have in Publishing House's format, since it needs to
   drive the legacy shell scripts (see below) rather than the ansible-playbook-per-module
   style the fresh `zt-guided` scaffold assumes.

`README.md` (this file) is excluded from the overlay — it documents the scaffold source
itself and must never land in a scaffolded project's root, where it would clobber the
real `README.md`.

## Contents

- `qa-automation/e2e.yml` — builds a bastion inventory from `BASTION_*` env
  vars, reads module order from `ui-config.yml`, then solves + validates
  every module by running `tasks/run_script.yml`.
- `qa-automation/healthcheck.yml` — builds the same inventory and pings the
  bastion over SSH to confirm it's reachable.
- `qa-automation/tasks/run_script.yml` — shared logic: copies a
  `{stage}-{hostname}.sh` script from `runtime-automation/{module}/` onto the
  remote host, sources a `fail_validation()` helper, runs the script, and
  fails the play on a non-zero exit or a captured `fail_validation` block.

## Usage

Invoked automatically as part of the normal `zt-guided` scaffold run:

```bash
python scaffold.py --pattern zt-guided --migration --force
```

This is what `config-helper` (in `rhdp-publishing-house-skills`) runs for a project with
`project.intake_type: migration` and `project.showroom_type: zero_touch`. See
`config-helper.md` Route A for the full flow, including the module-naming alignment step
that runs immediately before this.
