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
```

## When this gate runs

Immediately **before** writing `openspec/changes/<change>/tasks.md`.

If the gate fails:

```text
TASKS_STATUS: BLOCKED
FILES_CHANGED: none
```

Do **not** create or overwrite `tasks.md`.

## TASK_GENERATION_READINESS

Emit (chat and/or durable note in the continue/ff progress output):

```text
TASK_GENERATION_READINESS

UNRESOLVED_DESIGN_CHOICES: none | <item> (fix: <artifact-path>)
UNRESOLVED_PRODUCT_CHOICES: none | <item> (route: <command>)
UPSTREAM_NORMATIVE_CONFLICTS: none | <pair>
SCENARIO_REQUIREMENTS_CONSUMED: yes | not_required

TASKS_STATUS: READY | BLOCKED
REASON: <none | TECHNICAL_DESIGN_UNRESOLVED | UNRESOLVED_PRODUCT_CHOICE | UPSTREAM_NORMATIVE_CONFLICT | …>
```

Write `tasks.md` only when:

```text
UNRESOLVED_DESIGN_CHOICES: none
UNRESOLVED_PRODUCT_CHOICES: none
UPSTREAM_NORMATIVE_CONFLICTS: none
SCENARIO_REQUIREMENTS_CONSUMED: yes | not_required
TASKS_STATUS: READY
```

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
decisions) into tasks, preserve normative modality:

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

If two upstream artifacts conflict on modality for the same observable:

```text
TASKS_STATUS: BLOCKED
REASON: UPSTREAM_NORMATIVE_CONFLICT
CONFLICT: <artifact-a modality> vs <artifact-b modality>
NEXT_ACTION: reconcile upstream planning artifacts (not silent soft wording)
```

Do **not** pick the more convenient formulation.

---

## 4. SCENARIO_REQUIREMENTS_CONSUMED

When the Change has material scenario coverage obligations (e.g. Derived
Lifecycle + `/opsx-spec-scenario-coverage`, or explicit scenario requirements
in specs):

- `SCENARIO_REQUIREMENTS_CONSUMED: yes` — every material scenario/requirement
  that implementation must satisfy is reflected in tasks (or explicitly
  deferred with a named follow-up that is itself a task), **or**
- `SCENARIO_REQUIREMENTS_CONSUMED: not_required` — only when scenarios are
  not applicable for this Change (document why briefly).

Missing consumption with applicable scenarios → treat as readiness failure
(prefer fixing task draft before READY; do not silently drop scenarios).

---

## 5. CONTINUE_FF_EQUIVALENCE

```text
same upstream artifacts
  → semantically equivalent tasks.md
```

independent of advancement mode (`/opsx-continue` vs `/opsx-ff`).

If a shared helper/template is used, edit the **single** SoT (this contract
and any shared template it cites). Do **not** maintain divergent task rules
in continue-only vs ff-only prose.

---

## 6. Out of scope for this contract

- Editing product `openspec/changes/<change>/tasks.md` after the fact as a
  “repair” of a prior bad generation (use `/opsx-update` / re-run continue
  after design fix).
- Owner Contract semantic authorship.
- Production code, product tests, migrations.
- `/opsx-new`, `/opsx-owner-contract-review`, `/opsx-spec-scenario-coverage`,
  apply / verify / archive command bodies (unless a separate authorized fix
  lists them).

## Process fixtures

Regression fixtures live under:

`.cursor/commands/_fixtures/task-generation-readiness/`

Real planning sample used only as a **generator** fixture pointer:

`openspec/changes/auto-shelf-exhausted-pause-retest/`

Do not “fix” that Change’s product artifacts inside a command-contract
apply of this gate; regenerate via continue/ff after the gate exists (or
update design first if BLOCKED).
