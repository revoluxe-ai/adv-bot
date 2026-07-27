---
name: /opsx-admin-command-fix-command-defects
id: opsx-admin-command-fix-command-defects
category: Workflow
description: Plan (READ_ONLY) or apply (GO) command-contract defect fixes with narrow sequential I/O
argument-hint: "[optional packet or defect notes] [GO]"
---

# /opsx-admin-command-fix-command-defects

Plan or apply confirmed command-contract defects on **process contracts only**
(`.cursor/commands/**`, `.cursor/rules/**`, `.cursor/skills/**`,
`.cursor/agents/**`, `.cursor/static-check/**`, `.agents/**`, related shared
OPSX contracts, and mirrors when listed).

Does **not** edit production code, OpenSpec product specs, or tasks unless the
packet explicitly lists them.

If the human is still unsure whether the issue is a contract defect, a
pipeline redesign topic, a new-command need, or only a relationship question
→ `/opsx-admin-command-consult` first. Use this command when the defect target
is already identified (or a usable `FIX_PLAN_READY` / review packet exists).

Follow `.cursor/commands/opsx-source-resolution.md` and
`.cursor/commands/opsx-execution-preflight.md` (including **Read / tool I/O budgets**).

## User input

```text
$ARGUMENTS
```

Argument is **optional**. Invoking the command with an empty argument is valid.

## Modes

| Input | Mode | Writes |
|---|---|---|
| no `GO` (default) | `READ_ONLY` | never |
| exact token `GO` + usable `FIX_PLAN_READY` | `APPLY` | listed process files only |

### READ_ONLY (default — no mandatory argument)

When `GO` is absent:

- do not edit files;
- do not stage or commit;
- do not require a pasted `FIX_PLAN_READY` packet;
- build or refine a fix plan from whatever is available:
  1. optional `$ARGUMENTS` / pasted packet;
  2. else the latest completed review / analyze output in this chat
     (`CONFIRMED_DEFECTS`, `FIX_PLAN_READY`, or equivalent);
  3. else a short free-form defect note in `$ARGUMENTS` or the latest user
     message.
- If none of those exist → ask **one** narrow question for the defect source
  (review output, file list, or short description). Do not invent defects.
- Output a `STATUS: FIX_PLAN_READY` packet (or `BLOCKED_NEEDS_EVIDENCE` if
  evidence is insufficient).
- End with exact next owner action, e.g. `Reply: GO` to apply the packet.

### APPLY (requires `GO`)

You may edit files **only** when user input contains the exact token `GO`
**and** a usable `FIX_PLAN_READY` packet is present (in `$ARGUMENTS` or the
immediately preceding plan output in this chat).

If `GO` is present but there is no usable plan → stop with
`BLOCKED_NEEDS_FIX_PLAN` (still no writes).

## Packet shape

```text
STATUS: FIX_PLAN_READY
DEFECTS_TO_FIX:
...
FILES:
...
PROPOSED_BEHAVIOR:
...
```

For APPLY: if `STATUS` is not `FIX_PLAN_READY` or `DEFECTS_TO_FIX` is empty →
`BLOCKED_NEEDS_FIX_PLAN`.

## Hard I/O rules (mandatory — hang prevention)

Do **not** reproduce the failure mode of bulk parallel Reads.

1. Build the work list **only** from `FILES:` entries in the packet (plus shared
   contracts those FILES already cite by exact path). In READ_ONLY without a
   packet, derive a provisional file list only from cited paths in the chat
   evidence — never from a full command-set dump.
2. Never open `opsx-admin-command-analyze-pipeline.md`, `opsx-learn-from-bug.md`,
   `opsx-admin-command-design-command.md`, or other large siblings unless they
   appear in `FILES:` or are an exact cited dependency required for the current
   defect.
3. Process **one defect at a time**, and within a defect **one file at a time**:
   - `Read` that exact path (use `limit`/`offset` or Grep-first for files > ~200 lines);
   - in APPLY: patch for `PROPOSED_BEHAVIOR`; in READ_ONLY: only inspect;
   - only then open the next file.
4. Max **2** concurrent `Read` calls — prefer **1** for this command.
5. Prefer `Grep` over full-file Read when locating a token.
6. No Task/subagent “extract all opsx commands”. Fix/plan from packet or chat
   evidence only.
7. If a Read stalls/times out → stop stacking Reads; report
   `blocked_preflight_timeout` for that path; continue other listed files only
   if independent.

## Steps

### READ_ONLY

1. Resolve evidence source (optional args → chat packet → free-form note).
2. Parse or draft `DEFECTS_TO_FIX` + `FILES` + `PROPOSED_BEHAVIOR`.
3. Optionally spot-check listed files (narrow Grep/Read) to validate the plan;
   do not write.
4. Return `FIX_PLAN_READY` (or blocked status) + `NEXT_ACTION: Reply: GO`.

### APPLY

1. Parse `DEFECTS_TO_FIX` into an ordered list. Announce count and the exact
   file set (deduped).
2. For each defect:
   - Restate `CURRENT_BEHAVIOR` → `PROPOSED_BEHAVIOR` in one short line.
   - For each path in that defect’s `FILES:`:
     - resolve exact path (no rediscovery);
     - Grep/Read narrowly;
     - patch to match proposed behavior;
     - skip if already compliant (record `already_fixed`).
3. After all listed files: quick self-check that no new unbounded
   “read all / search all decisions” instruction was introduced.
4. Do not commit. After edits, hand off to `/opsx-admin-command-commit`
   (process surfaces only). Never point product/code commits here via
   `/opsx-commit` for command/rule/skill files.

## Out of scope

- Production / app code
- `openspec/decisions/**` content (unless listed in FILES)
- Tasks / product specs
- Running `/opsx-review-commands` or full command-set re-audit mid-fix
- “While I’m here” refactors of unrelated commands
- Any write while `GO` is absent

## Output

### READ_ONLY

```text
STATUS: FIX_PLAN_READY | BLOCKED_NEEDS_EVIDENCE | blocked_preflight_timeout
MODE: READ_ONLY

DEFECTS_TO_FIX:
- id/title:
  - CURRENT_BEHAVIOR:
  - PROPOSED_BEHAVIOR:
  - FILES:

READ_IO:
- paths_opened:
- parallel_max_used:
- timeouts:

NEXT_ACTION:
- Reply: GO
  (or provide missing evidence if blocked)
```

### APPLY

```text
STATUS: FIXED | PARTIAL | BLOCKED_NEEDS_FIX_PLAN | blocked_preflight_timeout
MODE: APPLY

DEFECTS_APPLIED:
- id/title:
  - files_changed:
  - already_fixed:
  - skipped_reason:

READ_IO:
- paths_opened:
- parallel_max_used:
- timeouts:

FILES_NOT_TOUCHED:
- (explicit: production, decisions, tasks, unlisted commands)

NEXT_ACTION:
- if process files changed: /opsx-admin-command-commit
- else: none
- optional after FIXED (transferable process class?): /opsx-admin-command-promote-process-lesson
  (separate from product /opsx-learn-from-bug)
```

After a successful `FIXED` APPLY, if the defect class looks transferable
(missing guardrail, wrong branch, durable-handoff omission, ADL/exhaust gap,
etc.), prefer hinting `/opsx-admin-command-promote-process-lesson` so the owner
can promote a process lesson → `DESIGN_BRIEF` without mixing into product
`/opsx-learn-from-bug`.

## Self-review

Before returning:

- mode matches input (`GO` ⇒ APPLY, else READ_ONLY);
- READ_ONLY never wrote files and never required a mandatory packet argument;
- every APPLY edit maps to a packet defect + listed file;
- no bulk preload of the command set;
- decision lookup changes stay context-first / bounded fallback;
- I/O stayed within execution-preflight Read budgets.
