---
description: "READ_ONLY independent review of a finished OpenSpec planning package before apply: Owner→decisions→design→spec→scenario→tasks coherence; PLANNING_REVIEW_HANDOFF for /opsx-update. Never writes."
argument-hint: "change=<name> [paste PLANNING_REVIEW_HANDOFF for re-review]"
---

# /opsx-planning-review

Независимый **READ_ONLY** verifier готового planning package Change перед
`/opsx-apply`.

Capability: `planning-review`.

**Canonical SoT:** `.cursor/pipeline/contracts/PLANNING_REVIEW.md`  
This command file is a thin operational mirror. Prefer the contract for
pillar definitions, finding schema, and handoff field names.

Единственный вопрос:

> Согласованы ли Owner semantics → decisions → design → spec →
> scenario coverage → tasks настолько, чтобы implementation мог
> исполнять план, не принимая новых semantic/architecture решений?

## Core invariant

```text
PLANNING_READY
MUST NOT be self-attested by artifact writers alone.
```

```text
DESIGN_STATUS: READY
TASKS_STATUS: READY
NORMATIVE_MODALITY_PRESERVED: yes
```

are evidence, not authority — always check artifact bodies.

## What this is

* Independent package reviewer (prefer separate chat from writers).
* Soft recommended gate before `/opsx-apply` (v1).
* Producer of `PLANNING_REVIEW_RESULT` + findings + (when needed)
  `PLANNING_REVIEW_HANDOFF` for `/opsx-update`.
* Classifier only: may name `FIRST_BAD_ARTIFACT` and required repair
  semantics when upstream meaning is already known.

## What this is NOT

* NOT a writer of design/spec/tasks/decisions/owner-contract.
* NOT `/opsx-owner-contract-review` (Owner Contract only, earlier hop).
* NOT `/opsx-spec-scenario-coverage` / Product Acceptance / `/opsx-verify`.
* NOT an automatic repair agent (must not call `/opsx-update` itself).
* NOT a universal OPSX mega-reviewer.
* NOT implementation success certification.

## Hard rules

* **READ_ONLY** end-to-end. Any mutation = command failure.
* Always emit `FILES_CHANGED: none`.
* Do not invent Owner/product semantics.
* Do not trust READY markers without body check.
* Do not rebuild scenario coverage; consume plan status/coherence only.
* Follow `.cursor/commands/opsx-source-resolution.md` and
  `.cursor/commands/opsx-execution-preflight.md` (Grep-first; parallel
  Read ≤ 2; no broad archaeology).

## User input

```text
$ARGUMENTS
```

| Token | Effect |
|-------|--------|
| `change=<name>` | review `openspec/changes/<name>/` planning package |
| pasted `PLANNING_REVIEW_HANDOFF` | re-review after claimed repair |
| unknown token | `STATUS=BLOCKED`, no file changes |

If `change=` absent and no single unambiguous active change → ask one
concrete question; do not invent the change id.

## Pipeline position (soft v1)

```text
owner-contract-review PASS
  → proposal → decisions → design → specs
  → scenario coverage plan (when required)
  → tasks
  → /opsx-planning-review
       ├─ PASS → /opsx-apply (recommended)
       ├─ REPAIR_REQUIRED → PLANNING_REVIEW_HANDOFF → /opsx-update
       │                    → /opsx-planning-review
       ├─ NEEDS_OWNER → one Owner question; continue same cycle
       └─ BLOCKED → supply missing evidence; re-run
```

Authority:

```text
Owner Contract / Owner     → product semantics
decisions / design         → architecture within Owner semantics
spec / scenario / tasks    → behavior / coverage / decomposition
opsx-planning-review       → verification + repair handoff only
opsx-update                → sole writer for planning-package repair
```

## Required read set

Minimum when present:

```text
openspec/changes/<change>/owner-contract.md
openspec/changes/<change>/proposal.md
openspec/changes/<change>/decisions/**/*.md
openspec/changes/<change>/design.md
openspec/changes/<change>/specs/**/*.md
openspec/changes/<change>/tasks.md
scenario coverage plan / durable plan evidence (when required):
  openspec/changes/<change>/scenario-coverage/plan.md
  openspec/changes/<change>/scenario-coverage/plan.receipt.json
```

Bounded contracts:

```text
.cursor/pipeline/contracts/PLANNING_REVIEW.md   (this capability)
.cursor/pipeline/contracts/DESIGN_GENERATION.md
.cursor/pipeline/contracts/TASK_GENERATION.md
.cursor/pipeline/contracts/PRODUCT_ACCEPTANCE.md
.cursor/pipeline/contracts/SEMANTIC_WRITE_TARGET.md
.cursor/pipeline/contracts/SCENARIO_TEST_COVERAGE.md
```

When `PRODUCT_ACCEPTANCE_REQUIRED=true` and SWT applicability holds
(high-risk multi-target write): FAIL / `REPAIR_REQUIRED` if durable
artifacts lack the **exact** SWT schema tokens `TARGET_ENTITY_OR_LEG`,
`ALLOWED_ADAPTERS`, `FORBIDDEN_ADAPTERS` — even when decision
Allowed/Forbidden prose or design Ownership tables look complete
(`prose≠RESOLVED` / MEANING_LOCK). Handoff primary writer:
`/opsx-update` (not scenario-coverage).

Fixtures: `.cursor/commands/_fixtures/planning-review/`

## Review flow

```text
START
  ↓
resolve change=
  ↓
required artifacts present for applicable pillars?
  ├─ NO → STATUS: BLOCKED (name missing evidence)
  └─ YES
  ↓
run pillars P1–P8 (+ stale-derived cross-check)
  ↓
any OWNER_INPUT_REQUIRED: YES unresolved?
  ├─ YES → STATUS: NEEDS_OWNER (one precise question)
  └─ NO
  ↓
any BLOCKING finding?
  ├─ YES → STATUS: REPAIR_REQUIRED + PLANNING_REVIEW_HANDOFF
  └─ NO  → STATUS: PASS + APPLY_PLANNING_GATE: PASS
```

Never ask Owner to reconfirm semantics already proven by durable
upstream — those are writer repairs (`OWNER_INPUT_REQUIRED: NO`).

## Pillars (summary)

Full definitions: `PLANNING_REVIEW.md`.

| ID | Name | Typical FAIL type |
|----|------|-------------------|
| P1 | SEMANTIC_CONTINUITY | SEMANTIC_DRIFT |
| P2 | NORMATIVE_PRESERVATION | NORMATIVE_DRIFT |
| P3 | DESIGN_READINESS | DESIGN_READINESS_GAP |
| P4 | AUTHORITY_AND_SOT | AUTHORITY_OR_SOT_GAP |
| P5 | LIFECYCLE_COMPLETENESS | LIFECYCLE_GAP / UNRESOLVED_PRODUCT_SEMANTICS |
| P6 | SPEC_COVERAGE | SPEC_COVERAGE_GAP / SPEC_COVERAGE_EVIDENCE_MISSING / STALE_DERIVED_ARTIFACT / EVIDENCE_INTEGRITY_FAIL |
| P7 | TASK_DECOMPOSITION | TASK_DECOMPOSITION_GAP |
| P8 | SCOPE_CONTINUITY | SCOPE_DRIFT |

Cross-cutting: `STALE_DERIVED_ARTIFACT`.

### First-bad-artifact

Walk Owner → decisions → design → spec → scenario → tasks. Earliest
divergence from authoritative upstream = `FIRST_BAD_ARTIFACT`. Downstream
echoes = `AFFECTED_DOWNSTREAM` only.

## Status model

```text
PASS | REPAIR_REQUIRED | NEEDS_OWNER | BLOCKED
```

`APPLY_PLANNING_GATE: PASS` only with `STATUS: PASS`.

## Findings

Each finding MUST include fields from the contract:

```text
FINDING_ID, TYPE, SEVERITY, AUTHORITATIVE_SOURCE, EXPECTED_SEMANTICS,
FIRST_BAD_ARTIFACT, BAD_EVIDENCE, AFFECTED_DOWNSTREAM,
OWNER_INPUT_REQUIRED, REPAIR_OWNER, REPAIR_BOUNDARY, DO_NOT_CHANGE
```

## Output contract

### 1) Human lead-in

* PASS — package coherent for apply/preflight.
* REPAIR_REQUIRED — copy handoff into `/opsx-update` chat.
* NEEDS_OWNER — one question; continue this cycle.
* BLOCKED — named missing evidence.

### 2) Machine block

```text
PLANNING_REVIEW_RESULT

CHANGE_ID: <change>
MODE: READ_ONLY
STATUS: PASS | REPAIR_REQUIRED | NEEDS_OWNER | BLOCKED

SEMANTIC_CONTINUITY: PASS|FAIL
NORMATIVE_PRESERVATION: PASS|FAIL
DESIGN_READINESS: PASS|FAIL
AUTHORITY_AND_SOT: PASS|FAIL|NOT_APPLICABLE
LIFECYCLE_COMPLETENESS: PASS|FAIL|NOT_APPLICABLE
SPEC_COVERAGE: PASS|FAIL|NOT_APPLICABLE
TASK_DECOMPOSITION: PASS|FAIL
SCOPE_CONTINUITY: PASS|FAIL

BLOCKING_FINDINGS: none | <ids>
FILES_CHANGED: none

APPLY_PLANNING_GATE: PASS | FAIL
```

### 3) Findings (when any)

### 4) PLANNING_REVIEW_HANDOFF

Required when `STATUS: REPAIR_REQUIRED`. Literal shared shape with
`/opsx-update` `MODE: REPAIR_PLANNING_PACKAGE` (companion may lag —
still emit the handoff).

```text
/opsx-update

PLANNING_REVIEW_HANDOFF

CHANGE_ID: <change>
TARGET_WRITER: /opsx-update
MODE: REPAIR_PLANNING_PACKAGE

REVIEW_STATUS: REPAIR_REQUIRED

AUTHORITATIVE_SOURCES:
...

FINDINGS:

P-001:
TYPE:
FIRST_BAD_ARTIFACT:
EXPECTED_SEMANTICS:
BAD_EVIDENCE:
AFFECTED_DOWNSTREAM:
OWNER_INPUT_REQUIRED: NO
REPAIR_REQUIRED:
...

DO_NOT_CHANGE:
...

WRITE_BOUNDARY:
only artifacts necessary to repair findings and their stale downstream
derivatives

FORBIDDEN:
- new product decisions
- scope expansion
- production code
- apply
- Owner Contract edits unless finding explicitly requires that path

AFTER_REPAIR:
/opsx-planning-review change=<change>
```

### 5) Footer (mandatory)

```text
MODE: READ_ONLY
FILES_CHANGED: none
```

### 6) Next action

```text
NEXT_ACTION:
  PASS             → /opsx-apply (recommended soft gate)
  REPAIR_REQUIRED  → paste /opsx-update + PLANNING_REVIEW_HANDOFF; then AFTER_REPAIR
  NEEDS_OWNER      → answer OWNER_QUESTION; continue same review cycle
  BLOCKED          → supply named evidence; re-invoke
```

## Do NOT

* mutate artifacts or run apply/production tests as “proof”
* replace scenario coverage / OCR / PA / verify
* require Owner confirmation for derived technical corrections when
  upstream semantics already prove the repair
* grant APPLY_PLANNING_GATE: PASS on summary/self-report alone
* create a new Change artifact as part of review

## Checklist before return

- [ ] Contract `PLANNING_REVIEW.md` followed
- [ ] Bodies checked vs READY markers
- [ ] First-bad distinguished from symptoms
- [ ] FILES_CHANGED: none
- [ ] Handoff present iff REPAIR_REQUIRED
- [ ] No invented product semantics
