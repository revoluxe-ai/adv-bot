# Design Generation Readiness (planning → design.md)

## Purpose

Shared SoT for creating `design.md` from upstream planning artifacts
(owner-contract, proposal, specs, decisions) plus repository evidence.

Consumed by:

- `/opsx-continue` (when the ready artifact is `design`)
- `/opsx-ff` (when creating the `design` artifact)

Skill/prompt mirrors of those commands MUST follow this contract identically.

This contract is **not** a user-facing command. It does **not** authorize
Owner semantic decisions, product code edits, or rewriting reviewed
`owner-contract.md` semantics. It does authorize (and require) the planning
agent to resolve **technical** architecture choices needed for
implementation readiness.

## Authority invariant

```text
DESIGN MUST RESOLVE ARCHITECTURE BEFORE IMPLEMENTATION
design.md = resolved technical plan for already-authorized product semantics
same upstream context → semantically equivalent design
  (/opsx-continue ≡ /opsx-ff; advancement mode differs only)
DESIGN GENERATION MUST PRESERVE UPSTREAM NORMATIVE MODALITY
MUST/MUST NOT/MAY modality preserved from authoritative upstream
```

Apply executes design. Apply MUST NOT receive tasks that choose:

- State Source of Truth
- durability boundary
- ownership
- write-path / write authority
- recovery / persistence contract

## When this gate runs

Two phases — both required before declaring
`openspec/changes/<change>/design.md` complete (before marking the design
artifact done / unlocking tasks):

```text
UPSTREAM_REQUIREMENTS
        ↓
DRAFT_DESIGN  (in memory / scratch — not yet declared complete)
        ↓
NORMATIVE_PRESERVATION_CHECK  (post-generation)
        ↓
READY | BLOCKED
```

1. **Pre-draft / while drafting:** resolve technical choices; scan upstream
   for modality conflicts and implementation-critical open questions.
2. **Post-draft:** validate the **actually generated** draft design content
   for normative modality preservation.

`DESIGN_STATUS: READY` is allowed **only after** the post-generation check
passes. A clean upstream scan alone is **not** sufficient.

If either phase fails:

```text
DESIGN_STATUS: BLOCKED
FILES_CHANGED: none | partial-draft-only-if-explicitly-kept-unready
```

Do **not** treat design as ready. Downstream planning MUST NOT receive a
false «design complete». Prefer not writing a READY design file; if a draft
exists, it MUST carry `DESIGN_STATUS: BLOCKED` and MUST NOT be reported as
complete.

## DESIGN_READINESS

Emit (chat and/or durable note in the continue/ff progress output, and
prefer a short `DESIGN_READINESS` / `DESIGN_STATUS` block inside
`design.md` when READY) **after** draft construction and post-generation
validation:

```text
DESIGN_READINESS

PRODUCT_SEMANTICS_RESOLVED: yes
STATE_OWNERSHIP_RESOLVED: yes | not_applicable
DURABLE_SOT_RESOLVED: yes | not_applicable
WRITE_AUTHORITY_RESOLVED: yes | not_applicable
RECOVERY_SEMANTICS_RESOLVED: yes | not_applicable
NORMATIVE_CONFLICTS: none
NORMATIVE_MODALITY_PRESERVED: yes | no
IMPLEMENTATION_CRITICAL_OPEN_QUESTIONS: none

DESIGN_STATUS: READY | BLOCKED
REASON: <none | TECHNICAL_DESIGN_UNRESOLVED | UPSTREAM_NORMATIVE_CONFLICT |
  NORMATIVE_MODALITY_DRIFT | …>
```

Declare design complete only when:

```text
PRODUCT_SEMANTICS_RESOLVED: yes
STATE_OWNERSHIP_RESOLVED: yes | not_applicable
DURABLE_SOT_RESOLVED: yes | not_applicable
WRITE_AUTHORITY_RESOLVED: yes | not_applicable
RECOVERY_SEMANTICS_RESOLVED: yes | not_applicable
NORMATIVE_CONFLICTS: none
NORMATIVE_MODALITY_PRESERVED: yes
IMPLEMENTATION_CRITICAL_OPEN_QUESTIONS: none
DESIGN_STATUS: READY
```

Use `not_applicable` only when the Change truly has no durable/stateful
write/recovery surface (document why briefly). Durable-state Changes MUST
NOT mark SoT/ownership/write/recovery as `not_applicable`.

Forbidden false readiness: declaring `NORMATIVE_CONFLICTS: none` +
`DESIGN_STATUS: READY` and then emitting draft text that weakens upstream
`MUST` / `MUST NOT`. Preflight that ignores draft content is a contract
defect.

---

## 1. TECHNICAL_CHOICE_RESOLUTION

When a technical architecture choice exists, for example:

- PG vs Redis (or other persistence)
- existing state vs new state
- which component owns canonical state
- which component may write
- how state is read / recovered after restart

the design generator MUST:

1. Study repository evidence (existing patterns, adjacent modules).
2. Study existing architecture decisions / patterns
   (context-first; bounded fallback — see architecture-decisions rule).
3. Choose the minimal technical option that satisfies upstream semantics.
4. Record the choice in `design.md` (and propose a change decision artifact
   when reusable ownership/write-path rules are new).
5. Record rationale / trade-off.
6. Fix ownership and write boundary.

Record at least:

```text
WHAT is durable (if anything)
WHO owns canonical state
WHERE canonical state lives (SoT class / store)
WHO may write it
HOW it is read / recovered
```

Exact ORM field names or class names are **not** required for READY.

### Owner confirmation

If the technical choice does **not** change WHAT / SCOPE / ACCEPTANCE,
Owner confirmation is **not** required. This is planning/design-agent
responsibility.

### Forbidden READY shapes

```text
Точная схема PG/Redis — apply-time
PG vs Redis — выбрать в apply / при реализации
SoT TBD — decide during implementation
write ownership — resolve at apply
```

Forbidden combination:

```text
DESIGN_STATUS: READY
+ architecture choice delegated to apply
```

### Fail → BLOCKED when evidence is insufficient

Do **not** write «решить в apply». Instead:

```text
DESIGN_STATUS: BLOCKED
REASON: TECHNICAL_DESIGN_UNRESOLVED

UNRESOLVED:
<exact architecture choice>

EVIDENCE_MISSING:
<what prevents a safe decision>

NEXT_ACTION: gather evidence / propose decision / /opsx-update after facts exist
```

Do **not** auto-ask Owner solely for a pure technical PG/Redis fork when
WHAT/SCOPE/ACCEPTANCE are unchanged — either resolve from evidence or
BLOCK with `EVIDENCE_MISSING`.

---

## 2. NORMATIVE_MODALITY_PRESERVATION

When reflecting authoritative upstream semantics (reviewed owner-contract,
specs, accepted/proposed decisions) into design prose, preserve modality:

```text
MUST     → MUST
MUST NOT → MUST NOT
MAY      → MAY
```

Forbidden weakenings (examples):

```text
MUST     → MAY
MUST     → SHOULD
MUST NOT → SHOULD NOT
MUST NOT → MAY NOT
```

Example (regression class):

```text
upstream: our block clear AND no other blockers → Auto MUST start
design:   Activity-control MUST start Auto …
FORBIDDEN: Activity-control MAY start Auto …
```

If two **authoritative** upstream artifacts conflict on modality for the
same observable:

```text
DESIGN_STATUS: BLOCKED
REASON: UPSTREAM_NORMATIVE_CONFLICT

SOURCE_A:
<artifact + modality>

SOURCE_B:
<artifact + modality>

NEXT_ACTION: reconcile upstream planning (not silent compromise wording)
```

Do **not** model-select the more convenient semantics. If a single
authoritative source is unambiguous, design MUST match it.

### Post-generation drift (mandatory)

After draft design exists, re-check draft wording against upstream
obligations.

If draft weakens an upstream obligation (e.g. upstream `MUST start`, draft
`MAY start`):

```text
NORMATIVE_MODALITY_PRESERVED: no
DESIGN_STATUS: BLOCKED
REASON: NORMATIVE_MODALITY_DRIFT
DRIFT: <upstream obligation> → <draft wording>
FILES_CHANGED: none | partial-draft-only-if-explicitly-kept-unready
```

Do **not** declare design complete. Fix the draft (preserve modality) or
stop.

This catch is required even when the pre-draft upstream scan reported
`NORMATIVE_CONFLICTS: none` — the generator itself can introduce drift.

---

## 3. OPEN_QUESTIONS_BOUNDARY

`## Open Questions` MAY exist, but only for items that:

- are **not** required for implementation readiness;
- do **not** define state authority;
- do **not** define product semantics;
- do **not** define write / recovery contract.

### Forbidden Open Questions (implementation-critical)

```text
- где SoT?
- PG или Redis?
- кто владеет состоянием?
- где начинается epoch? (when that is product/recovery semantics)
- какой component имеет write authority?
```

Any such question → readiness FAIL (`IMPLEMENTATION_CRITICAL_OPEN_QUESTIONS`
non-empty) → `DESIGN_STATUS: BLOCKED`.

### Allowed Open Questions (harmless naming)

```text
- точное имя enum / reason string
- точное имя поля
- локальное название helper
```

only when semantics and authority are already fully determined. Such
questions alone MAY leave `DESIGN_STATUS: READY`.

---

## 4. DERIVED_LIFECYCLE (temporal / stateful)

Unchanged authority model (see continue/ff command bodies):

```text
owner-contract.md (+ review PASS) = semantic authority
design Lifecycle                  = DERIVED planning representation
continue / ff                     = no product authority
```

When behavior is temporal/stateful, design MUST include Derived Lifecycle
with `LIFECYCLE_STATUS: DERIVED` and per-step `SOURCE:` provenance, or
`LIFECYCLE_STATUS: UNRESOLVED` → route
`/opsx-owner-contract-review` (not `CONFIRM_LIFECYCLE` inside continue/ff).

Lifecycle completeness does **not** waive TECHNICAL_CHOICE_RESOLUTION or
NORMATIVE_MODALITY_PRESERVATION.

---

## 5. CONTINUE_FF_EQUIVALENCE

```text
same upstream context + same repository evidence
  → semantically equivalent design.md
```

independent of advancement mode (`/opsx-continue` vs `/opsx-ff`).

If a shared helper/template is used, edit the **single** SoT (this contract
and any shared template it cites). Do **not** maintain divergent design
rules in continue-only vs ff-only prose.

---

## 6. Out of scope for this contract

- Manually «fixing» a product Change’s existing `design.md` as part of a
  command-contract apply (regenerate via continue/ff after this gate exists,
  or `/opsx-update`).
- Owner Contract semantic authorship.
- Production code, product tests, migrations, product tasks.
- `/opsx-new`, `/opsx-owner-contract-review`, `/opsx-spec-scenario-coverage`,
  apply / verify / archive command bodies (unless a separate authorized fix
  lists them).
- Task generation (see `TASK_GENERATION.md`).

## Process fixtures

Regression fixtures live under:

`.cursor/commands/_fixtures/design-generation-readiness/`

Real planning sample used only as a **generator** fixture pointer:

`openspec/changes/auto-shelf-exhausted-pause-retest/`

Do not edit that Change’s product `design.md` inside a command-contract
apply of this gate; regenerate via continue/ff (or update) after the gate
exists.
