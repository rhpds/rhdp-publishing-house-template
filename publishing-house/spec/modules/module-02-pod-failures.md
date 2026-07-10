# Module 2: Diagnosing Pod Failures and CrashLoopBackOff

## Brief Overview

With the LangGraph agent running and connected (from Module 1), students turn it against a
broken application that has been pre-deployed in their namespace with a CrashLoopBackOff
fault seeded intentionally. Rather than manually correlating logs and events with the oc CLI,
students drive the AI agent to investigate the failing pod and interpret the root cause it
surfaces. This module reinforces that the agent's value is holistic interpretation of cluster
state — not just log retrieval — and builds the diagnostic vocabulary students need for the
more complex scenarios in Module 3.

## Audience and Time

- **Target personas:** Platform engineers (intermediate)
- **Prerequisites:** Module 1 complete; LangGraph agent running and connected to RHOAI
  model endpoint; familiarity with pod events and logs via oc CLI
- **Estimated duration:** ~30 min

## Learning Objectives

- Diagnose a CrashLoopBackOff root cause by driving the LangGraph agent to correlate pod
  status, events, and container logs in the student namespace
- Interpret agent tool call output and reasoning to identify the specific cause of pod failure
  as distinct from generic oc describe output

## Lab Structure

| Section | Title | Duration |
|---------|-------|----------|
| 1 | Observe the Broken Application | ~8 min |
| 2 | Run the AI Agent Diagnosis | ~13 min |
| 3 | Interpret Agent Findings | ~9 min |

## Detailed Steps

### Section 1: Observe the Broken Application

1. Confirm the sample application is deployed in your namespace:
   `oc get pods -n <your-namespace>`
2. Observe that one or more pods are in a `CrashLoopBackOff` state.
3. Use the oc CLI to inspect the pod status manually — note the restart count and last
   termination reason:
   `oc describe pod <pod-name> -n <your-namespace>`
4. Review the container logs for the crashing pod:
   `oc logs <pod-name> -n <your-namespace> --previous`
5. Note what you observe: is the root cause immediately obvious from the CLI output, or
   does it require further correlation? Record your initial hypothesis.

### Section 2: Run the AI Agent Diagnosis

6. With the LangGraph agent running, submit a diagnostic prompt asking it to investigate
   the CrashLoopBackOff in your namespace. The exact prompt form is provided in the lab guide.
7. Observe the agent's tool call sequence — it will issue calls against the OpenShift API
   to retrieve pod status, events, and logs.
8. Watch each tool call result appear as the agent builds its context:
   - Pod status and restart count retrieval
   - Event timeline retrieval for the failing pod
   - Container log retrieval (including previous termination)
9. Allow the agent to complete its reasoning pass and return a root cause summary.
10. If the agent requests clarification or additional scope, respond as indicated in the
    lab guide.

### Section 3: Interpret Agent Findings

11. Read the agent's root cause summary. Compare it to your initial hypothesis from step 5.
12. Identify which data sources the agent correlated to reach its conclusion (pod events,
    log error messages, termination reason) — the agent's tool call trace shows this.
13. Note whether the agent's explanation provides more specific root cause detail than the
    raw oc describe output you reviewed in Section 1.
14. Answer the reflection question in the lab guide: what would have taken longer or required
    more expertise if you had investigated this manually?
15. Do not remediate the fault — the broken application intentionally stays broken for
    continuity with Module 3.

## Key Takeaways

- The AI agent correlates pod status, events, and logs together in a single reasoning pass
  rather than requiring the engineer to manually join that data.
- CrashLoopBackOff root causes often require cross-referencing multiple oc outputs; the
  agent surfaces this correlation explicitly.
- Module 3 builds on the same running agent and broken application, adding resource
  exhaustion and networking scenarios to the same namespace.
