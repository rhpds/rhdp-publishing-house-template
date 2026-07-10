# Module 3: Resource Exhaustion and Networking Investigation

## Brief Overview

This module extends the agent-driven troubleshooting workflow to two additional fault
scenarios that were seeded in the student namespace alongside the CrashLoopBackOff from
Module 2: resource exhaustion across namespaces, and a networking misconfiguration. Each
scenario requires the agent to use different OpenShift API tool calls — resource metrics
and quota inspection for the first, and network policy or service configuration inspection
for the second. Students complete both investigations using the same LangGraph agent
configured in Module 1, reinforcing that a single agent can pivot across different
troubleshooting domains by issuing different tool calls.

## Audience and Time

- **Target personas:** Platform engineers (intermediate)
- **Prerequisites:** Modules 1 and 2 complete; LangGraph agent running and connected;
  student namespace still has all three fault scenarios active
- **Estimated duration:** ~35 min

## Learning Objectives

- Identify resource exhaustion patterns across namespaces by directing the LangGraph agent
  to investigate resource consumption and quota state through agent-driven cluster
  investigation
- Trace a networking misconfiguration root cause by driving the agent to issue tool calls
  against live OpenShift networking APIs and interpret the returned configuration state

## Lab Structure

| Section | Title | Duration |
|---------|-------|----------|
| 1 | Resource Exhaustion Investigation | ~15 min |
| 2 | Networking Misconfiguration Trace | ~15 min |
| 3 | Cross-Scenario Reflection | ~5 min |

## Detailed Steps

### Section 1: Resource Exhaustion Investigation

1. Confirm the resource exhaustion fault is visible in your namespace. Look for pods in a
   `Pending` or `OOMKilled` state, or for resource quota pressure:
   `oc get pods -n <your-namespace>`
   `oc describe resourcequota -n <your-namespace>`
2. Note initial observations from the CLI output: which resource is under pressure (CPU,
   memory, pod count, other)?
3. Submit a resource investigation prompt to the LangGraph agent asking it to identify
   resource exhaustion patterns in your namespace. The exact prompt form is provided in
   the lab guide.
4. Observe the agent's tool call sequence for this scenario — it will query resource
   metrics and quota state across the relevant namespace scope.
5. Watch the agent retrieve and interpret:
   - Current resource consumption and limits per workload
   - ResourceQuota and LimitRange state
   - Any node-level resource pressure signals visible from the API
6. Allow the agent to complete its reasoning and return a summary of the exhaustion pattern.
7. Compare the agent's findings to your initial CLI observation from steps 1-2. Note
   which signals the agent weighted most heavily.
8. Answer the reflection prompt in the lab guide: does the agent's cross-namespace view
   surface anything that per-namespace oc commands would miss?

### Section 2: Networking Misconfiguration Trace

9. Switch focus to the networking fault seeded in your namespace. Observe that a service
   or pod-to-pod communication path is broken — symptoms may include connection timeouts
   or DNS resolution failures visible in application logs.
10. Review the failing service or route configuration using the oc CLI to establish a
    baseline before running the agent:
    `oc get svc -n <your-namespace>`
    `oc get networkpolicy -n <your-namespace>`
11. Submit a networking investigation prompt to the LangGraph agent asking it to trace
    the misconfiguration. The exact prompt form is provided in the lab guide.
12. Observe the agent's tool call sequence for this scenario — it will call OpenShift
    networking APIs to inspect service selectors, NetworkPolicy rules, and route or
    endpoint configuration.
13. Watch the agent retrieve and interpret:
    - Service selector and endpoint binding state
    - NetworkPolicy rules affecting the relevant pods
    - Any route or ingress configuration anomalies
14. Allow the agent to complete its reasoning and identify the specific misconfiguration
    causing the connectivity failure.
15. Compare the agent's diagnosis to what you observed manually in steps 9-10. Note
    whether the root cause was visible from the initial oc get output or required
    deeper correlation.

### Section 3: Cross-Scenario Reflection

16. With all three fault scenarios investigated (CrashLoopBackOff in Module 2, resource
    exhaustion and networking in this module), review the agent's tool call traces across
    all three sessions.
17. Identify the pattern: the same LangGraph agent issued different tool calls for each
    scenario — pod/log/event APIs for CrashLoopBackOff, resource/quota APIs for
    exhaustion, and networking APIs for the connectivity fault.
18. Answer the synthesis question in the lab guide: how does the agent's ability to select
    appropriate tool calls per scenario change the troubleshooting workflow compared to
    manual oc-based investigation?

## Key Takeaways

- Resource exhaustion investigation benefits from the agent's ability to correlate quota
  state, workload resource requests, and node pressure across the cluster in a single pass.
- Networking misconfigurations often require inspecting multiple objects (service selectors,
  NetworkPolicy, endpoints) that the agent can traverse through tool calls without manual
  cross-referencing.
- A single LangGraph agent connected to RHOAI can cover multiple troubleshooting domains
  by selecting different OpenShift API tool calls per scenario — the same pattern applies
  to production troubleshooting beyond these lab scenarios.

## Infrastructure Notes

- All three fault scenarios (CrashLoopBackOff, resource exhaustion, networking
  misconfiguration) are seeded at environment provisioning time per student namespace;
  no manual fault injection is required during the lab.
- Resource exhaustion and networking faults remain active from Module 1 setup; students
  do not need to re-trigger them.
- If a fault scenario is not visible in a student's namespace, escalate to the lab
  facilitator — this indicates an automation issue with fault seeding.
