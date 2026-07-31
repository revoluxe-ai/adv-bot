---
name: /opsx-admin-command-promote-process-lesson
id: opsx-admin-command-promote-process-lesson
category: Workflow
description: "Process-only lesson from command-contract defects → DESIGN_BRIEF for design-command (not product learn-from-bug)"
argument-hint: "[Bugbot / FIXED packet / process defect notes]"
---

# /opsx-admin-command-promote-process-lesson

Adjudicate a **process / command-contract** lesson after a Bugbot finding or a
`/opsx-admin-command-fix-command-defects` `FIXED` packet, then emit a pasteable
`DESIGN_BRIEF_READY` for `/opsx-admin-command-design-command` (or route to
extend an existing process file via fix-command-defects).

This command is **only** for the **commands / process** branch.

It is **not**:

- typing learning (use static-check / `/opsx-fix-types` gates — no lesson command);
- product / logic learning (use `/opsx-learn-from-bug`);
- a product bug fixer (use `/opsx-fix-bug`);
- a silent auto-implementer of new commands;
- a general process front-door (use `/opsx-admin-command-consult` for
  relationship / triage questions before a FIXED or Bugbot process packet).

Follow `.cursor/commands/opsx-source-resolution.md` and
`.cursor/commands/opsx-execution-preflight.md` (including Read / tool I/O budgets).

## User input

```text
$ARGUMENTS
```

Argument is optional. Empty invoke is valid if the chat already has a process
Bugbot text or a `STATUS: FIXED` packet from fix-command-defects.

## Modes

| Input | Mode | Writes |
|---|---|---|
| default (no `GO`) | `READ_ONLY` | never |
| exact token `GO` | **not used for writes in v1** | never — still READ_ONLY; reject inventing files |

v1 never edits files. Owner applies design via `/opsx-admin-command-design-command`
(+ later GO there) or fix-command-defects. This command only classifies the
process lesson and emits the brief / next pasteable command.

## Hard boundaries

MUST NOT:

- edit production code, tests, or OpenSpec product specs;
- edit `.cursor/commands/**` / rules / skills in this command (v1);
- invoke or substitute `/opsx-learn-from-bug` for process-contract lessons;
- route typing packets here;
- route behavioral product bugs here;
- create worklogs or a new learning hierarchy;
- auto-create a new command file;
- bypass design-command need analysis (brief ≠ NEW_COMMAND_REQUIRED proof).

## Evidence sources (priority)

1. `$ARGUMENTS` / pasted Bugbot or FIXED packet;
2. latest same-chat `/opsx-admin-command-fix-command-defects` `FIXED` /
   `FIX_PLAN_READY` output;
3. else ask **one** narrow question for the process defect source.

## Steps (READ_ONLY)

1. Confirm the signal is **process-contract** (`.cursor/commands/**`, rules,
   skills, static-check contracts, admin OPSX surfaces). If typing →
   `WRONG_BRANCH` / `NEXT_ACTION: /opsx-fix-types` or static-check. If product
   logic → `WRONG_BRANCH` / `NEXT_ACTION: /opsx-fix-bug` (without mixing). Stop.
2. Extract `PROCESS_CLASS`, `PROCESS_LESSON`, `EVIDENCE_REFS`.
3. Decide disposition (exactly one):

| Disposition | Meaning | NEXT |
|---|---|---|
| `no_process_lesson` | one-off fix; no transferable class | `none` |
| `extend_existing` | existing command/rule should gain a guardrail | `/opsx-admin-command-fix-command-defects` (+ hint FILES) |
| `design_brief_required` | needs new command / new check / coherent design | `/opsx-admin-command-design-command` + brief |
| `needs_more_evidence` | class unclear | one extraction question |
| `wrong_branch` | not process | redirect typing or logic |

4. If `design_brief_required`, emit full `DESIGN_BRIEF_READY` packet (below).
5. Do not write files.

## DESIGN_BRIEF_READY packet

```text
STATUS: DESIGN_BRIEF_READY
SOURCE: opsx-admin-command-promote-process-lesson
PROCESS_CLASS:
PROCESS_LESSON:
EVIDENCE_REFS:
- 
WHY_EXISTING_INSUFFICIENT:
DESIRED_ARTIFACT: new_command | extend_command | new_check_rule
CONSTRAINTS:
- process surfaces only
- F6: not /opsx-fix-bug / not /opsx-bug-hunt
- no product code
- design-command still owns need analysis (IMPROVE vs NEW)
SUGGESTED_NAME:
NEXT_ACTION: /opsx-admin-command-design-command
```

## Output contract

```text
STATUS: DESIGN_BRIEF_READY | EXTEND_EXISTING | NO_PROCESS_LESSON | BLOCKED_NEEDS_EVIDENCE | WRONG_BRANCH
MODE: READ_ONLY

BRANCH: process_commands
(not typing, not product_logic)

PROCESS_CLASS:
PROCESS_LESSON:
DISPOSITION:
EVIDENCE_REFS:

DESIGN_BRIEF:   # present iff DESIGN_BRIEF_READY
...

WHAT_HAPPENED:
WHY:
OWNER_DECISION_REQUIRED:
NEXT_ACTION:
DO_NOT_DO_YET:
- /opsx-learn-from-bug for this process lesson
- /opsx-bug-hunt for command-contract class detection
- creating command files from this command alone
```

## Relationship to other branches

```text
unclear process question → /opsx-admin-command-consult  (triage / route)
typing  → /opsx-fix-types / static-check     (no promote-process-lesson)
logic   → /opsx-fix-bug → /opsx-learn-from-bug
process → /opsx-admin-command-fix-command-defects
        → /opsx-admin-command-promote-process-lesson
        → /opsx-admin-command-design-command  (if DESIGN_BRIEF_READY)
```

## I/O budgets

- Prefer Grep + section Read; parallel Read max 2;
- Only open paths cited in the defect evidence (plus exact shared contracts
  those paths cite);
- Do not preload learn-from-bug, analyze-pipeline, or full command-set dumps.

## Self-review

- process-only branch enforced;
- no file writes in v1;
- DESIGN_BRIEF does not skip design-command need analysis;
- product learn-from-bug not used for command-contract lessons.
