# AI Agent Troubleshooting on OpenShift

## Problem Statement

Platform engineers spend significant time manually correlating logs, events, and resource metrics when OpenShift applications fail. Traditional CLI-based troubleshooting requires expertise across multiple tools and is slow when the root cause is non-obvious. AI-powered troubleshooting agents built with LangGraph and Red Hat OpenShift AI can interpret cluster state holistically and surface root causes faster, but most platform engineers lack a practical on-ramp to building and using these agents with Red Hat tooling.

## Target Audience

- **Role:** Platform engineers
- **Experience level:** Intermediate
- **What they already know:** OpenShift day-2 operations, oc CLI, pod and event debugging, basic understanding of what LLMs do
- **What they don't know:** Building LangGraph agents, connecting AI model endpoints to operator tooling, agent-driven troubleshooting workflows
- **Prerequisites:** Familiarity with OpenShift (oc CLI, namespaces, pods, events); no prior agent development experience required

## Learning Objectives

1. Configure a LangGraph troubleshooting agent connected to Red Hat OpenShift AI
2. Diagnose CrashLoopBackOff and pod failure root causes using the AI agent
3. Identify resource exhaustion patterns across namespaces through agent-driven cluster investigation
4. Trace networking misconfigurations using agent tool calls against live OpenShift APIs

## Content Type

Lab (hands-on)

## Products & Technologies

- Red Hat OpenShift 4.21
- Red Hat OpenShift AI (RHOAI)
- LangGraph (upstream)

## Module Map

| Module | Title | Duration |
|--------|-------|----------|
| 1 | Build Your First OpenShift Troubleshooting Agent | ~25 min |
| 2 | Diagnosing Pod Failures and CrashLoopBackOff | ~30 min |
| 3 | Resource Exhaustion and Networking Investigation | ~35 min |
| — | **Total hands-on** | **~90 min** |
| — | Intro / presentation | ~10 min |
| — | **Total lab** | **~100 min** |

**Module relationship:** Sequential — modules build on each other. Module 1 provisions and configures the agent; Modules 2 and 3 require the agent to be running and connected.

## Difficulty Level

Intermediate

## Environment

**Learner view:** Students arrive to an OCP 4.21 shared cluster with Red Hat OpenShift AI already installed and a model serving endpoint active. A sample application is pre-deployed in their namespace with intentional faults seeded per scenario — CrashLoopBackOff, resource exhaustion, and networking misconfiguration. Participants configure and use the LangGraph agent against this broken environment; no cluster installs required.

**Automation needed:** Yes — RHOAI Operator and model serving endpoint provisioned at cluster startup; broken sample application deployed per student namespace with fault scenarios injected (pod failure, resource pressure, network misconfiguration).

## Infrastructure Requirements

- **Base infrastructure:** ocp4-cluster
- **Sizing:** 3 control plane nodes (4 CPU, 16GB RAM), 4 worker nodes (8 CPU, 32GB RAM, 100GB disk), 1 GPU worker node (A10G or equivalent, 16 vCPU, 64GB RAM) for RHOAI model serving — TBD, exact sizing pending multi-user load estimation
- **Cloud provider:** CNV
- **Automation approach:** Ansible
- **Existing workloads to reuse:** RHOAI Operator AgnosticD workload (ocp4_workload_rhods or current equivalent)
- **New workloads needed:** Broken sample application with seeded fault scenarios (CrashLoopBackOff, resource pressure, network misconfiguration) — to be developed by lab owner
