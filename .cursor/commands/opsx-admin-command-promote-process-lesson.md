---
name: /opsx-admin-command-promote-process-lesson
id: opsx-admin-command-promote-process-lesson
category: Workflow
description: "Process-only lesson → classify; default EXTEND via meta-fix-command-defects; design-command only for NEW_COMMAND (not product learn-from-bug)"
argument-hint: "[Bugbot / FIXED packet / process defect notes]"
---

# /opsx-admin-command-promote-process-lesson

Adjudicate a **process / command-contract** lesson after a Bugbot finding or a
`/opsx-meta-fix-command-defects` `FIXED` packet, then route to the correct
repair path.

**Default repair path:** `extend_existing` → `/opsx-meta-fix-command-defects`
(pasteable FILES + PROPOSED_BEHAVIOR hint).

**Exception only:** `design_brief_required` → `/opsx-admin-command-design-command`
when a **new** command file or greenfield check is required (no durable
authority to extend).

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

v1 never edits files. Owner applies guardrail fixes via
`/opsx-meta-fix-command-defects` (+ `AUTHORIZE_COMMAND_FIX`), or (only when
`design_brief_required` for a **new** command) via
`/opsx-admin-command-design-command`. This command only classifies the process
lesson and emits the next pasteable command / FIX_PLAN hint.

## Hard boundaries

MUST NOT:

- edit production code, tests, or OpenSpec product specs;
- edit `.cursor/commands/**` / rules / skills in this command (v1);
- invoke or substitute `/opsx-learn-from-bug` for process-contract lessons;
- route typing packets here;
- route behavioral product bugs here;
- create worklogs or a new learning hierarchy;
- auto-create a new command file;
- emit `DESIGN_BRIEF_READY` when the change is an extend/guardrail on an
  existing authority (must use `EXTEND_EXISTING` instead);
- treat `DESIRED_ARTIFACT: extend_command` as a reason to call design-command;
- bypass design-command need analysis when truly NEW (brief ≠ NEW_COMMAND_REQUIRED proof).

## Evidence sources (priority)

1. `$ARGUMENTS` / pasted Bugbot or FIXED packet;
2. latest same-chat `/opsx-meta-fix-command-defects` `FIXED` /
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
| `extend_existing` | existing command/rule/contract should gain a guardrail | `/opsx-meta-fix-command-defects` (+ hint FILES + PROPOSED_BEHAVIOR) |
| `design_brief_required` | **new** command file or greenfield check; no durable authority to extend | `/opsx-admin-command-design-command` + brief |
| `needs_more_evidence` | class unclear | one extraction question |
| `wrong_branch` | not process | redirect typing or logic |

### Extend-first rule (mandatory)

Prefer `extend_existing` (`STATUS: EXTEND_EXISTING`) when **all** hold:

- a durable authority path already exists (contract, command, rule, or skill);
- the change is a guardrail / wording / wire-up on that authority or its
  listed producers/consumers;
- no new command file is required.

Examples that MUST be `extend_existing` (not `design_brief_required`):

- `AUTHORITY_ALREADY_EXISTS` (e.g. Product Acceptance kernel present; need
  enforce/echo);
- any lesson whose natural artifact would be `DESIRED_ARTIFACT: extend_command`;
- wiring an existing PA/scenario/verify consumer to match an already-written
  pillar.

`design_brief_required` ONLY when a **new** `.cursor/commands/**` file (or
equivalent greenfield check with no extend target) is required.

4. If `extend_existing`: emit `STATUS: EXTEND_EXISTING` with pasteable
   `FIX_PLAN` hint (FILES + CURRENT/PROPOSED_BEHAVIOR) for
   `/opsx-meta-fix-command-defects`. Do **not** emit `DESIGN_BRIEF_READY`.
5. If `design_brief_required` (new command only): emit full
   `DESIGN_BRIEF_READY` packet (below). `DESIRED_ARTIFACT` MUST be
   `new_command` or `new_check_rule` (greenfield) — never `extend_command`.
6. Do not write files.

## EXTEND_EXISTING packet (default repair)

```text
STATUS: EXTEND_EXISTING
SOURCE: opsx-admin-command-promote-process-lesson
PROCESS_CLASS:
PROCESS_LESSON:
EVIDENCE_REFS:
-
DISPOSITION: extend_existing
FIX_PLAN_HINT:
  STATUS: FIX_PLAN_READY
  DEFECTS_TO_FIX:
  - id/title:
    CURRENT_BEHAVIOR:
    PROPOSED_BEHAVIOR:
    FILES:
      - <exact process path>
NEXT_ACTION: /opsx-meta-fix-command-defects
```

## DESIGN_BRIEF_READY packet (new command only)

```text
STATUS: DESIGN_BRIEF_READY
SOURCE: opsx-admin-command-promote-process-lesson
PROCESS_CLASS:
PROCESS_LESSON:
EVIDENCE_REFS:
- 
WHY_EXISTING_INSUFFICIENT:
  (must state why no durable authority can be extended)
DESIRED_ARTIFACT: new_command | new_check_rule
CONSTRAINTS:
- process surfaces only
- F6: not /opsx-fix-bug / not /opsx-bug-hunt
- no product code
- design-command still owns need analysis (IMPROVE vs NEW)
- FORBIDDEN: DESIRED_ARTIFACT extend_command (use EXTEND_EXISTING instead)
SUGGESTED_NAME:
NEXT_ACTION: /opsx-admin-command-design-command
```

## Output contract

```text
STATUS: EXTEND_EXISTING | DESIGN_BRIEF_READY | NO_PROCESS_LESSON | BLOCKED_NEEDS_EVIDENCE | WRONG_BRANCH
MODE: READ_ONLY

BRANCH: process_commands
(not typing, not product_logic)

PROCESS_CLASS:
PROCESS_LESSON:
DISPOSITION:
EVIDENCE_REFS:

FIX_PLAN_HINT:   # present iff EXTEND_EXISTING
...

DESIGN_BRIEF:   # present iff DESIGN_BRIEF_READY (new command only)
...

WHAT_HAPPENED:
WHY:
OWNER_DECISION_REQUIRED:
NEXT_ACTION:
DO_NOT_DO_YET:
- /opsx-learn-from-bug for this process lesson
- /opsx-bug-hunt for command-contract class detection
- creating command files from this command alone
- /opsx-admin-command-design-command when EXTEND_EXISTING applies
```

## Relationship to other branches

```text
unclear process question → /opsx-admin-command-consult  (triage / route)
typing  → /opsx-fix-types / static-check     (no promote-process-lesson)
logic   → /opsx-fix-bug → /opsx-learn-from-bug
process → /opsx-meta-fix-command-defects          (primary repair)
        → /opsx-admin-command-promote-process-lesson  (classify lesson)
            → /opsx-meta-fix-command-defects       (if EXTEND_EXISTING — default)
            → /opsx-admin-command-design-command      (if DESIGN_BRIEF_READY — NEW only)
```

## I/O budgets

- Prefer Grep + section Read; parallel Read max 2;
- Only open paths cited in the defect evidence (plus exact shared contracts
  those paths cite);
- Do not preload learn-from-bug, analyze-pipeline, or full command-set dumps.

## Self-review

- process-only branch enforced;
- no file writes in v1;
- extend-first: AUTHORITY_ALREADY_EXISTS / extend_command ⇒ EXTEND_EXISTING;
- DESIGN_BRIEF only for new_command / greenfield; never for extend_command;
- DESIGN_BRIEF does not skip design-command need analysis when NEW;
- product learn-from-bug not used for command-contract lessons.
