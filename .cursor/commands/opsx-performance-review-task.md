---
name: /opsx-performance-review-task
id: opsx-performance-review-task
category: Workflow
description: "Fresh-Task wrapper for /opsx-performance-review — launch + relay only"
argument-hint: "[scope=…] [base=<ref>] [focus=…] [same args as /opsx-performance-review]"
---

# /opsx-performance-review-task

Thin wrapper. SoT: `.cursor/commands/opsx-performance-review.md`.
Shared launch rules: `.cursor/commands/opsx-task-wrapper-contract.md`.

## Purpose

Independent performance review in a fresh Task; relay Final report unchanged.

## User input

```text
$ARGUMENTS
```

Passthrough to `/opsx-performance-review`.

## Execution

1. Follow `opsx-task-wrapper-contract.md`.
2. `TARGET_CONTRACT` = `.cursor/commands/opsx-performance-review.md`
3. Task `subagent_type`: `generalPurpose`
4. Prompt: wrapper-contract body with
   `TARGET_COMMAND=/opsx-performance-review`, `ARGS=$ARGUMENTS`
5. Relay worker Final report as-is (including FIX_PACKET / authorization if any).
6. Do not reinterpret PASS/FAIL/DATA_GAP; do not execute measurements.
7. Task unavailable → `STATUS=BLOCKED`; fallback:

```text
/opsx-performance-review $ARGUMENTS
```

## Authority

Independent performance verdict remains the target command output only.

## Self-check

- [ ] Wrapper READ_ONLY
- [ ] No measurement / live runs from wrapper
- [ ] Report relayed unchanged
