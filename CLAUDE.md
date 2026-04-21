# Publishing House Project

## State
Project state tracked in [publishing-house/manifest.yaml](publishing-house/manifest.yaml).
Read it first every session.

## Repos
- `content/` — Showroom content repo (git submodule, remote in `integrations.showroom_repo`)
- `automation/` — Automation repo (git submodule, remote in `integrations.automation_repo`)

Each is a separate git repo. Use `git submodule update --init` to clone them after checkout.

## Spec
Design spec in [publishing-house/spec/design.md](publishing-house/spec/design.md).
Module outlines in [publishing-house/spec/modules/](publishing-house/spec/modules/).

## Worklog
Session notes and open items in [publishing-house/worklog.yaml](publishing-house/worklog.yaml).
Managed by the `/rhdp-publishing-house:worklog` skill.

## Invoke
Run `/rhdp-publishing-house` to start or continue work.
