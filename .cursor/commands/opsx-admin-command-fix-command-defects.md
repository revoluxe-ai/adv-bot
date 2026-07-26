---
name: /opsx-admin-command-fix-command-defects
id: opsx-admin-command-fix-command-defects
category: Workflow
description: Apply a FIX_PLAN_READY packet to OPSX/Cursor command contracts with narrow sequential I/O
argument-hint: "[paste FIX_PLAN_READY packet]"
---

# /opsx-admin-command-fix-command-defects

Apply confirmed command-contract defects from a `FIX_PLAN_READY` packet.

This command edits **process contracts only** (`.cursor/commands/**`,
`.cursor/rules/**`, `.cursor/skills/**`, `.cursor/agents/**`,
`.cursor/static-check/**`, `.agents/**`, related shared OPSX contracts,
and mirrors when listed). It does **not** edit production code, OpenSpec
product specs, or tasks unless the packet explicitly lists them.

Follow `.cursor/commands/opsx-source-resolution.md` and `.cursor/commands/opsx-execution-preflight.md` (including **Read / tool I/O budgets**).

## Input

User provides (or the Cursor command body contains) a packet like:

```text
STATUS: FIX_PLAN_READY
DEFECTS_TO_FIX:
...
FILES:
...
PROPOSED_BEHAVIOR:
...
```

If `STATUS` is not `FIX_PLAN_READY` or `DEFECTS_TO_FIX` is empty → stop with `BLOCKED_NEEDS_FIX_PLAN`.

## Hard I/O rules (mandatory — hang prevention)

Do **not** reproduce the failure mode of bulk parallel Reads.

1. Build the work list **only** from `FILES:` entries in the packet (plus shared contracts those FILES already cite by exact path).
2. Never open `opsx-admin-command-analyze-pipeline.md`, `opsx-learn-from-bug.md`, `opsx-admin-command-design-command.md`, or other large siblings unless they appear in `FILES:` or are an exact cited dependency required for the current defect.
3. Process **one defect at a time**, and within a defect **one file at a time**:
   - `Read` that exact path (use `limit`/`offset` or Grep-first for files > ~200 lines);
   - apply the minimal patch for `PROPOSED_BEHAVIOR`;
   - only then open the next file.
4. Max **2** concurrent `Read` calls — prefer **1** for this command.
5. Prefer `Grep` over full-file Read when locating a token (`openspec/decisions/**`, verify gate, etc.).
6. No Task/subagent “extract all opsx commands” during apply. Fix from the packet evidence.
7. If a Read stalls/times out → stop stacking Reads; report `blocked_preflight_timeout` for that path; continue other listed files only if independent.

## Steps

1. Parse `DEFECTS_TO_FIX` into an ordered list. Announce count and the exact file set (deduped).
2. For each defect:
   - Restate `CURRENT_BEHAVIOR` → `PROPOSED_BEHAVIOR` in one short line.
   - For each path in that defect’s `FILES:`:
     - resolve exact path (no rediscovery);
     - Grep/Read narrowly;
     - patch to match proposed behavior;
     - skip if already compliant (record `already_fixed`).
3. After all listed files: quick self-check that no new unbounded “read all / search all decisions” instruction was introduced.
4. Do not commit. After edits, hand off to `/opsx-admin-command-commit`
   (process surfaces only). Never point product/code commits here via `/opsx-commit`
   for command/rule/skill files.

## Out of scope

- Production / app code
- `openspec/decisions/**` content (unless listed in FILES)
- Tasks / product specs
- Running `/opsx-review-commands` or full command-set re-audit mid-fix
- “While I’m here” refactors of unrelated commands

## Output

```text
STATUS: FIXED | PARTIAL | BLOCKED_NEEDS_FIX_PLAN | blocked_preflight_timeout

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
```

## Self-review

Before returning:

- every edit maps to a packet defect + listed file;
- no bulk preload of the command set;
- decision lookup changes stay context-first / bounded fallback;
- I/O stayed within execution-preflight Read budgets.
