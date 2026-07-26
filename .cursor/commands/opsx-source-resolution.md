---
description: "Shared OPSX source-resolution and bounded-search contract. Not a standalone user command; referenced by opsx-* command contracts."
---

# OPSX Source Resolution Contract

Shared mandatory contract for OPSX commands that resolve artifacts by exact path or stable ID.

This file is **not** a user-facing `/opsx-*` workflow command.
Any OPSX command that references it MUST follow it before broad repository exploration.

Companion contract: `.cursor/commands/opsx-execution-preflight.md` (purpose-driven shell/git budgets).
This file covers **artifact resolution / rediscovery**, not execution hang risk.

## Resolution order

### A. DIRECT RESOLUTION

1. If an exact path is provided:
   - check existence with a direct filesystem/read check;
   - read that exact file;
   - do **not** rediscover it via `rg`, `find`, glob, Task/explore, or semantic search.

2. If a stable ID is provided (`CASE_ID`, `INTAKE_ID`, `FINDING_ID`, `CHANGE_ID`, result id, packet path, receipt `OUTPUT_PATH`):
   - compute the deterministic canonical path first;
   - then use INDEX / ledger / receipt / packet fields if they are the approved source;
   - only after unsuccessful direct resolution may fallback search run.

3. If an already-read artifact contains explicit references to next sources:
   - read only those referenced sources;
   - do not widen scope without a recorded evidence gap.

### Canonical bug-case paths

```text
.tmp/opsx-bug-cases/INDEX.md
.tmp/opsx-bug-cases/<CASE_ID>/CASE.md
.tmp/opsx-bug-cases/<CASE_ID>/LEDGER.md
.tmp/opsx-bug-cases/<CASE_ID>/intakes/<INTAKE_ID>.md
.tmp/opsx-bug-cases/<CASE_ID>/findings/<FINDING_ID>.md
.tmp/opsx-bug-cases/<CASE_ID>/results/<RESULT_ID>.md
.tmp/opsx-bug-cases/<CASE_ID>/handoffs/COMMON_HANDOFF.md
```

### Canonical OpenSpec change paths

```text
openspec/changes/<CHANGE_ID>/proposal.md
openspec/changes/<CHANGE_ID>/design.md
openspec/changes/<CHANGE_ID>/tasks.md
openspec/changes/<CHANGE_ID>/specs/
openspec/changes/<CHANGE_ID>/decisions/
```

## B. BOUNDED FALLBACK SEARCH

Fallback search is allowed only when one of these is true:

- direct path missing;
- canonical path does not exist;
- ID is ambiguous;
- referenced source is missing;
- an authoritative source is required and its path was never saved.

Before any fallback search, define internally:

```text
SEARCH_REASON:
SEARCH_TARGET:
SEARCH_ROOT:
SEARCH_BUDGET:
```

Base budget:

- at most **3** targeted search operations per unresolved target;
- search only relevant roots;
- order: exact filename/ID → exact symbol/reference → stop;
- broad semantic / Task-explore / “search the whole repo for the same artifact” is forbidden without an explicit evidence gap.

If budget is exhausted, stop and return a blocker compatible with the command vocabulary, preferably:

```text
RESULT: blocked_needs_exact_source
```

or the command’s existing equivalent (`blocked`, `needs_input`, `NO_GO` with missing-source reason).

Include:

- what was found;
- what is missing;
- which exact path or extraction is needed;
- what the user/operator should return next.

Do **not** invent a second global status taxonomy when the command already has a blocker form.

## C. NO RE-DISCOVERY

Forbidden when the durable path/id is already known:

- repo-wide search for a finding when `FINDING_PATH` / `case+finding` canonical path exists;
- repo-wide search for an intake when `INTAKE_PATH` / `case+intake` exists;
- repo-wide search for a result when receipt `OUTPUT_PATH` exists;
- rebuild of entrypoint inventory when a confirmed fresh inventory was already supplied to the command;
- full OpenSpec change tree listing when only one exact decision/spec/proposal section is required;
- repeating the same search without a new `SEARCH_TARGET`.

## D. EXPLORATION EXPANSION GATE

Scope expansion is allowed only with an explicit:

```text
EVIDENCE_GAP
```

or an equivalent confirmed reason already required by the command.

Before expanding, state:

- which question is still open;
- why direct sources are insufficient;
- which additional roots will be inspected;
- which maximum search budget applies.

Never use unbounded “continue exploring”.

## E. OUTPUT fragment

Affected commands MUST include this in terminal output (or embed equivalent fields in an existing receipt):

```text
SOURCE_RESOLUTION:
- mode: exact_path | canonical_id | referenced_source | bounded_fallback
- primary_path:
- fallback_used: true | false
- search_operations:
- search_scope:
- unresolved_gap:
```

## Hard rules

* Exact path or stable ID wins over exploration.
* Fallback is exceptional, bounded, and explained.
* Exhausted budget → blocker, not more searching.
* No second storage layout and no second status system.
