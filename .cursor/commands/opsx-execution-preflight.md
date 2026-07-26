---
description: "Shared OPSX execution-preflight contract: purpose-driven, bounded, timeout-safe shell/tool ops. Not a standalone user command."
---

# OPSX Execution Preflight Contract

Shared mandatory contract for shell/tool operations that OPSX commands run before or beside their main work.

This file is **not** a user-facing `/opsx-*` workflow command.
Any OPSX command that references it MUST follow it for git/status/diff/find/rg/test-discovery and similar preflight operations.

Companion contract: `.cursor/commands/opsx-source-resolution.md` (artifact resolution).
This contract covers **execution cost / hang risk**, not path rediscovery.

## Goal

Prevent hangs on unconditional preflight shells when those results are not required for the current command decision.

Do **not** delete necessary checks.
Make every operation purpose-driven, bounded, timeout-safe, and skippable when irrelevant.

## Hard principle

Never run an operation only because it traditionally appears in a preflight checklist.

Before every shell/tool operation, the command MUST be able to fill:

```text
OPERATION_REASON:
REQUIRED_FOR:
SKIP_IF:
TIME_BUDGET:
FAILURE_BEHAVIOR:
```

If `REQUIRED_FOR` is empty or not needed for the current decision, **skip** the operation.

## Default time budgets

| Operation class | Default TIME_BUDGET | Notes |
|---|---|---|
| `git branch --show-current` | 5s | local metadata |
| `git status --short` | 10s | can hang on huge/dirty trees or locks |
| `git diff` / `git diff --stat` (unstaged/staged) | 15s | defer until staging/commit/PR decision |
| `git rev-parse` / short `git log` | 10s | required only when refs matter |
| `git fetch` / remote checks | 30s | never for read-only classify |
| `rg` / targeted search | per source-resolution budget | not a default preflight |
| `find` inventories | forbidden by default | fallback only with EVIDENCE_GAP |
| test discovery / pytest collect | defer until test command needs it | |

Commands MAY tighten these budgets; they MUST NOT remove budgets for optional ops.

## Failure / timeout behavior

When a preflight operation times out, hangs, or fails:

1. stop waiting;
2. do **not** retry the same op in a loop;
3. record:

```text
PREFLIGHT_RESULT:
- operation:
- status: skipped | ok | timeout | failed | deferred
- required_for_decision: true | false
```

4. if `required_for_decision=false` → continue the main command;
5. if `required_for_decision=true` → return a command-compatible blocker such as:

```text
RESULT: blocked_preflight_timeout
```

or existing `blocked` / `NO_GO` with the missing fact named.

Never block a read-only classification solely because optional git metadata was slow.

## Command-class defaults

### A. Read-only classification / routing
Examples: `/opsx-classify-bug`, read-only portions of `/opsx-fix-bug` without `GO`, `/opsx-fanout-bug-hunt` source ingest.

Default:

* resolve durable/exact sources first;
* **skip** `git status` / `git branch` / `git diff` unless the decision explicitly depends on dirty-tree or branch identity;
* output fields like `branch:` / `dirty files:` may be:

```text
deferred_not_required
```

### B. Adjudication / forensics with code evidence
Examples: `/opsx-fix-bug` forensics, `/opsx-invariant`, `/opsx-bug-hunt`.

Default:

* git metadata only when needed for `base`/`head`/dirty interaction with the claim;
* `rg` only after packet/source resolution and only for packet symbols;
* never run git status as step 0 before reading known case/finding.

### C. Git-mutating / PR / split / commit workflows
Examples: `/opsx-commit`, `/opsx-create-pr`, `/opsx-split-for-pr`.

Default:

* git status/diff/log **are** usually required for the decision;
* still apply TIME_BUDGET and FAILURE_BEHAVIOR;
* prefer the smallest git command that answers the required fact;
* `git fetch` only when remote freshness is REQUIRED_FOR the decision.

### D. OpenSpec lifecycle CLI workflows
Examples: `/opsx-apply`, `/opsx-verify`, `/opsx-sync`, `/opsx-continue`.

Default:

* prefer `openspec ... --change "<name>"` over git preflight;
* git only when dirty-tree or branch identity is REQUIRED_FOR apply/verify safety.

## Output fragment

Affected commands SHOULD include (or embed equivalently):

```text
EXECUTION_PREFLIGHT:
- git_branch: skipped | ok | timeout | failed | deferred_not_required
- git_status: skipped | ok | timeout | failed | deferred_not_required
- other_ops:
- blocked_on_preflight: true | false
```

## Hard rules

* No unconditional “always run git status first”.
* Optional preflight must not gate the main read-only decision.
* Timeout → continue or blocker by `required_for_decision`, never silent hang.
* Do not invent a second status taxonomy when the command already has blockers.
* Keep companion source-resolution rules for artifact rediscovery.
