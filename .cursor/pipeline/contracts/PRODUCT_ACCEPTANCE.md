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

- `/opsx-spec-scenario-coverage mode=plan` evidence exists for the change, and
- fresh independent scenario report with `VERDICT=PASS` via `mode=audit` or
  `mode=certify` as required by `SCENARIO_TEST_COVERAGE.md`
  (certify when PG/CH provider receipts are required).

Missing / stale / FAIL / BLOCKED scenario report ⇒
`PRODUCT_ACCEPTANCE_STATUS=FAIL` pillar `LIFECYCLE_COVERAGE`.

When PA is required, legacy
`SCENARIO_COVERAGE_REQUIRED absent|false` **does not** waive this pillar.
Treat PA-required as forcing lifecycle coverage (equivalent to
`SCENARIO_COVERAGE_REQUIRED=true` for archive).

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

### Planning (`/opsx-ff`, `/opsx-update`)

- Decide `PRODUCT_ACCEPTANCE_REQUIRED`.
- Complete MEANING_LOCK before apply-ready when required.
- When PA required, ensure scenario `mode=plan` is on the path (not optional).

### Apply (`/opsx-apply`)

- Re-check MEANING_LOCK before production edits when PA required.
- Do not treat task checkboxes alone as DONE.
- Author tests that can satisfy SIDE_EFFECT_PROOF for acceptance seams.

### Scenario (`/opsx-spec-scenario-coverage`)

- Owns LIFECYCLE_COVERAGE evidence; does not declare archive DONE.

### Verify (`/opsx-verify`)

- Sole consumer that may emit archive GO.
- Computes/records `PRODUCT_ACCEPTANCE_STATUS` and fail pillar.
- Soft sections MUST state they do not authorize archive without PA PASS.

### Archive (`/opsx-archive`)

- Hard-stop unless verify archive GO with PA PASS (or NOT_REQUIRED).

### Supervisor

- Owner soft-waive of tooling ≠ PA clear.
- Meaning blocks → Owner semantic decision + planning writer.
- Lifecycle/side-effect blocks → route to scenario / test producers, not
  “continue soft chain to archive”.

## Explicit non-goals

- No `/opsx-product-acceptance` command.
- No bug-team redesign.
- No replacement of SEMANTIC or scenario producers — composition only.

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
