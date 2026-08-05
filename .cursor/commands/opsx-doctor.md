---
name: /opsx-doctor
id: opsx-doctor
category: Workflow
description: "OpenSpec change-tree hygiene: default CHECK (scan); GO deletes all qualifying corrupt leftover active changeRoots. Wraps openspec doctor + leftover gates."
argument-hint: "[CHECK] | GO | change=<name> | GO change=<name>"
---

# /opsx-doctor

Side-lane **hygiene clinic** for OpenSpec **active change trees** (ghost
leftovers). Not a product-spec rewriter.

**Mental model (minimum):**

| Input | Effect |
|-------|--------|
| `/opsx-doctor` (no `GO`) | **Scan only** — all active changes |
| `/opsx-doctor GO` | **Scan + delete** every leftover that passes the gate |
| optional `change=<name>` | Focus scan / delete to one name |

Follow `.cursor/commands/opsx-source-resolution.md` and
`.cursor/commands/opsx-execution-preflight.md` (Read / tool I/O budgets).
Prefer Grep + bounded Reads; do not dump all change bodies.

**Store selection:** If the user names a store or work lives in one, run
`openspec store list --json`, then pass `--store <id>` on `openspec doctor`
and other store-aware CLI calls.

## What this is

* Clinic over `openspec doctor` (root/store links) **plus** leftover checks
  CLI doctor does not cover.
* Default: READ_ONLY FINDINGS over **all** active `changes/<name>/`.
* Exact `GO`: delete every active `changeRoot` that qualifies as corrupt
  leftover (gate below). Optional `change=<name>` limits to one name.

## What this is NOT

* NOT rewrite of `openspec/specs/**` / main capability specs.
* NOT invent / fill empty `proposal.md` / `design.md`.
* NOT `/opsx-verify` product GO/NO_GO.
* NOT `/opsx-archive` sync / decision promote.
* NOT `/opsx-apply` / `/opsx-update`.
* NOT edit of command contracts.

## When to use

* After archive soft tripwire → doctor.
* `openspec list` shows a “complete” change that looks empty / already archived.
* Pre-commit suspicious `openspec/changes/<name>/`.
* Owner: “is the change tree dirty?”

## When not to use

* Live change audit → `/opsx-verify`.
* Archive a live change → `/opsx-archive`.
* Process-contract bugs → `/opsx-admin-command-fix-command-defects`.
* Routing → `/opsx-admin-command-consult`.

## User input

```text
$ARGUMENTS
```

| Token | Effect |
|-------|--------|
| (default) / `CHECK` | READ_ONLY scan **all** active changes |
| `GO` | Scan + delete **all** qualifying leftovers |
| `change=<name>` | Focus CHECK or GO to one name |
| `repair=remove_corrupt_leftover` | Legacy alias; ignored as redundant (same allowlisted op) |
| `scope=all` / `scope=active` | Legacy alias; same as default all-active |

Acknowledgement / “ok” / “OPTION A” is **not** `GO`.

## Leftover delete gate (unchanged safety — never weaken)

A name may be deleted **only** when **all** are true:

1. Active path `changes/<name>/` exists.
2. At least one `changes/archive/*-<name>/` exists (same logical name).
3. Required active artifacts empty/corrupt: `proposal.md` and/or `design.md`
   missing, size 0, or whitespace-only (no meaningful markdown).

If archive sibling is missing → FINDING only (`CORRUPT_OR_EMPTY_…` or warn);
**never** delete. Healthy / non-empty live changes are never deleted.

## Modes

### CHECK (default) — READ_ONLY

1. Run `openspec doctor --json` (surface healthy yes/no).
2. Resolve `planningHome.changesDir`.
3. Scan each active change dir (or only `change=<name>` if set):
   - empty/missing required proposal/design → finding;
   - archive sibling + empty/corrupt → `CORRUPT_LEFTOVER_ACTIVE_CHANGE`.
4. Emit report. **Do not write files.**

### GO — heal qualifying leftovers

1. Exact token `GO` required.
2. Re-run the same scan scope (all active, or `change=<name>` if set).
3. List targets that pass the leftover delete gate **before** deleting.
4. For each target: unstage that `changeRoot` if staged; delete **only** that
   active directory.
5. Do **not** touch `archive/`, `openspec/specs/`, `openspec/decisions/`, or
   other changes.
6. Report `REPAIRED` and `SKIPPED` (name + reason). If `GO` but zero
   qualifying targets → `STATUS=HEALTHY` or `FINDINGS` (non-deletable only);
   not a failed gate.

Internal op name remains `remove_corrupt_leftover` (one allowlisted action).
Owners need not type `repair=`.

## FINDING kinds

| KIND | Meaning |
|------|---------|
| `OPENSPEC_DOCTOR_UNHEALTHY` | `openspec doctor` non-healthy |
| `CORRUPT_OR_EMPTY_PLANNING_ARTIFACTS` | Empty/missing required artifacts (no safe delete without archive sibling) |
| `CORRUPT_LEFTOVER_ACTIVE_CHANGE` | Ghost active + archive sibling → GO may delete |

## Output

```text
STATUS: HEALTHY | FINDINGS | REPAIRED | BLOCKED
MODE: CHECK | GO

OPENSPEC_DOCTOR:
- healthy: yes | no
- summary: ...

FINDINGS:
- KIND: ...
  PATH: ...
  SEVERITY: warn | block
  EVIDENCE: ...
  NEXT: ...

TARGETS_FOR_GO: none | list (CHECK may preview)
REPAIRED: none | list of deleted changeRoots
SKIPPED: none | name + reason
OUTSIDE_ALLOWLIST: none

STAGE_COMMIT_PUSH: not_performed
NEXT_ACTION:
- /opsx-doctor GO   (when leftovers remain)
- none
DO_NOT_DO_YET:
- /opsx-apply on leftover names
- invent proposal/design to “heal” a ghost
```

For `CORRUPT_LEFTOVER_ACTIVE_CHANGE`, `NEXT` MUST be:

```text
/opsx-doctor GO
```

(or `/opsx-doctor GO change=<name>` when focused). Not `/opsx-apply`.

## Pipeline position

```text
ENTRY_STATE: anytime (post-archive soft next | suspicious list | pre-commit)
COMMAND_ACTION: hygiene scan; optional GO delete of qualifying leftovers
EXIT_STATE: hygiene_ok | hygiene_findings | leftover_removed
NEXT_ALLOWED_STEP: none | /opsx-doctor GO | re-CHECK
FAILURE_OR_RECOVERY_STEP: BLOCKED only if GO attempted outside allowlist rules
```

## Authority

* Does not re-decide `/opsx-verify` GO/NO_GO.
* Does not bypass archive sync / decision promotion.
* Repair owner: operator via exact `GO`.
* Archive owns `mv` + sync; doctor owns leftover GC only.

## Guardrails

* Default READ_ONLY; writes only with exact `GO`.
* Delete gate must stay: archive sibling + empty/corrupt required artifacts.
* Never delete archive / main specs / decisions.
* Never create or fill proposal/design.
* Do not stage, commit, or push.

## Self-check

- [ ] Default / CHECK never deleted paths
- [ ] `/opsx-doctor GO` heals all qualifying leftovers (not BLOCKED for missing repair=)
- [ ] Per-name gate still requires archive sibling + empty/corrupt artifacts
- [ ] FINDINGS next points at `/opsx-doctor GO`, not apply
- [ ] `openspec doctor` surfaced in report
