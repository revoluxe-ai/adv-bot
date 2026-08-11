---
description: "READ_ONLY interactive semantic review of owner-contract.md: gather context, ask real Owner choices, emit OWNER_REVIEW_HANDOFF for /opsx-new, re-review. Never writes."
argument-hint: "change=<name> | path=<owner-contract.md> [paste EVOLUTION_HANDOFF / EXPLORE_HANDOFF / OWNER_REVIEW_HANDOFF] [Owner answers]"
---

# /opsx-owner-contract-review

Независимый **READ_ONLY** semantic review `owner-contract.md` после
`/opsx-new` и до создания `proposal` / `spec` / `design` / `tasks`.

Capability: `owner-contract-review`.

Единственный вопрос команды:

> Можно ли доказать по доступным **durable** artifacts, что Owner Contract
> сохраняет смысл Owner, не содержит неподтверждённых Owner decisions,
> внутренних противоречий и скрытого расширения scope — и если нет, можно
> ли довести review до готового repair handoff без того, чтобы Owner сам
> собирал recovery workflow?

## What this is

* Independent semantic reviewer (prefer **separate chat** from `/opsx-new`).
* Soft recommended precondition before `/opsx-continue` / `/opsx-ff`.
* Owner of the full **READ_ONLY review dialog**: gather missing durable
  context → ask only real Owner product choices → recompute → emit one
  deterministic `OWNER_REVIEW_HANDOFF` for `/opsx-new` → re-review after
  repair.
* Producer of `OWNER_CONTRACT_REVIEW` machine block + findings + (when
  ready) `OWNER_REVIEW_HANDOFF`.
* Source of truth = durable artifacts only (not prior chat reasoning),
  except Owner answers given **in this review cycle**, which the reviewer
  records into the handoff as `CONFIRMED_OWNER_DECISIONS`.

## What this is NOT

* NOT an implementation designer / technical variant picker.
* NOT a writer of `owner-contract.md`, Evolution, Explore, or planning
  artifacts (even when `OWNER_INPUT_REQUIRED: NO`).
* NOT Owner semantic authority (never replaces Owner approval).
* NOT a hard machine gate inside `continue` / `ff` / `apply` / `verify` /
  Supervisor (v1: recommend only; future hard-gate = separate Owner decision).
* NOT `/opsx-verify`, `/opsx-performance-review`, `/opsx-antipattern-gate`.
* NOT a batch-linter that dumps a long finding list and leaves recovery to
  Owner.

## Hard rules

* **READ_ONLY** end-to-end. Any file mutation = command failure.
* Do not auto-fix contradictions; report them and route via
  `REVIEW_STATE`.
* Do not invent product decisions or new scope.
* Chat-only confirmation that is **not** in a durable handoff/artifact
  **and** not an explicit Owner answer in this review cycle
  ⇒ **not** a proven `OWNER_DECISION` ⇒ `NEEDS_OWNER` / missing provenance
  (never `FAIL` solely for missing confirmation).
* Silence / no objection / answer to a neighboring question / agent proposal /
  repository evidence / “technical obviousness” ≠ Owner confirmation.
* Prefer Owner UI/product terms over internal enums; internal ids only as
  parenthetical gloss.
* Follow `.cursor/commands/opsx-source-resolution.md` and
  `.cursor/commands/opsx-execution-preflight.md` (Grep-first; parallel Read ≤ 2;
  no broad archaeology).
* Do **not** ask Owner to reconfirm semantics already proven by durable
  evidence; those become writer repairs (`OWNER_INPUT_REQUIRED: NO`).

## User input

```text
$ARGUMENTS
```

| Token | Effect |
|-------|--------|
| `change=<name>` | resolve `openspec/changes/<name>/owner-contract.md` |
| `path=<file>` | exact path to `owner-contract.md` |
| pasted `EVOLUTION_HANDOFF` / `EXPLORE_HANDOFF` | durable origin context |
| pasted `OWNER_REVIEW_HANDOFF` | prior repair handoff for re-review |
| Owner answers to pending `OWNER_QUESTION`s | continue same semantic cycle |
| unknown token | `STATUS=BLOCKED`, no file changes |

If neither `change=` nor `path=` and no resolvable single active change → ask
one concrete question; do not invent the change id.

## Pipeline position (soft)

```text
opsx-evolution
  → opsx-explore
  → opsx-new                    (writes / repairs owner-contract.md)
  → opsx-owner-contract-review  ← this command (separate chat, READ_ONLY)
  → NEEDS_CONTEXT / NEEDS_OWNER (same review dialog) as needed
  → READY_FOR_REPAIR + OWNER_REVIEW_HANDOFF
  → /opsx-new                   (sole writer of owner-contract.md)
  → opsx-owner-contract-review  (re-review until PASS)
  → opsx-continue / opsx-ff     (recommended after PASS; not hard-gated v1)
```

Authority:

```text
Owner                         → semantic decisions
opsx-owner-contract-review    → diagnosis + clarification + repair handoff
opsx-new                      → sole writer/repairer of owner-contract.md
```

## Source precedence

1. **OWNER_INTENT** — Owner wording / durable Owner correction only.
2. **OWNER_DECISIONS** — only explicitly confirmed Owner decisions with
   durable provenance (including answers recorded in this review cycle).
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
OWNER_REVIEW_HANDOFF → prior REPAIRS_REQUIRED / DO_NOT_CHANGE / CONFIRMED_*
```

Also as needed (bounded):

* relevant `openspec/specs/**`
* relevant Accepted `openspec/decisions/**`
* targeted archived changes for terminology/history
* current code/tests **only** for concrete CONTRACT_VS_REALITY claims

Regression fixtures (dry-run / acceptance):  
`.cursor/commands/_fixtures/owner-contract-review/`

## Interactive review flow (mandatory)

Reviewer owns a bounded clarification dialog. Do **not** after the first
run dump: answer N questions + paste handoffs + fix the contract + figure
out next steps.

```text
START
  ↓
read owner-contract.md
  ↓
discover available durable sources
  ↓
enough context for required checks?
  ├─ NO → REVIEW_STATE: NEEDS_CONTEXT
  │        ask only the concrete missing source
  │        (e.g. paste EVOLUTION_HANDOFF entirely)
  │        ↓ Owner supplies → re-enter flow
  └─ YES
  ↓
run mandatory checks / findings
  ↓
any finding with OWNER_INPUT_REQUIRED: YES
and semantics not yet answered in this cycle?
  ├─ YES → REVIEW_STATE: NEEDS_OWNER
  │        ask only real product choices (compact set if independent)
  │        ↓ Owner answers → record into CONFIRMED_OWNER_DECISIONS
  │        → recompute findings
  └─ NO
  ↓
contract already matches proven semantics?
  ├─ YES → REVIEW_STATE: PASS
  └─ NO  → REVIEW_STATE: READY_FOR_REPAIR
           emit OWNER_REVIEW_HANDOFF
           REPAIR_COMMAND: /opsx-new
           AFTER_REPAIR: /opsx-owner-contract-review change=<change>
```

Priority inside one cycle:

1. Obtain missing durable context first.
2. Recompute findings.
3. Ask only unresolved real Owner decisions.
4. Do not ask what durable evidence already proves.
5. After answers, recompute again.
6. Only then emit repair handoff.

If context is already sufficient on first invocation, proceed directly to
`PASS`, `NEEDS_OWNER`, or `READY_FOR_REPAIR` — do not invent questions.

## Review state model

Exactly one `REVIEW_STATE` per response:

| State | When |
|-------|------|
| `NEEDS_CONTEXT` | Required durable source missing; check cannot complete. **Not FAIL.** |
| `NEEDS_OWNER` | Real semantic/product choice cannot be resolved from proven Owner statements. **Not FAIL.** |
| `READY_FOR_REPAIR` | Context + Owner choices sufficient; contract text still wrong; writer repairs known. |
| `PASS` | Current `owner-contract.md` matches proven Owner semantics; no material contradictions / stale assumptions / unproven Owner decisions. |
| `FAIL` | Sufficient evidence shows contract is wrong **and** the cycle cannot go to PASS without repair — use only when routing to repair is blocked **or** as legacy synonym under `READY_FOR_REPAIR` for per-check FAIL labels. Prefer `READY_FOR_REPAIR` whenever repairs are knowable. |

Hard distinctions:

```text
missing context          ≠ FAIL  → NEEDS_CONTEXT
missing Owner decision   ≠ FAIL  → NEEDS_OWNER
proven writer defect     ≠ NEEDS_OWNER → READY_FOR_REPAIR
```

Per-check results may still be `FAIL` while `REVIEW_STATE: READY_FOR_REPAIR`
(example: `INTERNAL_CONSISTENCY: FAIL` + repairable stale acceptance).

Do **not** mask recovery as overall `VERDICT: NEEDS_OWNER` when Owner input
is not required.

## Mandatory checks

### 1. INTENT_PRESERVATION

Compare `OWNER_INTENT` to «Что хотим получить», «Зачем», and main acceptance
statements. Same object of change? Same user-visible result? No silent
technical reframe? No dropped essential intent?

If `OWNER_INTENT` source is missing → `NEEDS_CONTEXT` (request that source),
not `FAIL`.

### 2. OWNER_DECISION_PROVENANCE

For each material bullet under `## Решения Owner`, require durable explicit
Owner confirmation. Partial answers confirm **only** what was answered.

Critical regression: agent proposes `PLAN_DISTANCE only` + module ON; Owner
says only “module ON” ⇒ `PLAN_DISTANCE only` must **not** be treated as
confirmed.

If the bullet is an unconfirmed agent proposal → finding with
`OWNER_INPUT_REQUIRED: YES` **or** `REPAIR_REQUIRED: YES` to remove the
unproven bullet (prefer remove/repair when Owner already declined / only
answered the other part — do not re-ask module ON).

### 3. INTERNAL_CONSISTENCY

Conflicts among want / keep / out-of-scope / acceptance / Owner decisions.
Report conflict; do **not** pick the “correct” wording unless durable
evidence already proves which side is Owner semantics — then
`OWNER_INPUT_REQUIRED: NO` + `REPAIR_REQUIRED: YES`.

### 4. TERMINOLOGY_DISAMBIGUATION

Disambiguate overloaded product terms (e.g. «полки» = WB Auto placement vs
bot module «Управление ставкой в полках»). Ambiguous with no durable
disambiguation ⇒ `OWNER_INPUT_REQUIRED: YES` + `REVIEW_STATE: NEEDS_OWNER`.

### 5. SCOPE_INTEGRITY

No unconfirmed capability / mode / constraint; no dropped essential intent;
no FUTURE/OUT_OF_SCOPE smuggled into current Change via CURRENT_INCREMENT /
KEEP / HARD / FORWARD / EXPLORE_PROPOSALS / CANDIDATE_MAPPING.

### 6. ACCEPTANCE_COHERENCE

«Как поймём, что получилось» must prove Owner intent: observable, mutually
consistent, respects higher-priority constraints, not a technical proxy for
the real result. Do **not** design tests — only semantic adequacy.

Regression (auto-shelf): acceptance «через N суток Авто снова включается»
while durable decision is «снимается только наш block; другие blockers могут
держать Auto остановленным» ⇒ `OWNER_INPUT_REQUIRED: NO`,
`REPAIR_REQUIRED: YES`, `REVIEW_STATE: READY_FOR_REPAIR`.

### 7. STALE_ASSUMPTION_CHECK

After Owner correction, old meaning must not remain in other sections
(invariants / acceptance / out of scope / decisions / summary).

### 8. CONTRACT_VS_REALITY

Only when contract asserts current behavior (“сейчас X работает так”):
targeted specs/code/tests check. On mismatch →
`CONTRACT_VS_REALITY: CONFLICT` with Owner desired vs current — do **not**
rewrite Owner intent.

## Findings contract

Each actionable finding:

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

OWNER_INPUT_REQUIRED: YES|NO

OWNER_QUESTION:
<only if OWNER_INPUT_REQUIRED: YES>

REPAIR_REQUIRED: YES|NO
REPAIR_SEMANTICS:
<if already knowable — desired contract meaning>
```

Rules:

* `OWNER_INPUT_REQUIRED: NO` ⇒ do **not** emit `OWNER_QUESTION`.
* Proven durable semantics + wrong contract text ⇒ writer defect, not Owner
  quiz.
* Missing confirmed decision that is still a live product fork ⇒
  `OWNER_INPUT_REQUIRED: YES`.

## OWNER_REVIEW_HANDOFF (required at READY_FOR_REPAIR)

Emit one self-contained block transferable to `/opsx-new` without extra
prose:

```text
OWNER_REVIEW_HANDOFF
CHANGE_ID: <change>

REVIEW_SOURCE:
- owner-contract.md: <path>
- OWNER_INTENT: <source>
- OWNER_DECISIONS: <sources>
- relevant handoffs: <sources>

CONFIRMED_OWNER_DECISIONS:
- D-01: <full semantic statement — not "Owner chose A">
- ...

REPAIRS_REQUIRED:

R-001
SECTION: <section>
CURRENT_TEXT: <current problematic meaning/text>
PROBLEM: <semantic defect>
REQUIRED_SEMANTICS: <what contract must say>
OWNER_INPUT_REQUIRED: NO
SOURCE: <durable evidence>

R-002
...

DO_NOT_CHANGE:
- <confirmed semantics not implicated by findings>
- ...

REPAIR_BOUNDARY:
- modify owner-contract.md only
- do not create proposal/spec/design/tasks
- do not reinterpret OWNER_INTENT
- do not introduce new product decisions

REPAIR_COMMAND:
/opsx-new

AFTER_REPAIR:
/opsx-owner-contract-review change=<change>
```

Notes:

* Verbatim patch text optional; desired semantics + evidence mandatory.
* New Owner answers from this cycle **must** appear under
  `CONFIRMED_OWNER_DECISIONS` as full semantics (chat-stable).
* Never route repair as “Owner + owning writer”, “manual edit”, or vague
  “owning writer”. Always `REPAIR_COMMAND: /opsx-new`.

If `/opsx-new` cannot safely apply the handoff (no repair-only mode for an
existing change), still emit the handoff and add:

```text
DEPENDENCY_FOUND:
/opsx-new lacks REPAIR mode for OWNER_REVIEW_HANDOFF on existing change
```

Do **not** silently redesign `/opsx-new` from this command.

## Re-review behavior

After `/opsx-new` repair, accept:

```text
change=<change>
+ OWNER_REVIEW_HANDOFF   (pasted or recovered from this review conversation)
```

Verify:

1. Every `REPAIRS_REQUIRED` item is actually fixed in current
   `owner-contract.md`.
2. `DO_NOT_CHANGE` semantics were not altered.
3. No new semantic mutations appeared.
4. Owner decisions are represented correctly.
5. Result is internally consistent.

Outcomes:

* all hold → `REVIEW_STATE: PASS`
* repairs incomplete / regression → new bounded findings →
  `NEEDS_OWNER` or `READY_FOR_REPAIR` (new handoff), never dump recovery
  onto Owner.

## Output contract

### 1) Human summary (first)

Short plain language. Examples:

`NEEDS_CONTEXT`:

```text
Для provenance не хватает EVOLUTION_HANDOFF.
Вставьте его целиком — после этого продолжу review.
```

`NEEDS_OWNER`:

```text
Остался один product question (ниже).
После ответа продолжу review в этом же цикле.
```

`READY_FOR_REPAIR`:

```text
Все нужные semantic decisions определены.
Контракт требует writer repairs — ниже OWNER_REVIEW_HANDOFF для /opsx-new.
```

`PASS`:

```text
Owner Contract согласован с доказанной Owner-семантикой.
Неподтверждённых Owner decisions и внутренних противоречий не найдено.
Можно переходить к continue/ff.
```

### 2) Machine block

```text
OWNER_CONTRACT_REVIEW
CHANGE_ID: <change>
REVIEW_STATE: NEEDS_CONTEXT | NEEDS_OWNER | READY_FOR_REPAIR | PASS | FAIL

INTENT_PRESERVATION: PASS|FAIL|NEEDS_OWNER|NEEDS_CONTEXT
OWNER_DECISION_PROVENANCE: PASS|FAIL|NEEDS_OWNER|NEEDS_CONTEXT
INTERNAL_CONSISTENCY: PASS|FAIL|NEEDS_OWNER
TERMINOLOGY: PASS|FAIL|NEEDS_OWNER
SCOPE_INTEGRITY: PASS|FAIL|NEEDS_OWNER
ACCEPTANCE_COHERENCE: PASS|FAIL|NEEDS_OWNER
STALE_ASSUMPTIONS: PASS|FAIL
CONTRACT_VS_REALITY: PASS|CONFLICT|NOT_CHECKED

VERDICT: PASS|NEEDS_CONTEXT|NEEDS_OWNER|READY_FOR_REPAIR|FAIL
```

`VERDICT` MUST equal `REVIEW_STATE` (compatibility alias). Prefer reading
`REVIEW_STATE`.

### 3) Findings

Use the findings contract above. Omit empty finding dump when
`NEEDS_CONTEXT` and checks have not run yet — state the missing source.

### 4) OWNER_REVIEW_HANDOFF

Required when `REVIEW_STATE: READY_FOR_REPAIR`. Omit otherwise.

### 5) Footer (mandatory)

```text
MODE: READ_ONLY
FILES_CHANGED: none
```

### 6) Next action

```text
NEXT_ACTION:
  NEEDS_CONTEXT     → supply the exact requested durable source; re-invoke
                      or continue in this chat
  NEEDS_OWNER       → answer OWNER_QUESTION(s); continue same review cycle
  READY_FOR_REPAIR  → run REPAIR_COMMAND (/opsx-new) with OWNER_REVIEW_HANDOFF;
                      then AFTER_REPAIR
  PASS              → /opsx-continue or /opsx-ff (recommended)
  FAIL              → treat as READY_FOR_REPAIR when repairs known;
                      otherwise escalate with explicit blocker

DO_NOT_DO_YET:
  - do not treat PASS as implementation approval
  - do not edit owner-contract from this command
  - do not assume continue/ff will enforce this gate (v1 soft only)
  - do not ask Owner to manually invent recovery or rewrite the contract
```

## Self-check before return

- [ ] No files modified
- [ ] Did not rely on non-durable chat memory as OWNER_DECISION (except
      explicit Owner answers recorded this cycle into the handoff)
- [ ] Did not promote EXPLORE_PROPOSAL / inference to OWNER_DECISION
- [ ] Did not choose technical implementation
- [ ] Did not ask Owner questions where `OWNER_INPUT_REQUIRED: NO`
- [ ] Did not end as FAIL solely for missing context or missing Owner choice
- [ ] `READY_FOR_REPAIR` includes `OWNER_REVIEW_HANDOFF` + `REPAIR_COMMAND: /opsx-new`
- [ ] Human summary is short; dump only when findings exist
- [ ] Machine block present with `REVIEW_STATE` and all check keys
- [ ] Footer `MODE: READ_ONLY` / `FILES_CHANGED: none`
