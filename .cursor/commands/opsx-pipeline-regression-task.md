---
name: /opsx-pipeline-regression-task
id: opsx-pipeline-regression-task
category: Workflow
description: "Fresh-Task wrapper for pipeline REGRESSION_PIPELINE_REVIEW — launch + relay only"
argument-hint: "[optional regression notes / changed command paths]"
---

# /opsx-pipeline-regression-task

Thin wrapper for **process** pipeline regression review.
Target SoT: `.cursor/commands/opsx-admin-command-analyze-pipeline.md`
mode `REGRESSION_PIPELINE_REVIEW`.
Shared launch rules: `.cursor/commands/opsx-task-wrapper-contract.md`.

## Purpose

Run pipeline regression analysis in a fresh Task (READ_ONLY); relay Final
report unchanged. Not a product quality gate; not archive authority.

## When to use

* After process-command / GRAPH / wrapper changes
* Admin check that clarity/safety/predictability did not regress

## When not to use

* Product change verify → `/opsx-verify-task`
* Day-to-day NAVIGATE → `/opsx-pipeline`
* Live product bugs → bug-team / fix-bug

## User input

```text
$ARGUMENTS
```

Optional notes; wrapper always forces regression mode in the Task prompt.

## Execution

1. Follow `opsx-task-wrapper-contract.md`.
2. `TARGET_CONTRACT` = `.cursor/commands/opsx-admin-command-analyze-pipeline.md`
3. Task `subagent_type`: `generalPurpose`
4. Prompt: wrapper-contract body with
   `TARGET_COMMAND=/opsx-admin-command-analyze-pipeline`,
   `ARGS=REGRESSION_PIPELINE_REVIEW $ARGUMENTS`
   and explicit: Mode = REGRESSION_PIPELINE_REVIEW; READ_ONLY; no file edits.
5. Relay worker Final report as-is (`STATUS` / `PROBLEMS_FOUND` / `NEXT_ACTION`).
6. Do not reinterpret; do not edit commands from this wrapper.
7. Task unavailable → `STATUS=BLOCKED`; fallback:

```text
/opsx-admin-command-analyze-pipeline REGRESSION_PIPELINE_REVIEW $ARGUMENTS
```

## Authority

Ephemeral analysis only. Durable GRAPH materialization remains `/opsx-pipeline UPDATE GO`.

## Self-check

- [ ] READ_ONLY
- [ ] No product paths in scope
- [ ] Report relayed unchanged
