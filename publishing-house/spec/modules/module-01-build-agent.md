# Module 1: Build Your First OpenShift Troubleshooting Agent

## Brief Overview

This module introduces LangGraph as an agent framework and walks students through connecting
it to the Red Hat OpenShift AI model serving endpoint that has been pre-provisioned in the
shared cluster. There is no cluster installation required — the RHOAI Operator and model
endpoint are already active. Students configure the LangGraph agent and verify it can reach
the model endpoint and query the OpenShift API. This module is a prerequisite for Modules 2
and 3, which use the running agent to investigate fault scenarios.

## Audience and Time

- **Target personas:** Platform engineers (intermediate)
- **Prerequisites:** Familiarity with oc CLI, namespaces, pods, and events; basic understanding
  of what LLMs do; no prior agent development experience required
- **Estimated duration:** ~25 min

## Learning Objectives

- Configure a LangGraph troubleshooting agent by connecting it to the Red Hat OpenShift AI
  model serving endpoint in the shared cluster
- Verify that the configured agent can successfully reach the model endpoint and issue a
  test query against live OpenShift APIs

## Lab Structure

| Section | Title | Duration |
|---------|-------|----------|
| 1 | Locate the RHOAI Model Endpoint | ~7 min |
| 2 | Configure the LangGraph Agent | ~12 min |
| 3 | Verify Agent Connectivity | ~6 min |

## Detailed Steps

### Section 1: Locate the RHOAI Model Endpoint

1. Log in to the OpenShift cluster using the credentials provided in the Showroom environment.
2. Confirm access to your student namespace:
   `oc project <your-namespace>`
3. Retrieve the model serving endpoint URL from the cluster. The endpoint is provisioned in
   the RHOAI model serving namespace — inspect the relevant Service or Route:
   `oc get route -n <rhoai-model-serving-namespace>`
4. Note the endpoint URL and any required authentication token or secret; these will be needed
   in the next section.
5. Confirm the model serving endpoint is reachable by issuing a basic health check against it.

### Section 2: Configure the LangGraph Agent

6. Open the agent configuration provided in your student namespace. The LangGraph agent
   skeleton is pre-staged — locate the configuration file in the provided working directory.
7. Set the model endpoint URL from Section 1 in the agent configuration.
8. Set any required credentials or token in the configuration (use the value retrieved
   in step 4).
9. Review the OpenShift API tool definitions included in the agent skeleton — these are the
   tools the agent will call to query pod status, events, and resource metrics.
10. Start the LangGraph agent:
    `<agent start command per lab guide>`
11. Observe the startup output to confirm the agent initialized without errors.

### Section 3: Verify Agent Connectivity

12. Send a simple test prompt to the running agent — for example, ask it to list pods in
    your namespace.
13. Observe the agent invoking an OpenShift API tool call and returning pod information.
14. Confirm the response includes real data from your namespace (not a placeholder or error).
15. If the agent returns an error, check the endpoint URL and credentials set in Section 2
    and restart.

## Key Takeaways

- The RHOAI model serving endpoint acts as the LLM backend for the LangGraph agent; students
  do not need to install or provision it.
- LangGraph connects to OpenShift through tool definitions that wrap oc-equivalent API calls.
- A verified agent connection is required before proceeding to Modules 2 and 3.

## Infrastructure Notes

- RHOAI Operator and model serving endpoint are provisioned at cluster startup by lab
  automation; students do not install them.
- The LangGraph agent skeleton is pre-deployed in each student namespace.
- If the model endpoint is unreachable, escalate to the lab facilitator — this indicates
  an infrastructure issue, not a student configuration error.
