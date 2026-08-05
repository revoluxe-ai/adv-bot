---
description: "Shared cite-only contract for OPSX *-task wrappers: Task launch + Final report relay. Not a user-facing /opsx-* command."
---

# OPSX Task Wrapper Contract

Shared contract for thin `*-task` Cursor command wrappers.

This file is **not** a user-facing `/opsx-*` workflow command.
Do **not** invoke it as `/opsx-task-wrapper-contract`.
Wrappers that isolate independent gates MUST cite and follow it.

Companion patterns:

* `/opsx-static-check` internal workers — `.cursor/static-check/base/worker-prompt.md`
* Target gate full contracts remain SoT for behavior and verdicts

## Purpose

Run a target OPSX command inside a **fresh Cursor Task** so the worker does
not inherit Owner-chat implementer history, then relay the worker Final report
unchanged.

## Hard rules

1. Wrapper **does not** own gate logic, STATUS semantics, or archive verdicts.
2. Wrapper **must not** reinterpret, soften, or override target `STATUS` /
   `GO` / `NO_GO` / `PASS` / `FAIL`.
3. Wrapper **writes no files** of its own. Target write rights apply only
   inside the Task when the target contract explicitly allows them
   (most gates are READ_ONLY).
4. Task prompt **must not** include parent chat transcript, prior GO claims,
   implementer rationales, or “we already verified”.
5. Task prompt **must** include:
   - absolute `REPO_ROOT`
   - exact target command path under `.cursor/commands/`
   - remaining Owner args passthrough
   - instruction to follow **only** that command file (+ its cited policies)
   - instruction to return **only** that command’s Final report contract
6. Parent after Task completion: print worker Final report to Owner; do not
   add a second verdict layer.
7. If Task / `subagent_type` unavailable → `STATUS=BLOCKED` with pasteable
   inline fallback to the target command (no silent inline run pretending
   to be isolated).
8. System/Task completion notification alone is **not** the Owner Final
   report — parent must relay the worker body.

## Default Task types

| Target family | `subagent_type` |
|---------------|-----------------|
| verify, external-call, performance, antipattern, pipeline-regression | `generalPurpose` |
| static-check (whole orchestrator) | `generalPurpose` (inner workers stay registry `shell`) |

Fallback once: if preferred type missing from live Task enum → `generalPurpose`
with the same prompt. Never invent custom agent names.

## Required Task prompt body

```text
You are a READ-ONLY OPSX gate worker (unless the target command explicitly
allows listed writes).

REPO_ROOT: <abs path>
TARGET_COMMAND: <e.g. /opsx-verify>
TARGET_CONTRACT: <REPO_ROOT>/.cursor/commands/<opsx-….md>
ARGS: <passthrough>

Load and follow ONLY TARGET_CONTRACT (and files it explicitly requires).
Do NOT use parent chat history.
Do NOT invent prior PASS/GO claims.
Do NOT edit files unless TARGET_CONTRACT explicitly authorizes the write
for these ARGS.

Return ONLY the Final report defined by TARGET_CONTRACT.
Working directory: <abs REPO_ROOT>
```

## Wrapper file shape (thin)

Each `/opsx-*-task` command file should stay short:

* frontmatter `name` / `id` / `description` / `argument-hint`
* one-line purpose + pointer to this contract
* exact `TARGET_CONTRACT` path
* default `subagent_type`
* steps: parse args → Task launch → wait → relay
* self-check: no reinterpret; no transcript dump; inline fallback on BLOCKED

## Pipeline note

Soft recommends may prefer `*-task` pasteables for independence.
Inline target commands remain **ALSO_OK**.
Archive authority remains the verify Final report contract, not the wrapper name.
