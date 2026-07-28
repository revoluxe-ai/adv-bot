---
name: /opsx-bound-scope
id: opsx-bound-scope
category: Workflow
description: "Bound an oversized OpenSpec change to KEEP scope; park DEFER remainder in DOTO/WORKLOG.md; hand off KEEP revisions to /opsx-update"
---

# /opsx-bound-scope

Bound the current OpenSpec change to an owner-approved KEEP set. Park deferred
remainder in `DOTO/WORKLOG.md`. Produce an `/opsx-update` handoff for the KEEP
artifact revisions.

This is a local WB Sky OpenSpec workflow command.
It is not an upstream OpenSpec command.

## Purpose

Use when a change TZ / DoD has grown too large mid-flight and the owner needs:

1. a hard boundary on what stays in the **current** change;
2. deferred ideas preserved in the product WORKLOG;
3. a pasteable handoff so `/opsx-update` applies the KEEP narrowing coherently.

## When to use

- Change proposal/design/tasks/specs раздулись («нафантазировали»).
- Need an MVP / shippable boundary before apply / verify / archive.
- Want to park remainder without losing it and without keeping it as owed DoD.
- After `/opsx-explore` emitted `NOW_LATER` and the owner accepted
  the DO_NOW / DO_LATER table (explore does not park — this command does).

## When not to use

- Coherence-only artifact fix, no park → `/opsx-update`
- Read / think with WORKLOG context → `/opsx-explore` (read-only WORKLOG;
  optional now/later *suggestion* only)
- Split oversized **git** diff into PRs → `/opsx-split-for-pr`
- Entirely different product intent → `/opsx-new`
- Bug-learning sink → `/opsx-learn-from-bug`
- «Just analyze now/later in chat» with no park intent → stay on `/opsx-explore`

## Usage

```text
/opsx-bound-scope change=<CHANGE_ID>
/opsx-bound-scope:GO change=<CHANGE_ID>
```

Optional:

```text
/opsx-bound-scope change=<CHANGE_ID> keep=<short MVP boundary hint>
```

If `change=` is missing, prompt via `openspec list --json` (same selection
discipline as `/opsx-update`). Do not guess.

## Modes

### `/opsx-bound-scope` (default) — READ_ONLY plan

MUST NOT edit files.
MUST NOT append WORKLOG.
MUST NOT revise OpenSpec artifacts.
MUST NOT edit production code.

MUST print **exactly two** printouts (and the return contract):

1. `PRINTOUT_KEEP` — what stays in the current change after the bound.
2. `PRINTOUT_WORKLOG` — exact entries proposed for `DOTO/WORKLOG.md`.

Then stop and ask for GO.

### `/opsx-bound-scope:GO` — apply park + handoff

Allowed only after the owner accepted the plan printouts
(explicit `GO` / `:GO` for that plan). Acknowledgement or discussion ≠ GO.

MUST:

1. Append `PRINTOUT_WORKLOG` entries to `DOTO/WORKLOG.md` (append-only).
2. Emit `UPDATE_HANDOFF` for `/opsx-update` (KEEP narrowing).
3. NOT edit OpenSpec change artifacts itself (update owns planning writes).
4. NOT edit production code.
5. NOT rollback code for `IMPLEMENTED_BUT_DEFERRED` items.

## Authority split

| Concern | Owner |
|---|---|
| KEEP vs DEFER decision (plan) | this command + owner GO |
| Suggest now/later while thinking | `/opsx-explore` (`NOW_LATER`, no write) |
| Append deferred notes to `DOTO/WORKLOG.md` | this command on `:GO` |
| Revise change planning artifacts to KEEP | `/opsx-update` via `UPDATE_HANDOFF` |
| Warn about open parks for this change | `/opsx-update` (mandatory `DEFERRED_PARKS_FOR_CHANGE`) |
| Re-enter a parked idea into **current** scope | `/opsx-update` only after `REENTER_CONFIRMED` |
| Annotate WORKLOG `[re-entered:<CHANGE_ID>]` | `/opsx-update` (narrow write after confirm) |
| Read WORKLOG as raw notes | `/opsx-explore` (must not write) |
| Git/PR packaging | `/opsx-split-for-pr` |

## Paired lifecycle with `/opsx-update`

```text
explore (optional NOW_LATER)
  → /opsx-bound-scope          (PRINTOUT_KEEP + PRINTOUT_WORKLOG)
  → /opsx-bound-scope:GO       (append WORKLOG parks + UPDATE_HANDOFF)
  → /opsx-update               (apply KEEP; print DEFERRED_PARKS_FOR_CHANGE)
  → later: owner asks to add a parked idea again
  → /opsx-update               (DEFERRED_REENTRY_REQUIRED → wait)
  → owner: REENTER_CONFIRMED   (then artifacts + WORKLOG [re-entered:] mark)
```

Deferred parks are **sticky**: after `:GO`, `/opsx-update` must not silently
restore them as owed DoD. Re-entry is an explicit owner decision on update,
not a second bound-scope run (bound-scope parks; update may re-enter).
Explore may only *propose* the split; it never parks and never re-enters.

When planning, prefer WORKLOG entry titles that `/opsx-update` can match later
(stable short title + `[deferred-from:<CHANGE_ID>]`).

## Preflight

Follow `.cursor/commands/opsx-source-resolution.md` and
`.cursor/commands/opsx-execution-preflight.md`.

```text
OPERATION_REASON: resolve named change + existing planning artifacts
REQUIRED_FOR: KEEP/DEFER units and UPDATE_HANDOFF paths
SKIP_IF: change= missing (prompt first)
TIME_BUDGET: status/list 15s; targeted reads ≤120 lines first pass
FAILURE_BEHAVIOR: BLOCKED_NEEDS_OWNER or EVIDENCE_GAP / NO_GO
```

Architecture Decision Lookup: same budgeted rules as `/opsx-update` when KEEP
cut touches ownership / layering / write-path / domain invariant. Unresolved
gaps → `NO_GO` (do not invent KEEP).

## Steps (plan mode)

1. Resolve `change=<CHANGE_ID>` (or prompt).
2. `openspec status --change "<name>" --json` — use `artifactPaths` /
   `existingOutputPaths` only.
3. Read existing planning artifacts needed to list requirement/task units
   (proposal, design, tasks, specs; decisions when ADL requires).
3b. If the owner (or prior `/opsx-explore` turn) supplied a `NOW_LATER`
    / `SPLIT_HINT` / DO_NOW·DO_LATER table, use it as the **starting** partition;
    still re-derive units from change artifacts and show any drift vs the hint.
4. Build unit list. Tag each unit:

```text
KEEP_IN_CHANGE
DEFER_TO_WORKLOG
IMPLEMENTED_BUT_DEFERRED
```

`IMPLEMENTED_BUT_DEFERRED`: deferred in TZ but evidence shows code already
implements it — flag and do **not** propose code rollback. Owner must decide
before GO if that unit stays KEEP or is parked with an explicit note.

5. If any unit is ambiguous → one clarifying question; do not invent MVP.
6. Emit the two printouts + return contract. Stop for GO.

## Steps (`:GO`)

1. Confirm the plan being applied matches the last accepted printouts.
2. If `IMPLEMENTED_BUT_DEFERRED` remains unresolved →
   `BLOCKED_NEEDS_OWNER` (no WORKLOG write, no handoff).
3. Append WORKLOG entries exactly from accepted `PRINTOUT_WORKLOG`
   (append-only; do not rewrite unrelated inbox lines).
4. Emit `UPDATE_HANDOFF` (below).
5. Point next action to `/opsx-update` with the handoff (guidance only —
   do not auto-run update unless the owner explicitly asks in the same turn).

## Printout 1 — PRINTOUT_KEEP

```text
PRINTOUT_KEEP:
CHANGE_ID: <id>
MVP_BOUNDARY: <one sentence>
KEEP_UNITS:
- <unit id/title> — <source artifact path> — <why keep>
OUT_OF_SCOPE_AFTER_BOUND:
- <unit id/title> — deferred (see PRINTOUT_WORKLOG)
ARTIFACT_TARGETS:
- path: <existingOutputPath>
  keep_edits: <bullet summary of deletions/narrowing for update>
STATUS: PLAN_READY | (on GO echo) BOUND_APPLIED
```

## Printout 2 — PRINTOUT_WORKLOG

Exact lines proposed for append. Prefer checklist form:

```text
PRINTOUT_WORKLOG:
TARGET: DOTO/WORKLOG.md
ENTRIES:
- [ ] [deferred-from:<CHANGE_ID>] <short title>
  source: openspec/changes/<CHANGE_ID>/<artifact>
  reason: out_of_current_mvp | oversized | owner_park
  notes: <1-3 lines from removed TZ text>
```

On `:GO`, append these entries under a dated marker if helpful:

```text
## Deferred from change <CHANGE_ID> (<YYYY-MM-DD>)
```

Do not create a second SoT: WORKLOG remains `raw_notes` (see EXPLORE_POLICY).

## UPDATE_HANDOFF (required on `:GO`)

Pasteable block for `/opsx-update`:

```text
UPDATE_HANDOFF:
SOURCE_COMMAND: /opsx-bound-scope
CHANGE_ID: <id>
STATUS: READY_FOR_UPDATE
WORKLOG_APPENDED: yes | no
WORKLOG_PATH: DOTO/WORKLOG.md
KEEP_MVP_BOUNDARY: <one sentence>
APPLY_KEEP_UNITS:
- ...
REMOVE_OR_NARROW_FROM_ARTIFACTS:
- path: <existingOutputPath>
  action: remove | narrow | mark_out_of_scope
  units: [...]
  instructions: <concrete edit guidance>
DO_NOT:
- recreate deferred units as owed tasks
- edit production code in this update
- create new change artifacts (continue frontier unchanged)
- silently ignore DEFERRED_PARKS_FOR_CHANGE (update must still print them)
NEXT_COMMAND: /opsx-update change=<CHANGE_ID>
NOTE_FOR_UPDATE: After this handoff, open WORKLOG parks for this CHANGE_ID remain
  out of scope until owner replies REENTER_CONFIRMED on a later /opsx-update.
```

`/opsx-update` consumes this as a specific revision request (confirm-before-write
still applies).

## Status tokens

```text
PLAN_READY
BOUND_APPLIED
BLOCKED_NEEDS_OWNER
NO_GO
PARTIAL_BLOCKED
```

Unit tags: `KEEP_IN_CHANGE` | `DEFER_TO_WORKLOG` | `IMPLEMENTED_BUT_DEFERRED`

## Failure behavior

- Ambiguous KEEP/DEFER → stop; one question.
- ADL / EVIDENCE_GAP on ownership → `NO_GO`; no WORKLOG append.
- Mid-GO append failure → `PARTIAL_BLOCKED`; do not pretend update handoff is complete.
- Never invent DEFER units absent from change artifacts or owner statement.
- Never delete production code.
- Never use this command as a bypass of verify / archive / sync gates.

## Return contract (every invocation)

```text
WHAT_HAPPENED:
WHY:
CURRENT_STATE:
OWNER_DECISION_REQUIRED:
NEXT_ACTION:
DO_NOT_DO_YET:
STATUS:
CHANGE_ID:
KEEP_COUNT:
DEFER_COUNT:
IMPLEMENTED_BUT_DEFERRED_COUNT:
WORKLOG_WRITTEN: yes | no
UPDATE_HANDOFF_EMITTED: yes | no
```

### Plan mode defaults

```text
OWNER_DECISION_REQUIRED: YES — approve PRINTOUT_KEEP + PRINTOUT_WORKLOG
NEXT_ACTION: Reply GO / run /opsx-bound-scope:GO change=<CHANGE_ID>
DO_NOT_DO_YET: edit artifacts; append WORKLOG; apply; archive
WORKLOG_WRITTEN: no
UPDATE_HANDOFF_EMITTED: no
```

### GO mode defaults

```text
OWNER_DECISION_REQUIRED: NO (unless blocked)
NEXT_ACTION: /opsx-update change=<CHANGE_ID> using UPDATE_HANDOFF
DO_NOT_DO_YET: treat WORKLOG as tasks.md; ship before update applies KEEP;
  rollback code for deferred units
WORKLOG_WRITTEN: yes (on success)
UPDATE_HANDOFF_EMITTED: yes (on success)
```

## Forbidden shortcuts

- MUST NOT skip the two printouts in plan mode.
- MUST NOT write WORKLOG without GO.
- MUST NOT revise change artifacts inside this command (that is `/opsx-update`).
- MUST NOT confuse this with `/opsx-split-for-pr`.
- MUST NOT use `.cursor/worklogs/` as the product defer sink (product sink is
  `DOTO/WORKLOG.md` per EXPLORE_POLICY).
- MUST NOT auto-create a new OpenSpec change per deferred line.
- MUST NOT claim that parking alone re-enters deferred ideas later — re-entry
  is owned by `/opsx-update` + `REENTER_CONFIRMED`.
- MUST NOT instruct `/opsx-update` to skip `DEFERRED_PARKS_FOR_CHANGE`.
