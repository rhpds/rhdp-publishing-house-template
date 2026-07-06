# Publishing House Project

## State
Project state tracked in [publishing-house/manifest.yaml](publishing-house/manifest.yaml).
Read it first every session.

## Content
Showroom AsciiDoc content lives in [content/](content/). The Antora component descriptor
is at `content/antora.yml` and modules are in `content/modules/ROOT/pages/`.

## Automation
Automation code (Ansible roles, Helm charts) lives in [automation/](automation/).

## Zero-Touch Automation
Zero-Touch (ZT) projects use [runtime-automation/](runtime-automation/) for runtime automation and
[setup-automation/](setup-automation/) for setup automation. These directories are removed by the
orchestrator for classic Showroom projects during intake.

## Spec
Design spec in [publishing-house/spec/design.md](publishing-house/spec/design.md).
Module outlines in [publishing-house/spec/modules/](publishing-house/spec/modules/).

## Worklog
Session notes and open items in [publishing-house/worklog.yaml](publishing-house/worklog.yaml).
Managed by the `/rhdp-publishing-house:worklog` skill.

## Invoke
Run `/rhdp-publishing-house` to start or continue work.
