---
name: /opsx-antipattern-gate-task
id: opsx-antipattern-gate-task
category: Workflow
description: "Fresh-Task wrapper for /opsx-antipattern-gate — launch + relay only"
argument-hint: "base=<ref> [head=<ref>] [focus=…] [change=<name>] [accept=…|reject=… GO]"
---

# /opsx-antipattern-gate-task

Thin wrapper. SoT: `.cursor/commands/opsx-antipattern-gate.md`.
Shared launch rules: `.cursor/commands/opsx-task-wrapper-contract.md`.

## Purpose

Run antipattern gate in a fresh Task; relay Final report unchanged.

## User input

```text
$ARGUMENTS
```

Passthrough (SCAN default; ledger write only if target args include
`accept=`/`reject=` + `GO`).

## Execution

1. Follow `opsx-task-wrapper-contract.md`.
2. `TARGET_CONTRACT` = `.cursor/commands/opsx-antipattern-gate.md`
3. Task `subagent_type`: `generalPurpose`
4. Prompt: wrapper-contract body with
   `TARGET_COMMAND=/opsx-antipattern-gate`, `ARGS=$ARGUMENTS`
5. Relay worker Final report as-is.
6. Do not reinterpret PASS/FAIL; do not invent ledger writes.
7. Task unavailable → `STATUS=BLOCKED`; fallback:

```text
/opsx-antipattern-gate $ARGUMENTS
```

## Authority

Ledger writes (if any) only inside Task under target GO rules.
Wrapper itself never appends ledger.

## Self-check

- [ ] No reinterpret of STATUS
- [ ] No parent transcript in prompt
- [ ] Report relayed unchanged
