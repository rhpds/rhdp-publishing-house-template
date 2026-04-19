# Automation

This folder holds the automation repo cloned during project setup (Ansible collection, Helm charts, or GitOps repo).

The repo is gitignored — this project repo tracks your specs, manifest, and progress, not the automation code. The automation repo has its own git history and remote.

The orchestrator clones the repo listed in `publishing-house/manifest.yaml` under `integrations.automation_repo`.
