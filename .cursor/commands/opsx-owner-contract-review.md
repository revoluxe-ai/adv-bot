---
description: "READ_ONLY independent semantic review of owner-contract.md vs OWNER_INTENT / confirmed OWNER_DECISIONS before continue/ff. Never writes."
argument-hint: "change=<name> | path=<owner-contract.md> [paste EVOLUTION_HANDOFF / EXPLORE_HANDOFF]"
---

# /opsx-owner-contract-review

Независимый **READ_ONLY** semantic review `owner-contract.md` после
`/opsx-new` и до создания `proposal` / `spec` / `design` / `tasks`.

Capability: `owner-contract-review`.

Единственный вопрос команды:

> Можно ли доказать по доступным **durable** artifacts, что Owner Contract
> сохраняет смысл Owner, не содержит неподтверждённых Owner decisions,
> внутренних противоречий и скрытого расширения scope?

## What this is

* Independent semantic reviewer (prefer **separate chat** from `/opsx-new`).
* Soft recommended precondition before `/opsx-continue` / `/opsx-ff`.
* Producer of `OWNER_CONTRACT_REVIEW` machine block + findings.
* Source of truth = durable artifacts only (not prior chat reasoning).

## What this is NOT

* NOT an implementation designer / technical variant picker.
* NOT a writer of `owner-contract.md`, Evolution, Explore, or planning artifacts.
* NOT Owner semantic authority (never replaces Owner approval).
* NOT a hard machine gate inside `continue` / `ff` / `apply` / `verify` /
  Supervisor (v1: recommend only; future hard-gate = separate Owner decision).
* NOT `/opsx-verify`, `/opsx-performance-review`, `/opsx-antipattern-gate`.

## Hard rules

* **READ_ONLY** end-to-end. Any file mutation = command failure.
* Do not auto-fix contradictions; report them.
* Do not invent product decisions or new scope.
* Chat-only confirmation that is **not** in a durable handoff/artifact
  ⇒ **not** a proven `OWNER_DECISION` ⇒ `NEEDS_OWNER` / missing provenance.
* Silence / no objection / answer to a neighboring question / agent proposal /
  repository evidence / “technical obviousness” ≠ Owner confirmation.
* Prefer Owner UI/product terms over internal enums; internal ids only as
  parenthetical gloss.
* Follow `.cursor/commands/opsx-source-resolution.md` and
  `.cursor/commands/opsx-execution-preflight.md` (Grep-first; parallel Read ≤ 2;
  no broad archaeology).

## User input

```text
$ARGUMENTS
```

| Token | Effect |
|-------|--------|
| `change=<name>` | resolve `openspec/changes/<name>/owner-contract.md` |
| `path=<file>` | exact path to `owner-contract.md` |
| pasted `EVOLUTION_HANDOFF` / `EXPLORE_HANDOFF` | durable origin context |
| unknown token | `STATUS=BLOCKED`, no file changes |

If neither `change=` nor `path=` and no resolvable single active change → ask
one concrete question; do not invent the change id.

## Pipeline position (soft)

```text
opsx-evolution
  → opsx-explore
  → opsx-new                    (writes owner-contract.md)
  → opsx-owner-contract-review  ← this command (separate chat, READ_ONLY)
  → Owner corrections if needed (owning writer / Owner; not this command)
  → opsx-owner-contract-review until PASS
  → opsx-continue / opsx-ff     (recommended after PASS; not hard-gated v1)
```

## Source precedence

1. **OWNER_INTENT** — Owner wording / durable Owner correction only.
2. **OWNER_DECISIONS** — only explicitly confirmed Owner decisions with
   durable provenance.
3. **Current durable contracts** — `openspec/specs/**`, Accepted
   `openspec/decisions/**` for compatibility/terminology; cannot rewrite
   `OWNER_INTENT`.
4. **Repository facts** — mapping / current reality checks only; cannot become
   intent or decision.
5. **Explore proposals / agent inference** — advisory only; never
   `OWNER_DECISION` without separate Owner confirmation.

## Required read set

Minimum:

```text
openspec/changes/<change>/owner-contract.md
```

When available (paste or files):

```text
EVOLUTION_HANDOFF → OWNER_INTENT
EXPLORE_HANDOFF   → OWNER_INTENT, OWNER_DECISIONS, EXPLORE_PROPOSALS,
                    UNRESOLVED, CURRENT_CONTRACT, ACCEPTED_DECISIONS,
                    HISTORICAL_EVIDENCE, REPOSITORY_FINDINGS, RUNTIME_MAPPING
```

Also as needed (bounded):

* relevant `openspec/specs/**`
* relevant Accepted `openspec/decisions/**`
* targeted archived changes for terminology/history
* current code/tests **only** for concrete CONTRACT_VS_REALITY claims

Regression fixtures (dry-run / acceptance):  
`.cursor/commands/_fixtures/owner-contract-review/`

## Mandatory checks

### 1. INTENT_PRESERVATION

Compare `OWNER_INTENT` to «Что хотим получить», «Зачем», and main acceptance
statements. Same object of change? Same user-visible result? No silent
technical reframe? No dropped essential intent?

### 2. OWNER_DECISION_PROVENANCE

For each material bullet under `## Решения Owner`, require durable explicit
Owner confirmation. Partial answers confirm **only** what was answered.

Critical regression: agent proposes `PLAN_DISTANCE only` + module ON; Owner
says only “module ON” ⇒ `PLAN_DISTANCE only` must **not** be treated as
confirmed.

### 3. INTERNAL_CONSISTENCY

Conflicts among want / keep / out-of-scope / acceptance / Owner decisions.
Report conflict; do **not** pick the “correct” wording.

### 4. TERMINOLOGY_DISAMBIGUATION

Disambiguate overloaded product terms (e.g. «полки» = WB Auto placement vs
bot module «Управление ставкой в полках»). Ambiguous ⇒
`TERMINOLOGY: FAIL|NEEDS_OWNER` + exact Owner question.

### 5. SCOPE_INTEGRITY

No unconfirmed capability / mode / constraint; no dropped essential intent;
no FUTURE/OUT_OF_SCOPE smuggled into current Change via CURRENT_INCREMENT /
KEEP / HARD / FORWARD / EXPLORE_PROPOSALS / CANDIDATE_MAPPING.

### 6. ACCEPTANCE_COHERENCE

«Как поймём, что получилось» must prove Owner intent: observable, mutually
consistent, respects higher-priority constraints, not a technical proxy for
the real result. Do **not** design tests — only semantic adequacy.

### 7. STALE_ASSUMPTION_CHECK

After Owner correction, old meaning must not remain in other sections
(invariants / acceptance / out of scope / decisions / summary).

### 8. CONTRACT_VS_REALITY

Only when contract asserts current behavior (“сейчас X работает так”):
targeted specs/code/tests check. On mismatch →
`CONTRACT_VS_REALITY: CONFLICT` with Owner desired vs current — do **not**
rewrite Owner intent.

## Verdict model

Exactly one overall:

| Verdict | When |
|---------|------|
| `PASS` | All mandatory semantic checks pass. Does **not** mean Owner approved implementation. |
| `NEEDS_OWNER` | Semantics cannot be fixed without Owner (ambiguous term, unproven decision, conflicting expected behaviors, missing source). |
| `FAIL` | Contract demonstrably contradicts durable Owner intent/decision or contains stale/hidden semantic mutation. |

Aggregate rule: any check `FAIL` ⇒ overall `FAIL` unless only Owner-resolvable
ambiguity remains (then `NEEDS_OWNER`). Prefer `NEEDS_OWNER` over guessing.

## Output contract

### 1) Human summary (first)

Short plain language. Examples:

PASS:

```text
Owner Contract согласован с OWNER_INTENT.
Неподтверждённых Owner decisions и внутренних противоречий не найдено.
Можно переходить к continue/ff.
```

NEEDS_OWNER:

```text
Контракт пока нельзя считать согласованным.
Нашёл решение, записанное как Owner decision без явного подтверждения: …
Нужно подтвердить или убрать.
```

### 2) Machine block

```text
OWNER_CONTRACT_REVIEW
CHANGE_ID: <change>

INTENT_PRESERVATION: PASS|FAIL|NEEDS_OWNER
OWNER_DECISION_PROVENANCE: PASS|FAIL|NEEDS_OWNER
INTERNAL_CONSISTENCY: PASS|FAIL|NEEDS_OWNER
TERMINOLOGY: PASS|FAIL|NEEDS_OWNER
SCOPE_INTEGRITY: PASS|FAIL|NEEDS_OWNER
ACCEPTANCE_COHERENCE: PASS|FAIL|NEEDS_OWNER
STALE_ASSUMPTIONS: PASS|FAIL
CONTRACT_VS_REALITY: PASS|CONFLICT|NOT_CHECKED

VERDICT: PASS|NEEDS_OWNER|FAIL
```

### 3) Findings

Each finding:

```text
FINDING_ID:
SEVERITY: critical | high | medium | low
CHECK: INTENT_PRESERVATION | OWNER_DECISION_PROVENANCE | INTERNAL_CONSISTENCY |
       TERMINOLOGY | SCOPE_INTEGRITY | ACCEPTANCE_COHERENCE |
       STALE_ASSUMPTIONS | CONTRACT_VS_REALITY
CONTRACT_TEXT:
SOURCE:
PROBLEM:
WHY_IT_MATTERS:
OWNER_QUESTION:   # only if Owner input is actually required
```

### 4) Footer (mandatory)

```text
MODE: READ_ONLY
FILES_CHANGED: none
```

### 5) Next action

```text
NEXT_ACTION:
  PASS         → /opsx-continue or /opsx-ff   (recommended)
  NEEDS_OWNER  → answer OWNER_QUESTION(s); durable-record; re-run this command
  FAIL         → Owner + owning writer fix owner-contract.md; re-run this command

DO_NOT_DO_YET:
  - do not treat PASS as implementation approval
  - do not edit owner-contract from this command
  - do not assume continue/ff will enforce this gate (v1 soft only)
```

## Self-check before return

- [ ] No files modified
- [ ] Did not rely on non-durable chat memory as OWNER_DECISION
- [ ] Did not promote EXPLORE_PROPOSAL / inference to OWNER_DECISION
- [ ] Did not choose technical implementation
- [ ] Human summary is short; dump only when findings exist
- [ ] Machine block present with all check keys
- [ ] Footer `MODE: READ_ONLY` / `FILES_CHANGED: none`
