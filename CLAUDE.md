# Publishing House Project

## On every session start

Read `publishing-house/manifest.yaml`. Check `stage.current`. Follow the instructions for that stage below.

## Stage: intake

Conduct the spec interview. Ask one question at a time — do not dump all questions at once.

Collect in this order:
1. What is this lab about? (purpose, problem it solves)
2. Who is the target audience? (role, experience level)
3. What will students be able to do after completing it? (learning objectives, aim for 3-5)
4. How many modules? What is each module about?
5. What OpenShift version does this target? (must be 4.20 or higher)
6. What infrastructure? (shared cluster / per-student dedicated / CNV pool)
7. How long will it take? (hours)
8. Deployment mode: RHDP catalog (`rhdp_published`) or personal use (`self_published`)?
9. Who should review the spec? (reviewer email)

After collecting all answers:
1. Write `publishing-house/spec/design.md` with the structured spec
2. Update `publishing-house/manifest.yaml` — fill in the `spec:` section and set `project.slug`, `project.jira_ticket`, `project.content_type`, `project.reviewer_email`, `project.deployment_mode`
3. Tell the author to run `python ph-check.py` when they're ready to validate

Do NOT change `stage.current`. Stage transitions require explicit author approval and Central API validation.

## Stage: development

Help the author write content. Answer questions about AsciiDoc, module structure, learning objectives, procedures. You are an assistant — do not advance stages or modify spec without explicit instruction.

Run compliance check when asked:
```bash
python ph-check.py
```

## Zero-Touch Automation

Zero-Touch (ZT) projects use [runtime-automation/](runtime-automation/) for runtime automation and
[setup-automation/](setup-automation/) for setup automation. These directories are removed by the
orchestrator for classic Showroom projects during intake.

## Stage: review or ready

Show the author the current spec or compliance results and wait for instruction.

---

## Central API (REST — no MCP)

Policy data is served by Central API. ph-check.py fetches these automatically:
- OCP version minimum: `GET https://ph-central.apps.cluster-v27ps.dynamic2.redhatworkshops.io/api/v1/reference/ocp-policy`
- Product vocabulary: `GET https://ph-central.apps.cluster-v27ps.dynamic2.redhatworkshops.io/api/v1/reference/vocabulary`

No authentication required for policy endpoints.

## File locations
- Spec: `publishing-house/spec/design.md`
- Module outlines: `publishing-house/spec/modules/`
- Content: `content/modules/ROOT/pages/`
- Navigation: `content/modules/ROOT/nav.adoc`
