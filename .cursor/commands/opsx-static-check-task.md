---
name: /opsx-static-check-task
id: opsx-static-check-task
category: Workflow
description: "Fresh-Task wrapper for /opsx-static-check orchestrator — launch + relay only"
argument-hint: "[FAST|FULL] [PREFLIGHT]"
---

# /opsx-static-check-task

Thin wrapper. SoT: `.cursor/commands/opsx-static-check.md`.
Shared launch rules: `.cursor/commands/opsx-task-wrapper-contract.md`.

## Purpose

Run the **whole** static-check orchestrator in a fresh Task so Owner-chat
context does not bias synthesis. Inner check workers still use the target’s
registry Task fan-out (`shell`).

## User input

```text
$ARGUMENTS
```

Passthrough (`FAST`/`FULL`/`PREFLIGHT` per target).

## Execution

1. Follow `opsx-task-wrapper-contract.md`.
2. `TARGET_CONTRACT` = `.cursor/commands/opsx-static-check.md`
3. Task `subagent_type`: `generalPurpose` (orchestrator isolation)
4. Prompt: wrapper-contract body with
   `TARGET_COMMAND=/opsx-static-check`, `ARGS=$ARGUMENTS`
   plus note: worker must itself fan-out registry checks via Task/`shell`
   as the target contract requires, then print Final report §5.
5. Relay orchestrator Final report as-is (`STATUS` / `CHECKS` / `NEXT ACTION`).
6. Do not reinterpret PASS/FAIL; do not patch check infra.
7. Task unavailable → `STATUS=BLOCKED`; fallback:

```text
/opsx-static-check $ARGUMENTS
```

## Notes

* This wrapper does **not** replace `.cursor/static-check/` workers.
* Nested Tasks (orchestrator Task → check workers) are expected.

## Self-check

- [ ] Wrapper READ_ONLY
- [ ] Final report from orchestrator relayed unchanged
- [ ] No self-repair of static-check infra
