# Product Acceptance (DONE authority)

## Purpose

OPSX **DONE** for product-impacting changes is **Product Acceptance**, not
process/artifact/tooling green.

This contract is the kernel authority that composes existing producers:

| Pillar | Producer / contract |
|---|---|
| MEANING_LOCK | `.cursor/pipeline/contracts/SEMANTIC_WRITE_TARGET.md` |
| LIFECYCLE_COVERAGE | `.cursor/pipeline/contracts/SCENARIO_TEST_COVERAGE.md` + `/opsx-spec-scenario-coverage` |
| SIDE_EFFECT_PROOF | `.cursor/pipeline/contracts/TEST_EVIDENCE_TAXONOMY.md` (+ testing-rules pointer) |

It is **not** a new user-facing command. Archive GO/NO_GO remains
`/opsx-verify` (`mode=archive`). Soft tooling gates (pyright, ECC, perf,
antipattern, static) are advisory relative to this contract and **cannot**
create DONE.

## Result tokens

```text
PRODUCT_ACCEPTANCE_REQUIRED: true | false

PRODUCT_ACCEPTANCE_STATUS:
  NOT_REQUIRED
  PASS
  FAIL
  BLOCKED

PRODUCT_ACCEPTANCE_FAIL_PILLAR:
  MEANING_LOCK | LIFECYCLE_COVERAGE | SIDE_EFFECT_PROOF | MULTI
```

## When required

Set `PRODUCT_ACCEPTANCE_REQUIRED=true` when **any** of:

1. `SEMANTIC_WRITE_TARGET` applicability holds (high-risk write with competing
   entities/legs/adapters), or status is
   `BLOCKED_NEEDS_OWNER_SEMANTIC_DECISION` / unresolved `RESOLVED` fields;
2. change is evolution-linked (`EVOLUTION_LINK` / STAR increment / handoff);
3. change plans a material user-visible lifecycle write (campaign pause/start,
   paid notify, billing charge, equivalent consequential UX/state);
4. change artifacts explicitly set `PRODUCT_ACCEPTANCE_REQUIRED=true` or
   `SCENARIO_COVERAGE_REQUIRED=true`.

Set `PRODUCT_ACCEPTANCE_REQUIRED=false` only for documented **NOT_REQUIRED**
classes: pure docs/process/chore with **no** product mutation and **no**
user-visible lifecycle write. Prefer an explicit durable note in change
artifacts when claiming NOT_REQUIRED.

## PASS criteria

When `PRODUCT_ACCEPTANCE_REQUIRED=true`,
`PRODUCT_ACCEPTANCE_STATUS=PASS` iff **all** pillars hold:

### 1) MEANING_LOCK

- `SEMANTIC_WRITE_TARGET_STATUS=RESOLVED` with durable fields in
  decision/spec/design/tasks, **or**
- justified `NOT_APPLICABLE` (single proven target; no competing legs).

**Anti-abuse:** if repository evidence shows ≥2 plausible concrete
legs/adapters and the choice materially changes traffic/money/state, then
`NOT_APPLICABLE` is **forbidden**. Missing Owner durable fields ⇒
`PRODUCT_ACCEPTANCE_STATUS=FAIL` pillar `MEANING_LOCK` (or `BLOCKED` while
awaiting Owner), not silent skip.

Chat-only Owner answers are not durable (see SEMANTIC_WRITE_TARGET).

### 2) LIFECYCLE_COVERAGE

When `PRODUCT_ACCEPTANCE_REQUIRED=true`, this pillar is **MEANING of time**
plus scenario evidence — not scenario machinery alone.

**Authority:**

```text
reviewed owner-contract.md  = semantic authority for the Change
Derived Lifecycle in design = planning representation (no new product authority)
DESIGN_GENERATION.md        = design readiness (SoT/ownership/write/recovery;
                              normative modality; no apply-time architecture)
scenario coverage           = LIFECYCLE ↔ SPEC SCENARIOS verifier
```

`DERIVED` may restructure already-authorized semantics in time; it MUST NOT
add product semantics. Silent “sensible lifecycle defaults” are forbidden.
Lifecycle DERIVED does **not** waive `.cursor/pipeline/contracts/DESIGN_GENERATION.md`.

**Primary path (reviewed Owner Contract present):**

1. Durable **Derived Lifecycle** in planning artifacts (prefer `design.md`
   `## Lifecycle` with `LIFECYCLE_STATUS: DERIVED` and per-step `SOURCE:`
   provenance from owner-contract / decisions / repository facts).
2. Step count is **not** fixed to 3–7 — minimal sequence sufficient for the
   Change. Non-temporal Changes need no ceremonial lifecycle.
3. **No second Owner confirmation** (`CONFIRM_LIFECYCLE`) when the lifecycle
   is uniquely determined by reviewed Owner Contract semantics.
4. Unresolved material A|B forks → `LIFECYCLE_STATUS: UNRESOLVED` /
   `UNRESOLVED_PRODUCT_SEMANTICS` → `/opsx-owner-contract-review`
   (not invent; not a parallel confirm contour).
5. When `design.md` exists or is being written/revised: satisfy
   `.cursor/pipeline/contracts/DESIGN_GENERATION.md` —
   `DESIGN_READINESS` must hold (`DESIGN_STATUS: READY` with SoT/ownership/
   write/recovery resolved or `not_applicable`; `NORMATIVE_CONFLICTS: none`;
   no implementation-critical Open Questions). Forbidden: READY design that
   defers SoT/ownership/write-path to apply, or weakens MUST→MAY.

Missing Derived Lifecycle when temporal behavior applies, chat-only
lifecycle, or `UNRESOLVED` left open ⇒
`PRODUCT_ACCEPTANCE_STATUS=FAIL` (or `BLOCKED`) pillar `LIFECYCLE_COVERAGE`
(even if a scenario report says `VERDICT=PASS`).

READY (or purported-complete) `design.md` with deferred architecture,
implementation-critical Open Questions, or MUST/MUST NOT modality weaken ⇒
`PRODUCT_ACCEPTANCE_STATUS=FAIL` (or `BLOCKED`) pillar `PLANNING_DEFECT`
(subclass `PLANNING_DESIGN_READINESS_GAP`) — route to planning writers,
**not** apply.

**Legacy compatibility** (only Changes **without** reviewed
`owner-contract.md`):

1. Durable `OWNER_LIFECYCLE_ECHO` in design/decision/spec (ordered temporal
   steps), and
2. Owner token `CONFIRM_LIFECYCLE` (or `CORRECT` → rewrite → confirm).

Missing legacy echo/CONFIRM on that legacy path ⇒ same FAIL pillar.

**Scenario evidence (also mandatory under PA):**

- `/opsx-spec-scenario-coverage mode=plan` evidence exists for the change, and
- fresh independent scenario report with `VERDICT=PASS` via `mode=audit` or
  `mode=certify` as required by `SCENARIO_TEST_COVERAGE.md`
  (certify when PG/CH provider receipts are required), and
- acceptance-relevant scenario rows **map** to Derived Lifecycle steps
  (or legacy `OWNER_LIFECYCLE_ECHO` steps on the legacy path).

Failure classes (do not conflate):

| Class | Meaning | Typical NEXT |
|---|---|---|
| `UNRESOLVED_PRODUCT_SEMANTICS` | Owner Contract leaves a material transition open | `/opsx-owner-contract-review` |
| `PLANNING_LIFECYCLE_GAP` / `PLANNING_DEFECT` | Semantics known; design omitted them | `/opsx-continue` / `/opsx-ff` / `/opsx-update` |
| `PLANNING_DESIGN_READINESS_GAP` | design present but DESIGN_READINESS fails (deferred SoT/ownership/write, modality weaken, critical Open Questions) | `/opsx-update` / `/opsx-continue` / `/opsx-ff` (not apply) |
| `SPEC_COVERAGE_GAP` / `SPEC_SCENARIO_MISSING` | Lifecycle known; spec scenario missing | planning writer (spec) |
| `SEMANTIC_DRIFT` | Spec invents behavior not in lifecycle/Owner Contract | planning writer |

Missing / stale / FAIL / BLOCKED scenario report ⇒
`PRODUCT_ACCEPTANCE_STATUS=FAIL` pillar `LIFECYCLE_COVERAGE`.

When PA is required, legacy
`SCENARIO_COVERAGE_REQUIRED absent|false` **does not** waive this pillar.
Treat PA-required as forcing lifecycle coverage (equivalent to
`SCENARIO_COVERAGE_REQUIRED=true` for archive).

Planning writers (`/opsx-continue`, `/opsx-ff`, `/opsx-update`) **derive**
Lifecycle from reviewed Owner Contract (primary) or author legacy echo
(legacy only). When they create or revise `design.md`, they MUST also
satisfy `.cursor/pipeline/contracts/DESIGN_GENERATION.md` (`DESIGN_READINESS`).
Scenario commands **consume** Derived Lifecycle (or legacy
echo); they do not replace Owner Contract and must not invent a parallel
DONE or `CONFIRM_LIFECYCLE` contour.

### 3) SIDE_EFFECT_PROOF

Acceptance-relevant scenarios that claim an external mutation (or a forbidden
sibling non-effect) MUST prove:

- **this-run** external side effect (call/adapter observed in the test run), or
- explicit **forbidden non-effect** on the sibling target,

per `TEST_EVIDENCE_TAXONOMY.md` token `SIDE_EFFECT_PROOF` /
`PA_SIDE_EFFECT_PROOF`.

Intent-only, durable-reason-only, or OR-armed proxies that can PASS without
the this-run mutation ⇒ WEAK/FAIL for this pillar
(`PRODUCT_ACCEPTANCE_FAIL_PILLAR=SIDE_EFFECT_PROOF`).

## DONE rule

```text
archive-eligible DONE
  ⇔  PRODUCT_ACCEPTANCE_REQUIRED=false → STATUS NOT_REQUIRED
  OR PRODUCT_ACCEPTANCE_REQUIRED=true  → STATUS PASS
```

`/opsx-verify mode=archive` MUST evaluate this rule and treat PA `FAIL` /
`BLOCKED` / missing required evidence as **hard archive blockers**.

## Soft tooling relationship

Pyright-strict, external-call-coverage, performance-review, antipattern-gate,
static-check (and Owner waivers of those) are **soft / advisory** relative to
Product Acceptance:

```text
SOFT_WAIVE_CLEARS_PRODUCT_ACCEPTANCE: FORBIDDEN
SOFT_PASS_CREATES_DONE: FORBIDDEN
```

Supervisor MUST NOT dispatch verify-archive / archive while
`PRODUCT_ACCEPTANCE_REQUIRED=true` and status is not `PASS`.

## Stage behavior

### Planning (`/opsx-continue`, `/opsx-ff`, `/opsx-update`)

- Decide `PRODUCT_ACCEPTANCE_REQUIRED`.
- Complete MEANING_LOCK before apply-ready when required.
- When PA required and temporal behavior applies: derive durable Lifecycle
  into design (`LIFECYCLE_STATUS: DERIVED`) from reviewed Owner Contract;
  do **not** re-ask `CONFIRM_LIFECYCLE` when unambiguous. UNRESOLVED forks →
  `/opsx-owner-contract-review`. Legacy Changes without owner-contract may
  still use `OWNER_LIFECYCLE_ECHO` + `CONFIRM_LIFECYCLE`. Ensure scenario
  `mode=plan` is on the path (not optional). Do **not** declare apply-ready
  without Derived Lifecycle (or legacy confirmed echo).
- When creating or revising `design.md`: follow
  `.cursor/pipeline/contracts/DESIGN_GENERATION.md`; do **not** declare
  apply-ready if `DESIGN_STATUS: BLOCKED`, architecture is deferred to
  apply, or MUST/MUST NOT was weakened.

### Apply (`/opsx-apply`)

- Re-check MEANING_LOCK before production edits when PA required.
- Re-check durable Derived Lifecycle (`LIFECYCLE_STATUS: DERIVED`) — or
  legacy `OWNER_LIFECYCLE_ECHO` + `CONFIRM_LIFECYCLE` — when PA required;
  do not implement against chat-only lifecycle.
- Do not treat task checkboxes alone as DONE.
- Author tests that can satisfy SIDE_EFFECT_PROOF for acceptance seams.

### Scenario (`/opsx-spec-scenario-coverage`)

- Owns scenario half of LIFECYCLE_COVERAGE evidence; consumes Derived
  Lifecycle (prefer `design.md`) or legacy echo; verifies
  LIFECYCLE ↔ SPEC SCENARIOS; does not declare archive DONE; does not
  re-author product meaning or require `CONFIRM_LIFECYCLE` on the primary path.

### Verify (`/opsx-verify`)

- Sole consumer that may emit archive GO.
- Computes/records `PRODUCT_ACCEPTANCE_STATUS` and fail pillar.
- Soft sections MUST state they do not authorize archive without PA PASS.

### Archive (`/opsx-archive`)

- Hard-stop unless verify archive GO with PA PASS (or NOT_REQUIRED).

### Supervisor

- Owner soft-waive of tooling ≠ PA clear.
- Meaning blocks → Owner semantic decision + planning writer.
- Missing Derived Lifecycle (or legacy unconfirmed echo) → planning writer
  (`/opsx-continue` / `/opsx-update` / `/opsx-ff`), not soft chain or bug-team.
  Genuine unresolved product forks → `/opsx-owner-contract-review`.
- Lifecycle scenario / side-effect blocks → route to scenario / test
  producers, not “continue soft chain to archive”.

## Explicit non-goals

- No `/opsx-product-acceptance` command.
- No bug-team redesign.
- No replacement of SEMANTIC or scenario producers — composition only.
- No second Owner lifecycle confirmation when reviewed Owner Contract already
  uniquely determines temporal behavior.
- No default `owner-lifecycle.md` companion file.

## Regression matrix (process)

1. Competing Auto vs Search legs without Owner durable fields → PA FAIL MEANING
   (not NOT_APPLICABLE) → archive NO_GO.
2. PA required + no scenario report → PA FAIL LIFECYCLE → archive NO_GO even if
   `SCENARIO_COVERAGE_REQUIRED` absent.
3. Acceptance test OR-green without this-run pause/notify call → PA FAIL
   SIDE_EFFECT → archive NO_GO.
4. Soft ECC/pyright Owner waive while PA FAIL → verify/archive still blocked.
5. Docs-only change with explicit NOT_REQUIRED → PA NOT_REQUIRED → archive may
   proceed without scenario certify.
6. PA required + reviewed Owner Contract + Derived Lifecycle present → must
   **not** FAIL solely for absent `CONFIRM_LIFECYCLE` / `OWNER_LIFECYCLE_ECHO`.
7. PA required + no reviewed owner-contract + no durable echo/CONFIRM → PA FAIL
   LIFECYCLE → archive NO_GO (legacy path).
8. PA required + scenario invents behavior absent from lifecycle/Owner Contract
   → SEMANTIC_DRIFT / scenario FAIL (not PASS).
