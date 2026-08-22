# PLANNING_REVIEW

Canonical contract for `/opsx-planning-review`.

```text
CONTRACT_ID: PLANNING_REVIEW
MODE: READ_ONLY
AUTHORITY: verification only
APPLIES_TO: finished OpenSpec planning package before /opsx-apply
```

Thin command / skill / prompt mirrors MUST defer to this file. Do not
duplicate full pillar logic in three places.

---

## Purpose

Answer exactly one question:

```text
Are Owner semantics → decisions → design → spec →
scenario coverage → tasks coherent enough that implementation
can execute the plan without making new semantic/architecture decisions?
```

Core invariant:

```text
PLANNING_READY
MUST NOT be self-attested by artifact writers alone.
```

Self-declarations such as:

```text
DESIGN_STATUS: READY
TASKS_STATUS: READY
NORMATIVE_MODALITY_PRESERVED: yes
```

are **evidence**, not authority. Reviewer MUST compare declaration to
artifact body.

PASS means only:

```text
planning package coherent enough for apply/preflight
```

PASS does **not** mean implementation success, Product Acceptance PASS,
or scenario certify PASS.

---

## What this is / is not

### Is

* Independent READ_ONLY verifier of the **whole** planning package.
* Soft recommended gate before `/opsx-apply` (v1; hard gate = separate
  Owner decision / companion fix).
* Producer of `PLANNING_REVIEW_RESULT` + findings + (when needed)
  `PLANNING_REVIEW_HANDOFF` for `/opsx-update`.
* Classifier of inconsistency; identifier of `FIRST_BAD_ARTIFACT`.

### Is not

* Writer / repairer of any planning artifact.
* `/opsx-owner-contract-review` (Owner Contract only, earlier hop).
* `/opsx-spec-scenario-coverage` (scenario plan/audit/certify).
* Product Acceptance itself.
* `/opsx-verify` (post-apply audit).
* Universal OPSX mega-reviewer.
* Authority that invents missing Owner / product semantics.

---

## Pipeline position (soft v1)

```text
owner-contract-review PASS
  → proposal → decisions → design → specs
  → scenario coverage plan (when required)
  → tasks
  → /opsx-planning-review   ← this contract
       ├─ PASS            → /opsx-apply (recommended)
       ├─ REPAIR_REQUIRED → PLANNING_REVIEW_HANDOFF → /opsx-update
       │                    → re-run /opsx-planning-review
       ├─ NEEDS_OWNER     → one precise Owner question; no silent invent
       └─ BLOCKED         → supply missing evidence; re-run
```

Writers (`/opsx-new`, `/opsx-continue`, `/opsx-ff`, `/opsx-update`) remain
necessary self-validators; they are insufficient alone.

---

## Authority model

| Layer | Authority |
|-------|-----------|
| Owner Contract | WHAT / WHY / SCOPE / ACCEPTANCE / OWNER_DECIDED semantics |
| Decisions / Design | technical architecture, SoT, ownership, write boundary, recovery, derived lifecycle — within Owner semantics |
| Spec | formal observable behavior / requirements |
| Scenario coverage | required behavioral/evidence coverage (no product decision authority) |
| Tasks | implementation decomposition only |
| Planning review | verification only |

Tasks MUST NOT choose SoT/ownership, change product semantics, or weaken
`MUST` / `MUST NOT`.

Reviewer:

```text
MAY classify inconsistency
MAY identify first bad artifact
MAY prescribe required semantic repair (known upstream meaning)
MUST NOT invent missing semantics
MUST NOT mutate artifacts
MUST NOT call /opsx-update itself
```

---

## Inputs

Primary CLI:

```text
/opsx-planning-review change=<change-id>
```

Resolve change via normal OPSX rules when unambiguous; never silently pick
among multiple active Changes.

Read when present under `openspec/changes/<change>/`:

```text
owner-contract.md
proposal.md
decisions/**/*.md
design.md
specs/**/*.md
tasks.md
SCENARIO_COVERAGE_PLAN / durable scenario-plan evidence:
  openspec/changes/<change>/scenario-coverage/plan.md
  openspec/changes/<change>/scenario-coverage/plan.receipt.json
Evolution/Explore linkage when required by other contracts
```

Also read cited process contracts as needed (bounded):

```text
.cursor/pipeline/contracts/DESIGN_GENERATION.md
.cursor/pipeline/contracts/TASK_GENERATION.md
.cursor/pipeline/contracts/PRODUCT_ACCEPTANCE.md
.cursor/pipeline/contracts/SCENARIO_TEST_COVERAGE.md
.cursor/pipeline/contracts/SEMANTIC_WRITE_TARGET.md
openspec/decisions/** (accepted; context-first only)
```

Chat history is **not** semantic authority when meaning must already be
durable in artifacts.

I/O: follow `opsx-source-resolution` + `opsx-execution-preflight`
(Grep-first; parallel Read ≤ 2; section reads for large files).

---

## Hard rules

* `MODE: READ_ONLY` end-to-end. Any file mutation = command failure.
* `FILES_CHANGED: none` on every terminal status.
* Do not auto-repair; do not expand scope; do not run production code/tests
  as part of review.
* Do not trust READY / NORMATIVE_MODALITY_PRESERVED markers without body check.
* Do not absorb scenario coverage, Owner Contract review, or PA into one
  mega-command.
* Prefer Owner UI/product terms; internal ids only as gloss.
* Idempotent: same unchanged package ⇒ same status, findings, first-bad
  (ignore irrelevant timestamps/order).

---

## Status model

Exactly one terminal `STATUS`:

| STATUS | When |
|--------|------|
| `PASS` | All applicable blocking pillars PASS; no blocking findings |
| `REPAIR_REQUIRED` | Authoritative semantics known; package incoherent; update can repair |
| `NEEDS_OWNER` | Real unresolved Owner product choice (WHAT/SCOPE/ACCEPTANCE/transition) |
| `BLOCKED` | Cannot complete review: missing mandatory artifact/evidence or stale/inapplicable input |

Aliases / routing:

```text
missing mandatory evidence     → BLOCKED (not FAIL-as-PASS)
proven writer drift            → REPAIR_REQUIRED (OWNER_INPUT_REQUIRED: NO)
unresolved product fork        → NEEDS_OWNER (OWNER_INPUT_REQUIRED: YES)
```

`APPLY_PLANNING_GATE: PASS` only when `STATUS: PASS`.

---

## Review pillars (P1–P8)

Each pillar: `PASS` | `FAIL` | `NOT_APPLICABLE`.

### P1 — SEMANTIC_CONTINUITY

Chain Owner Contract → decisions → design → spec → tasks preserves
WHAT / SCOPE / ACCEPTANCE.

Detect: dropped Owner requirement; new product semantics without Owner
authority; changed meaning of existing requirement; scope expansion;
scope omission that changes acceptance.

Failure type: `SEMANTIC_DRIFT`

### P2 — NORMATIVE_PRESERVATION

End-to-end modality:

```text
MUST / MUST NOT / MAY
```

Forbidden weakenings:

```text
MUST → MAY
MUST → SHOULD
MUST NOT → SHOULD NOT
```

Also check conditional semantics (e.g. IF no blockers → MUST start must
not become bare MAY start when upstream requires obligation under the
same condition).

Failure type: `NORMATIVE_DRIFT`

### P3 — DESIGN_READINESS

Do not trust `DESIGN_STATUS: READY` alone. Body must resolve:

```text
PRODUCT_SEMANTICS_RESOLVED
STATE_OWNERSHIP_RESOLVED
DURABLE_SOT_RESOLVED
WRITE_AUTHORITY_RESOLVED
RECOVERY_SEMANTICS_RESOLVED
IMPLEMENTATION_CRITICAL_OPEN_QUESTIONS: none
```

Example FAIL: READY + «PG or Redis — choose during apply».

Failure type: `DESIGN_READINESS_GAP`

### P4 — AUTHORITY_AND_SOT

For stateful/write Changes, require coherent:

```text
canonical SoT, writer, reader, derived/mirror, reconciliation,
restart recovery, write target
```

Detect: two implicit SoTs; mirror as authority; hidden write authority;
architecture deferred to apply.

Failure type: `AUTHORITY_OR_SOT_GAP`  
`NOT_APPLICABLE` when Change is non-stateful / no durable write path.

### P5 — LIFECYCLE_COMPLETENESS

For temporal/stateful Changes, require minimally sufficient lifecycle
(entry/gate, transition, write/effect, steady, clear/recovery,
terminal/next) — not an artificial step count. Design lifecycle must
agree with Owner Contract / spec.

Failure type: `LIFECYCLE_GAP`  
If product transition itself is unresolved (not missing planning
representation): `UNRESOLVED_PRODUCT_SEMANTICS` → usually `NEEDS_OWNER`.  
`NOT_APPLICABLE` when non-temporal.

### P6 — SPEC_COVERAGE

Do **not** rebuild scenario coverage. Do **not** require Owner/user to paste
chat `SCENARIO_COVERAGE_PLAN` when durable evidence exists. Do **not** treat
`tasks.md` `SCENARIO_REQUIREMENTS_CONSUMED: yes` as authority.

When scenario plan is required for the Change:

1. Locate canonical pair:
   `openspec/changes/<change>/scenario-coverage/plan.md`
   `openspec/changes/<change>/scenario-coverage/plan.receipt.json`
2. Missing → `STATUS: BLOCKED` (or REPAIR path as applicable), type
   `SPEC_COVERAGE_EVIDENCE_MISSING` (prefer over vague `SPEC_COVERAGE_GAP`
   when the gap is absent durable evidence).
3. Validate `PLAN_CONTENT_HASH` vs `plan.md` → mismatch →
   `EVIDENCE_INTEGRITY_FAIL`.
4. Validate receipt `INPUTS.*` hashes vs current design/specs → mismatch →
   `STALE_DERIVED_ARTIFACT` (scenario-plan evidence STALE).
5. Validate `PLAN_STATUS` (ready/provisional/blocked) and consume human plan /
   receipt coverage for unresolved material gaps and lifecycle representation.
6. PASS only when evidence is CURRENT, integrity-ok, and coverage coherent.

If specialized command returned durable `PLAN_STATUS: ready` with CURRENT
receipt, verify applicability/coherence only — do not rebuild the matrix.

Failure types: `SPEC_COVERAGE_GAP` | `SPEC_COVERAGE_EVIDENCE_MISSING` |
`STALE_DERIVED_ARTIFACT` | `EVIDENCE_INTEGRITY_FAIL`  
`NOT_APPLICABLE` when scenario plan not required for this Change.

### P7 — TASK_DECOMPOSITION

Tasks vs design/spec/scenario plan. Tasks MUST NOT:

* choose SoT / ownership / product decision;
* weaken MUST / MUST NOT;
* drop conditional branches;
* skip required evidence;
* treat legacy baseline as final target.

Check evidence roles when present:

```text
LEGACY_BASELINE | TARGET_REGRESSION | FINAL_ACCEPTANCE
```

Failure types: `TASK_DECOMPOSITION_GAP` and/or `NORMATIVE_DRIFT`

### P8 — SCOPE_CONTINUITY

`IN_SCOPE` / `OUT_OF_SCOPE` / FORWARD_COMPATIBILITY / accepted decisions
vs downstream artifacts/tasks.

Failure type: `SCOPE_DRIFT`

### Cross-cutting — STALE_DERIVED_ARTIFACT

If upstream changed after downstream generation (hash/version evidence
when available, else semantic mismatch vs current upstream), classify
`STALE_DERIVED_ARTIFACT`. Do not invent a heavyweight provenance DB.

---

## Finding model

Each finding:

```text
FINDING_ID: P-NNN
TYPE: SEMANTIC_DRIFT | NORMATIVE_DRIFT | UNRESOLVED_PRODUCT_SEMANTICS |
      DESIGN_READINESS_GAP | AUTHORITY_OR_SOT_GAP | LIFECYCLE_GAP |
      SPEC_COVERAGE_GAP | SPEC_COVERAGE_EVIDENCE_MISSING |
      EVIDENCE_INTEGRITY_FAIL | TASK_DECOMPOSITION_GAP | SCOPE_DRIFT |
      STALE_DERIVED_ARTIFACT
SEVERITY: BLOCKING | HIGH | MEDIUM | LOW

AUTHORITATIVE_SOURCE:
EXPECTED_SEMANTICS:
FIRST_BAD_ARTIFACT:
BAD_EVIDENCE:
AFFECTED_DOWNSTREAM:
OWNER_INPUT_REQUIRED: YES | NO
REPAIR_OWNER: /opsx-update | OWNER | none
REPAIR_BOUNDARY:
DO_NOT_CHANGE:
```

Rules:

* `OWNER_INPUT_REQUIRED: NO` ⇒ no Owner quiz; emit repair handoff when
  status is `REPAIR_REQUIRED`.
* `OWNER_INPUT_REQUIRED: YES` ⇒ exactly one precise question; do not
  model-select semantics.
* Do not collapse all defects into generic «Coherence FAIL».

---

## First-bad-artifact algorithm

Distinguish **symptom** from **first bad artifact**.

Walk upstream → downstream:

```text
Owner Contract → decisions → design → spec → scenario plan → tasks
```

`FIRST_BAD_ARTIFACT` = earliest artifact where meaning/modality diverges
from authoritative upstream. Downstream copies are `AFFECTED_DOWNSTREAM`
only — repair MUST NOT start by manually patching the last symptom file
when upstream is wrong.

Example:

```text
Owner: MUST
Lifecycle: MUST
Design Decision: MAY
Tasks: MAY
→ FIRST_BAD_ARTIFACT: design.md
→ AFFECTED_DOWNSTREAM: tasks.md …
```

---

## PLANNING_REVIEW_RESULT (always)

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

On `PASS`, all applicable pillars PASS and `BLOCKING_FINDINGS: none`.

Human lead-ins (recommended):

* PASS — planning package coherent; may proceed to apply/preflight.
* REPAIR_REQUIRED — paste handoff into `/opsx-update` chat.
* NEEDS_OWNER — answer the single question; continue same cycle.
* BLOCKED — supply the named missing evidence.

Footer mandatory:

```text
MODE: READ_ONLY
FILES_CHANGED: none
```

---

## PLANNING_REVIEW_HANDOFF (REPAIR_REQUIRED)

Self-contained pasteable block. Owner copies into writer chat unchanged.

```text
/opsx-update

PLANNING_REVIEW_HANDOFF

CHANGE_ID: <change>
TARGET_WRITER: /opsx-update
MODE: REPAIR_PLANNING_PACKAGE

REVIEW_STATUS: REPAIR_REQUIRED

AUTHORITATIVE_SOURCES:
- <paths / sections>

FINDINGS:

P-001:
TYPE:
FIRST_BAD_ARTIFACT:
EXPECTED_SEMANTICS:
BAD_EVIDENCE:
AFFECTED_DOWNSTREAM:
OWNER_INPUT_REQUIRED: NO
REPAIR_REQUIRED:
<exact repair semantics>

DO_NOT_CHANGE:
- Owner Contract (unless finding explicitly requires Owner-contract repair
  via /opsx-owner-contract-review + /opsx-new — out of this handoff)
- unaffected upstream
- unrelated scenario semantics
- production code

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

Expected `/opsx-update` algorithm (companion; may be incomplete until
external fix):

```text
validate handoff
→ repair FIRST_BAD_ARTIFACT
→ identify stale downstream
→ repair/regenerate only affected downstream
→ do not modify unaffected upstream
→ stop
→ Owner re-runs /opsx-planning-review
```

If update cannot safely repair the dependency chain, report as a
**separate command defect** (`/opsx-meta-fix-command-defects`) — do not
silently broaden planning-review into update implementation.

---

## Product Acceptance / scenario interaction

```text
planning-review  → planning coherence
Product Acceptance → product acceptance/evidence conditions
scenario coverage → behavioral scenario evidence requirements
```

For PA-required Changes, planning-review checks that required PA/scenario
**planning** prerequisites are present and coherent — it does not certify
PA or replace `/opsx-spec-scenario-coverage`.

---

## Acceptance fixtures

Process-only cases live under:

```text
.cursor/commands/_fixtures/planning-review/
```

T1–T12 (clean PASS; MUST→MAY design; tasks-only drift; unresolved SoT;
genuine Owner ambiguity; scenario gap; scope drift; stale tasks;
self-attestation false; READ_ONLY; idempotency; repair loop) are binding
for command behavior.

Live change dry-runs (e.g. `auto-shelf-exhausted-pause-retest`) are
evidence, not a substitute for fixtures. Compare actual Owner modality
before asserting `NORMATIVE_DRIFT`.

---

## Regression checklist (implementer / auditor)

- [ ] READY markers not trusted without body check
- [ ] First-bad ≠ last symptom
- [ ] FILES_CHANGED always none
- [ ] Handoff self-contained for `/opsx-update`
- [ ] No absorption of OCR / scenario / PA / verify
- [ ] Soft gate only in v1 unless Owner hardens companions
- [ ] Idempotent findings on unchanged package
