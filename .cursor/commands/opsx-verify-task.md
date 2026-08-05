---
name: /opsx-verify-task
id: opsx-verify-task
category: Workflow
description: "Fresh-Task wrapper for /opsx-verify — launch + relay Final report only"
argument-hint: "[change-name] [same args as /opsx-verify]"
---

# /opsx-verify-task

Thin wrapper. Full audit SoT: `.cursor/commands/opsx-verify.md`.
Shared launch rules: `.cursor/commands/opsx-task-wrapper-contract.md`.

## Purpose

Run `/opsx-verify` in a fresh Cursor Task (no Owner-chat implementer history),
then relay the verify Final report unchanged (`✅ GO` / `❌ NO_GO`).

## When to use

* Pre-archive independence from apply chat
* Soft pipeline / apply NEXT prefer this over inline verify

## When not to use

* Debugging verify steps interactively in-chat → `/opsx-verify`
* Any write / fix → never from this wrapper

## User input

```text
$ARGUMENTS
```

Passthrough to `/opsx-verify` (change name and optional store/context tokens).

## Execution

1. Cite and follow `opsx-task-wrapper-contract.md`.
2. `TARGET_CONTRACT` = `.cursor/commands/opsx-verify.md`
3. Launch Task:
   - `subagent_type`: `generalPurpose`
   - `prompt`: required body from wrapper contract with
     `TARGET_COMMAND=/opsx-verify`, `ARGS=$ARGUMENTS`
   - Prefer `run_in_background: true` only if parent will wait and relay
4. On completion: print worker Final report **as-is** (verify sections + final marker).
5. Do **not** reinterpret GO/NO_GO.
6. If Task unavailable → `STATUS=BLOCKED`; pasteable fallback:

```text
/opsx-verify $ARGUMENTS
```

## Authority

* Archive verdict owner remains `/opsx-verify` contract output.
* This wrapper adds no second authority.

## Self-check

- [ ] No edits by wrapper
- [ ] No chat transcript in Task prompt
- [ ] Final marker from worker relayed unchanged
