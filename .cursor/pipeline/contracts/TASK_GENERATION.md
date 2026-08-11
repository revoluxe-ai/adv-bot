# Task Generation Readiness (planning → tasks.md)

## Purpose

Shared SoT for creating `tasks.md` from already-resolved planning artifacts.

Consumed by:

- `/opsx-continue` (when the ready artifact is `tasks`)
- `/opsx-ff` (when creating the `tasks` artifact)

Skill/prompt mirrors of those commands MUST follow this contract identically.

This contract is **not** a user-facing command. It does **not** authorize
Owner semantic decisions, product code edits, or rewriting upstream
`design.md` / `spec.md` / `owner-contract.md`.

## Authority invariant

```text
tasks.md = deterministic decomposition of resolved planning artifacts
TASKS MUST IMPLEMENT DESIGN, NOT COMPLETE DESIGN
same upstream artifacts → semantically equivalent tasks
  (/opsx-continue ≡ /opsx-ff; advancement mode differs only)
TASK GENERATION MUST PRESERVE UPSTREAM NORMATIVE MODALITY
```

Tasks are an implementation decomposition of resolved design/spec semantics —
**not** a reinterpretation of them.

## Normative source order

When forming task requirements, determine normative modality from already
authoritative planning artifacts (context-first, exact paths):

1. `owner-contract`
2. accepted/proposed `decision`(s) for this change
3. `design`
4. `spec` / scenario coverage plan

The task generator MUST NOT invent or weaken modality. If authoritative
upstream is unambiguous (`MUST`), the task MUST keep `MUST`. If upstream
sources conflict on the same observable (e.g. design `MUST` vs spec `MAY`):

```text
TASKS_STATUS: BLOCKED
REASON: UPSTREAM_NORMATIVE_CONFLICT
```

with the conflicting sources named. Do **not** model-select a compromise.

## When this gate runs

Two phases — both required before writing
`openspec/changes/<change>/tasks.md`:

```text
UPSTREAM_REQUIREMENTS
        ↓
DRAFT_TASKS  (in memory / scratch — not yet written)
        ↓
NORMATIVE_PRESERVATION_CHECK  (post-generation)
        ↓
READY | BLOCKED
```

1. **Pre-draft:** scan upstream for unresolved design/product choices and
   upstream-vs-upstream modality conflicts.
2. **Post-draft:** validate the **actually generated** draft task content
   for modality preservation, conditional-branch preservation, and
   scenario consumption.

`TASKS_STATUS: READY` is allowed **only after** the post-generation check
passes. A clean upstream scan alone is **not** sufficient.

If either phase fails:

```text
TASKS_STATUS: BLOCKED
FILES_CHANGED: none
```

Do **not** create or overwrite `tasks.md`.

## TASK_GENERATION_READINESS

Emit (chat and/or durable note in the continue/ff progress output)
**after** draft construction and post-generation validation:

```text
TASK_GENERATION_READINESS

UNRESOLVED_DESIGN_CHOICES: none | <item> (fix: <artifact-path>)
UNRESOLVED_PRODUCT_CHOICES: none | <item> (route: <command>)
UPSTREAM_NORMATIVE_CONFLICTS: none | <pair>
NORMATIVE_MODALITY_PRESERVED: yes | no
CONDITIONAL_BRANCHES_PRESERVED: yes | no
SCENARIO_REQUIREMENTS_CONSUMED: yes | no | not_required
SCENARIO_PLAN_EVIDENCE_ID: <id> | none | not_required
SCENARIO_PLAN_STATUS: ready | provisional | blocked | missing | not_required
SCENARIO_PLAN_FRESHNESS: current | stale | missing | integrity_fail | not_required

TASKS_STATUS: READY | BLOCKED
REASON: <none | TECHNICAL_DESIGN_UNRESOLVED | UNRESOLVED_PRODUCT_CHOICE |
  UPSTREAM_NORMATIVE_CONFLICT | NORMATIVE_MODALITY_DRIFT |
  CONDITIONAL_BRANCH_COLLAPSE | SCENARIO_PLAN_EVIDENCE_MISSING |
  SCENARIO_PLAN_EVIDENCE_STALE | SCENARIO_PLAN_EVIDENCE_INTEGRITY_FAIL | …>
```

Write `tasks.md` only when:

```text
UNRESOLVED_DESIGN_CHOICES: none
UNRESOLVED_PRODUCT_CHOICES: none
UPSTREAM_NORMATIVE_CONFLICTS: none
NORMATIVE_MODALITY_PRESERVED: yes
CONDITIONAL_BRANCHES_PRESERVED: yes
SCENARIO_REQUIREMENTS_CONSUMED: yes | not_required
# when consumed=yes, also require:
#   SCENARIO_PLAN_EVIDENCE_ID present
#   SCENARIO_PLAN_STATUS: ready
#   SCENARIO_PLAN_FRESHNESS: current
TASKS_STATUS: READY
```

Forbidden false readiness: declaring
`UPSTREAM_NORMATIVE_CONFLICTS: none` + `TASKS_STATUS: READY` and then
emitting draft text that weakens upstream `MUST` / collapses conditional
branches. Preflight that ignores draft content is a contract defect.

Forbidden false readiness: `SCENARIO_REQUIREMENTS_CONSUMED: yes` from chat
context alone without a CURRENT durable
`openspec/changes/<change>/scenario-coverage/plan.receipt.json`.

---

## 1. IMPLEMENT_NOT_COMPLETE_DESIGN

Before forming task lines, scan the **draft** task list and upstream
`design.md` / proposed decisions for unresolved technical forks that would
become implementer choices, including actions like:

- выбрать SoT / choose SoT
- решить PG или Redis / PG | Redis undecided
- определить ownership
- выбрать write-path
- решить architecture
- определить semantic behavior

### Pass

Upstream design/decision already names the SoT, ownership, write-path, and
semantic behavior. Tasks only implement that choice (migrate, wire, test).

### Fail → BLOCKED

```text
TASKS_STATUS: BLOCKED
REASON: TECHNICAL_DESIGN_UNRESOLVED
UNRESOLVED_ITEM: <exact fork, e.g. pause-block SoT = PG | Redis>
FIX_ARTIFACT: <exact path that must resolve it, e.g. design.md or decisions/.../decision.md>
NEXT_ACTION: resolve technical design (typically /opsx-update or design/decision edit)
```

Do **not** auto-ask Owner. Technical design gap ≠ Owner semantic gap.

Forbidden task shapes (examples):

```text
- [ ] Выбрать SoT … (PG и/или Redis …)
- [ ] Decide ownership during implementation
- [ ] Choose write-path at apply time
```

---

## 2. EVIDENCE_ROLES

When a Change **intentionally changes** existing behavior, task lines that
touch tests/evidence MUST distinguish roles:

| Role | Meaning |
|---|---|
| `LEGACY_BASELINE` | Proof of **current** behavior **before** the intentional change |
| `TARGET_REGRESSION` | Test of the **new** expected behavior |
| `FINAL_ACCEPTANCE` | End-state proof that target semantics hold |

### Rules

1. Label (or structurally separate) baseline vs target vs final tasks.
2. `LEGACY_BASELINE` may capture old assertions; it MUST NOT require those
   old assertions to remain green after the intentional semantic change.
3. `TARGET_REGRESSION` / `FINAL_ACCEPTANCE` assert the new behavior.
4. Forbidden logical contradiction in the final task plan:

```text
OLD behavior MUST happen
AND
OLD behavior MUST NOT happen
```

### Allowed patterns

- Use an existing test as baseline evidence, then replace/update it for
  `TARGET_REGRESSION`.
- Create a temporary characterization under `LEGACY_BASELINE`, then a
  separate target regression task.
- Explicitly split baseline proof from final regression.

---

## 3. NORMATIVE_MODALITY_PRESERVATION

When decomposing upstream requirements (spec / design / owner-contract /
decisions / scenario coverage plan) into tasks, preserve normative modality:

```text
MUST     → MUST
MUST NOT → MUST NOT
MAY      → MAY
```

Forbidden weakenings (examples):

```text
MUST     → MAY
MUST NOT → SHOULD NOT
MUST NOT → MAY NOT
MUST     → SHOULD
```

### Upstream conflict (pre-draft)

If two upstream artifacts conflict on modality for the same observable:

```text
TASKS_STATUS: BLOCKED
REASON: UPSTREAM_NORMATIVE_CONFLICT
CONFLICT: <artifact-a modality> vs <artifact-b modality>
NEXT_ACTION: reconcile upstream planning artifacts (not silent soft wording)
```

Do **not** pick the more convenient formulation.

### Post-generation drift (mandatory)

After draft tasks exist, re-check draft wording against upstream obligations.

If draft weakens an upstream obligation (e.g. upstream `MUST start`, draft
`MAY start`):

```text
NORMATIVE_MODALITY_PRESERVED: no
TASKS_STATUS: BLOCKED
REASON: NORMATIVE_MODALITY_DRIFT
DRIFT: <upstream obligation> → <draft wording>
FILES_CHANGED: none
```

Do **not** write `tasks.md`. Fix the draft (preserve modality) or stop.

This catch is required even when the pre-draft upstream scan reported
`UPSTREAM_NORMATIVE_CONFLICTS: none` — the generator itself can introduce
drift.

---

## 4. CONDITIONAL_BRANCH_PRESERVATION

Task decomposition MUST preserve material conditional branches from
upstream lifecycle / requirements.

Forbidden collapse:

```text
IF X → MUST A
ELSE Y → MUST NOT A
        ↓
A MAY happen
```

Both branches MUST remain explicit in tasks (wording may vary; semantic
equivalence required).

### Regression shape (shelf-exhausted clear / start)

Upstream:

```text
our block cleared AND no other blockers → Auto MUST start
other blocker remains → Auto MUST NOT be force-started
```

Required task semantics (both branches):

```text
Given our block is cleared AND no other blockers remain
→ Auto MUST start

Given another blocker remains
→ our block MUST clear
→ Auto MUST NOT be force-started
```

Forbidden as a substitute for that deterministic pair:

```text
Auto MAY start
```

On collapse:

```text
CONDITIONAL_BRANCHES_PRESERVED: no
TASKS_STATUS: BLOCKED
REASON: CONDITIONAL_BRANCH_COLLAPSE
FILES_CHANGED: none
```

---

## 5. EPOCH_COUPLING (when epoch semantics exist upstream)

When upstream says a new epoch MUST begin only after **actual** Auto start,
tasks MUST keep that coupling.

Required shape:

```text
clear our block → evaluate remaining blockers
if actual Auto start occurs → start new epoch
if Auto remains paused → MUST NOT start new epoch
```

Forbidden shortenings that drop the coupling:

```text
clear → new epoch
Auto MAY start + new epoch
```

(when used as a substitute for conditional MUST start / MUST NOT force-start
+ epoch-only-after-actual-start).

Violations count as modality/conditional failure
(`NORMATIVE_MODALITY_PRESERVED: no` and/or
`CONDITIONAL_BRANCHES_PRESERVED: no`).

---

## 6. SCENARIO_REQUIREMENTS_CONSUMED

When the Change has material scenario coverage obligations (e.g. Derived
Lifecycle + `/opsx-spec-scenario-coverage`, or explicit scenario requirements
in specs):

- Locate canonical durable evidence first:
  `openspec/changes/<change>/scenario-coverage/plan.receipt.json`
  (+ matching `plan.md`). Authority:
  `SCENARIO_TEST_COVERAGE.md` **DURABLE_PLAN_EVIDENCE**.
- Validate freshness (`CURRENT` / `STALE` / `MISSING` / `INTEGRITY_FAIL`)
  against current design/spec(/lifecycle) content hashes in the receipt.
- `SCENARIO_REQUIREMENTS_CONSUMED: yes` — **only** when:
  - durable receipt exists;
  - `PLAN_STATUS: ready` (v1 gate; provisional alone does not unlock READY);
  - freshness is `current`;
  - integrity checks pass;
  - tasks reflect that exact `PLAN_EVIDENCE_ID`'s material scenarios
    (or explicitly defer with a named follow-up task).
  Emit with the readiness block:
  `SCENARIO_PLAN_EVIDENCE_ID`, `SCENARIO_PLAN_STATUS: ready`,
  `SCENARIO_PLAN_FRESHNESS: current`.
- `SCENARIO_REQUIREMENTS_CONSUMED: not_required` — only when scenarios are
  not applicable for this Change (document why briefly).
- `SCENARIO_REQUIREMENTS_CONSUMED: no` — applicable scenarios missing from
  draft → readiness failure.

Missing / unusable durable plan evidence:

```text
TASKS_STATUS: BLOCKED
REASON: SCENARIO_PLAN_EVIDENCE_MISSING
  | SCENARIO_PLAN_EVIDENCE_STALE
  | SCENARIO_PLAN_EVIDENCE_INTEGRITY_FAIL
FILES_CHANGED: none
NEXT: /opsx-spec-scenario-coverage mode=plan change=<change>
```

Task generation MUST NOT manufacture receipts, MUST NOT use chat history as
SoT, and MUST NOT self-attest `consumed: yes` without the CURRENT receipt.

Missing consumption with applicable scenarios → treat as readiness failure
(prefer fixing task draft before READY; do not silently drop scenarios).

---

## 7. CONTINUE_FF_EQUIVALENCE

```text
same upstream artifacts
  → semantically equivalent tasks.md
```

independent of advancement mode (`/opsx-continue` vs `/opsx-ff`).

Edit this **single** SoT (and fixtures it cites). Do **not** maintain
divergent task rules in continue-only vs ff-only prose.

---

## 8. Out of scope for this contract

- Editing product `openspec/changes/<change>/tasks.md` after the fact as a
  “repair” of a prior bad generation (use `/opsx-update` / re-run continue
  after the gate exists; do not hand-patch modality as the process fix).
- Owner Contract semantic authorship.
- Production code, product tests, migrations.
- `/opsx-new`, `/opsx-owner-contract-review`, `/opsx-spec-scenario-coverage`,
  design-generation, Product Acceptance, apply / verify / archive command
  bodies (unless a separate authorized fix lists them).

## Process fixtures

Regression fixtures live under:

`.cursor/commands/_fixtures/task-generation-readiness/`

Real planning sample used only as a **generator** fixture pointer:

`openspec/changes/auto-shelf-exhausted-pause-retest/`

Do not “fix” that Change’s product artifacts inside a command-contract
apply of this gate; regenerate via continue/ff after the gate exists (or
update design first if BLOCKED).
