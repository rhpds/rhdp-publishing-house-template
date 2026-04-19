# Content

This folder holds the Showroom content repo cloned during project setup (AsciiDoc modules, lab guides, supplemental UI).

The repo is gitignored — this project repo tracks your specs, manifest, and progress, not the content itself. The Showroom repo has its own git history and remote.

The orchestrator clones the repo listed in `publishing-house/manifest.yaml` under `integrations.showroom_repo`.
