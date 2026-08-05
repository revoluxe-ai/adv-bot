---
name: /opsx-external-call-coverage-task
id: opsx-external-call-coverage-task
category: Workflow
description: "Fresh-Task wrapper for /opsx-external-call-coverage — launch + relay only"
argument-hint: "base=<ref> [head=<ref>] [focus=…] [change=<name>]"
---

# /opsx-external-call-coverage-task

Thin wrapper. SoT: `.cursor/commands/opsx-external-call-coverage.md`.
Shared launch rules: `.cursor/commands/opsx-task-wrapper-contract.md`.

## Purpose

Run external-call coverage in a fresh Task; relay Final report unchanged.

## User input

```text
$ARGUMENTS
```

Passthrough (requires `base=` per target contract).

## Execution

1. Follow `opsx-task-wrapper-contract.md`.
2. `TARGET_CONTRACT` = `.cursor/commands/opsx-external-call-coverage.md`
3. Task `subagent_type`: `generalPurpose`
4. Prompt: wrapper-contract body with
   `TARGET_COMMAND=/opsx-external-call-coverage`, `ARGS=$ARGUMENTS`
5. Relay worker Final report as-is (STATUS / GAPS / COPY_PASTE_RUNBOOK).
6. Do not reinterpret PASS/FAIL.
7. Task unavailable → `STATUS=BLOCKED`; fallback:

```text
/opsx-external-call-coverage $ARGUMENTS
```

## Authority

Disposition/archive rules remain in the target contract. Wrapper writes nothing.

## Self-check

- [ ] READ_ONLY wrapper
- [ ] No parent transcript in prompt
- [ ] Report relayed unchanged
