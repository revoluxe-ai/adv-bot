---
name: /opsx-apply
id: opsx-apply
category: Workflow
description: Implement tasks from an OpenSpec change (Experimental)
---

Implement tasks from an OpenSpec change.

**Store selection:** If the user names a store (a store is a standalone OpenSpec repo registered on this machine) or the work lives in one, run `openspec store list --json` to discover registered store ids, then pass `--store <id>` on the commands that read or write specs and changes (`new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`). Other commands do not take the flag. Hints printed by commands already carry the flag; keep it on follow-ups. Without a store, commands act on the nearest local `openspec/` root.

**Semantic write-target preflight:** Follow
`.cursor/pipeline/contracts/SEMANTIC_WRITE_TARGET.md`. After context/decision
read and **before any production edit**, re-check the semantic write target for
high-risk multi-target mutations. `RESOLVED` requires planned symbols to be in
`ALLOWED_ADAPTERS` and outside `FORBIDDEN_ADAPTERS`. Unresolved or chat-only
Owner answers return `NO_GO` / `BLOCKED_NEEDS_OWNER_SEMANTIC_DECISION` and route
to `/opsx-update` (or another planning writer) for durable materialization —
never guess Auto vs Search or equivalent legs from similar names.

**Product Acceptance:** Follow
`.cursor/pipeline/contracts/PRODUCT_ACCEPTANCE.md`. When
`PRODUCT_ACCEPTANCE_REQUIRED=true`, do not edit production code if MEANING_LOCK
is missing/blocked. Author acceptance tests with `side_effect_proof` /
`PA_SIDE_EFFECT_PROOF` for external mutations (this-run effect or forbidden
sibling non-effect). Task checkboxes and soft tooling green are not DONE.

**Planning-review soft preflight (v1, not a hard gate):** Prefer a recent
`/opsx-planning-review change=<name>` with `STATUS: PASS` /
`APPLY_PLANNING_GATE: PASS` before implementing. If the Owner has not just
completed that review for this change, soft-recommend it once (READY markers
alone are insufficient — `.cursor/pipeline/contracts/PLANNING_REVIEW.md`).
Do **not** hard-block `/opsx-apply` when review was skipped.

**Architecture Decision Lookup:** Before changing code, resolve decision paths from the selected change context/`artifactPaths.decisions` first. Prefer exact listed paths over a full `openspec/decisions/**` walk. Follow `.cursor/commands/opsx-source-resolution.md` and `.cursor/commands/opsx-execution-preflight.md`: when the change name is known, do not rediscover it by scanning all changes; do not gate apply on unconditional `git status`—run git only when dirty-tree / branch identity is REQUIRED_FOR safe implementation. Search `openspec/decisions/**/*.md` only for remaining gaps after direct context paths are read (budget ≤ 3 targeted lookups unless `EVIDENCE_GAP` is recorded). Do **not** equate budget exhaustion with “no decision exists”: if ownership / layering / write-path / domain-invariant gaps remain unresolved after that budget (a relevant accepted decision may still be unread), record `EVIDENCE_GAP` and return `NO_GO` without editing code. Use `Architecture Decision Missing` only when lookup within budget (or after a recorded `EVIDENCE_GAP` expansion) concludes no relevant decision. Implementation must cite relevant decisions in progress or completion notes. If planned code placement contradicts an accepted decision, stop before editing code and return `NO_GO` with the conflicting decision path. If placement depends on a proposed decision, use `openspec instructions decisions --change "<name>" --json` so `rules.decisions` are applied before deciding whether code can proceed. Passing tests are not sufficient if placement violates a decision.

**Canonical testing rule:** Before implementation, read `.cursor/rules/testing-rules.mdc` as the only general test-design/execution policy. Do not treat `.cursor/rules/TESTING_RULES.mdc` as policy (migration pointer only). Do not copy large test-policy blocks into this command; follow the authority split below.

**PG session mode:** New/changed production `sm(...)` / `get_async_session_maker(...)` MUST use explicit `read_only=` per intent (WRITE/RAW → `False`, PURE_READ → `True`). Bare `sm()` forbidden — see testing-rules § PG session mode; coverage will WEAK `PG_IMPLICIT_SESSION_MODE`.
For PG/CH testability seams, default to parent→child handoff: open session/client in the parent orchestration callable and pass it to the child callable that performs store work; avoid hidden session/client creation only inside deep child callables.

**Authority split for tests:**

- `.cursor/rules/testing-rules.mdc` — general test-design and execution
- `openspec/config.yaml` → `rules.tasks` — task-generation obligations
- `/opsx-invariant` → change-specific `TEST_COVERAGE_PACKET`
- `/opsx-apply` — implementation + test materialization for owning tasks
- `/opsx-pyright-strict-coverage` — post-apply soft recommend when production `.py` changed
- `/opsx-external-call-coverage` — after pyright-coverage PASS; soft recommend for external surfaces in diff
- `/opsx-performance-review` — after external-call PASS when performance trigger applies (DB/query/queue/concurrency/pool/retry); soft recommend, not every-diff hard gate
- `/opsx-verify` — phased READ_ONLY audit via
  `.cursor/pipeline/contracts/VERIFY_PHASES.md` (`mode=impl` DoD, then later
  `mode=archive` archive GO)

**Input**: Optionally specify a change name (e.g., `/opsx-apply add-auth`). If omitted, check if it can be inferred from conversation context. If vague or ambiguous you MUST prompt for available changes.

**Steps**

1. **Select the change**

   If a name is provided, use it. Otherwise:
   - Infer from conversation context if the user mentioned a change
   - Auto-select if only one active change exists
   - If ambiguous, run `openspec list --json` to get available changes and use the **AskUserQuestion tool** to let the user select

   Always announce: "Using change: <name>" and how to override (e.g., `/opsx-apply <other>`).

2. **Check status to understand the schema**
   ```bash
   openspec status --change "<name>" --json
   ```
   Parse the JSON to understand:
   - `schemaName`: The workflow being used (e.g., "spec-driven")
   - `planningHome`, `changeRoot`, and `actionContext`: planning scope and edit constraints
   - Which artifact contains the tasks (typically "tasks" for spec-driven, check status for others)

3. **Get apply instructions**

   ```bash
   openspec instructions apply --change "<name>" --json
   ```

   This returns:
   - `contextFiles`: artifact ID -> array of concrete file paths (varies by schema)
   - Progress (total, complete, remaining)
   - Task list with status
   - Dynamic instruction based on current state

   **Handle states:**
   - If `state: "blocked"` (missing artifacts): show message, suggest using `/opsx-continue`
   - If `state: "all_done"`: congratulate, then follow **Post-apply next-step recommend** below (not archive readiness)
   - Otherwise: proceed to implementation

4. **Read context files**

   Read file paths listed under `contextFiles` from the apply instructions output,
   under execution-preflight Read I/O budgets (prefer sequential; parallel max 2;
   large artifacts via section Read when only a part is needed).
   The files depend on the schema being used:
   - **spec-driven**: proposal, specs, design, tasks, and optional decisions when present
   - Other schemas: follow the contextFiles from CLI output

5. **Read canonical testing rule and optional TEST_COVERAGE_PACKET**

   - Always read `.cursor/rules/testing-rules.mdc` before editing code or tests.
   - Search current change artifacts / context files for a `TEST_COVERAGE_PACKET` block.
   - If found, extract its required behavioral / sibling / residual scenarios, reality and mocking constraints, and minimum test level.
   - Absence of `TEST_COVERAGE_PACKET` does **not** block legacy apply.
   - Packet status (`ready` / `provisional` / `not_materialized` / `not_applicable`) by itself does **not** block implementation.
   - Do not invent mandatory scenarios without evidence from spec, decision, task, invariant, or a materialized packet.
   - Do not modify an invariant only to make a test convenient.
   - Do not declare final test adequacy or archive readiness; that belongs to `/opsx-verify`.

6. **Perform Architecture Decision Lookup**

   - Resolve paths from `contextFiles.decisions` / `artifactPaths.decisions` / user-supplied paths first.
   - Read `openspec/decisions/index.md` only if still needed to locate candidates.
   - Search/read further under `openspec/decisions/` **only** for remaining gaps after direct context (budget ≤ 3 targeted lookups unless `EVIDENCE_GAP` is recorded). Never dump the full decision tree.
   - If the ≤ 3 fallback budget is exhausted while ownership / layering / write-path / domain-invariant gaps remain unresolved (a relevant accepted decision may still be unread), record `EVIDENCE_GAP` and return `NO_GO` without editing code. Budget exhaustion is not proof that no decision exists.
   - Read existing proposed decisions from `contextFiles.decisions` or `artifactPaths.decisions.existingOutputPaths`, if any.
   - Output `Architecture Decisions Found` with relevant decision paths and statuses.
   - If the change touches ownership, layering, write paths, or domain invariants and lookup within budget (or after a recorded `EVIDENCE_GAP` expansion) concludes no relevant decision, output `Architecture Decision Missing` and pause unless the artifacts already include a proposed decision.
   - If a proposed decision is required or present, get `openspec instructions decisions --change "<name>" --json` and apply `rules.decisions` before evaluating placement.
   - Compare planned implementation placement against accepted/proposed decisions before editing code.
   - If placement conflicts with an accepted decision, return `NO_GO` and do not edit code.

6a. **Semantic write-target preflight (before production edit)**

   Follow `.cursor/pipeline/contracts/SEMANTIC_WRITE_TARGET.md`:
   - If the change is not a high-risk multi-target write → `NOT_APPLICABLE` /
     proceed only when justified (single proven target).
   - If artifacts durably resolve `TARGET_ENTITY_OR_LEG`, `ALLOWED_ADAPTERS`,
     `FORBIDDEN_ADAPTERS`, evidence, Owner decision source, and paired tests →
     `RESOLVED`; planned write symbols MUST be in `ALLOWED_ADAPTERS` and MUST
     NOT be in `FORBIDDEN_ADAPTERS`.
   - If multiple plausible targets remain, or resolution exists only in chat →
     return `NO_GO` with `BLOCKED_NEEDS_OWNER_SEMANTIC_DECISION`, ask the
     contract's single Owner question, and route to `/opsx-update`. Do not edit
     production code. Do not close competing legs with `NOT_APPLICABLE`.

6b. **Product Acceptance preflight (before production edit)**

   Follow `.cursor/pipeline/contracts/PRODUCT_ACCEPTANCE.md`:
   - If `PRODUCT_ACCEPTANCE_REQUIRED=true` and MEANING_LOCK is not durable →
     `NO_GO`; route to `/opsx-update` / Owner semantic decision.
   - If `PRODUCT_ACCEPTANCE_REQUIRED=true` and temporal behavior applies:
     - **Primary:** durable Derived Lifecycle
       (`LIFECYCLE_STATUS: DERIVED` in design, from reviewed Owner Contract)
       must be present (or unambiguously derivable without invention). Do
       **not** `NO_GO` solely for absent `CONFIRM_LIFECYCLE` /
       `OWNER_LIFECYCLE_ECHO` on this path.
     - **Unresolved forks:** `LIFECYCLE_STATUS: UNRESOLVED` → `NO_GO`;
       route to `/opsx-owner-contract-review`.
     - **Legacy** (no reviewed owner-contract): missing/chat-only
       `OWNER_LIFECYCLE_ECHO` or missing `CONFIRM_LIFECYCLE` → `NO_GO`;
       route to `/opsx-update` (or `/opsx-ff`).
     Do not implement against chat-only lifecycle.
   - When implementing acceptance seams with external mutation, materialize
     tests that satisfy SIDE_EFFECT_PROOF (`side_effect_proof` /
     `PA_SIDE_EFFECT_PROOF` in TEST_EVIDENCE_TAXONOMY). Intent-only /
     OR-armed proxies without this-run effect are insufficient for later
     archive DONE.
   - Do not treat apply completion alone as Product Acceptance PASS.

7. **Show current progress**

   Display:
   - Schema being used
   - Progress: "N/M tasks complete"
   - Remaining tasks overview
   - Whether `TEST_COVERAGE_PACKET` was found (present / absent) and its status if present
   - Dynamic instruction from CLI

8. **Implement tasks (loop until done or blocked)**

   For each pending task:
   - Show which task is being worked on
   - Make the code changes required
   - Keep changes minimal and focused
   - Materialize materialized test obligations from the owning task together with that task when they are required by:
     - the task text;
     - `openspec/config.yaml` → `rules.tasks`;
     - `.cursor/rules/testing-rules.mdc`;
     - and/or a present `TEST_COVERAGE_PACKET` with applicable required scenarios
   - When those obligations apply:
     - do not create phantom model/DTO fields or impossible states;
     - do not fully mock the causal boundary under test;
     - materialize allowed sibling and residual/repeated-invocation scenarios when the packet/spec/task makes them mandatory;
     - for Spec Scenario write/notify **thin ends** (WB pause/start, notify,
       Telegram transport, etc.): prefer shared `ContractCase` + recording fake
       in `tests/**` at the thin end (see
       `.cursor/pipeline/contracts/SCENARIO_TEST_COVERAGE.md` /
       `/opsx-spec-scenario-coverage`). Bare `MagicMock`/`AsyncMock` without
       ContractCase is allowed only with explicit `TEST_DEBT` in task notes
       listing stub symbols → `/opsx-test` (do not invent production APIs);
     - run focused/targeted tests for the changed slice (and adjacent tests when a neighboring contract/workflow is affected)
   - Do **not** mark the task complete (`- [ ]` → `- [x]`) if its mandatory tests fail
   - Mark task complete in the tasks file only after required implementation and mandatory focused tests for that task succeed: `- [ ]` → `- [x]`
   - Continue to next task

   **Pause if:**
   - Task is unclear → ask for clarification
   - Implementation reveals a design issue → suggest updating artifacts
   - Error or blocker encountered → report and wait for guidance
   - User interrupts

9. **On completion or pause, show status**

   Display:
   - Tasks completed this session
   - Overall progress: "N/M tasks complete"
   - If all done: follow **Post-apply next-step recommend** (do not claim archive readiness)
   - If paused: explain why and wait for guidance

### Post-apply next-step recommend

После completion / `all_done` выбери **один** pasteable primary `NEXT_ACTION`
по правилам ниже (soft recommend; не hard gate archive).
Authority for bug close/handback:
`.cursor/pipeline/contracts/bug-episode/CLOSE_POLICY.md`.

**Bug-episode first** (when `case=`/`finding=` present or ROUTE_STATE ties
this change to a durable case):

1. **Never** write `closed_fixed` / close CASE from apply.
2. Read durable `CLOSE_FINDING_INTENT` / `POST_GREEN_OWNER` /
   `HANDBACK_COMMAND` from LEDGER (do not invent from chat).
3. **PRIMARY** `NEXT_ACTION`:
   `/opsx-test case=<CASE_ID> finding=<FINDING_ID> verify`
4. **SECONDARY** (always emit pasteable, no silent return):
   `HANDBACK_COMMAND` or
   `/opsx-bug-team case=<CASE_ID> mode=resume-family-fanout`
5. **ALSO_OK**: continue OpenSpec soft chain below (solo walk / coverage);
   Owner may ignore handback — not a violation.
6. Coverage recommends (pyright → ecc → …) remain **additional** after
   GREEN path is stated, when production `.py` changed.

**OpenSpec-only** (no bug case context):

0. **PRIMARY** всегда сначала DoD-фаза (VERIFY_PHASES):
   `/opsx-verify mode=impl <change-name>`
   `✅ IMPL_OK` ≠ archive; `❌ IMPL_GAPS` → apply/update, не quality chain
   как замена DoD.

1. После `IMPL_OK`, если есть **in-policy production Python**
   (`app/**/*.py` или top-level production `*.py` в корне, не `tests/**`):
   - Next: `/opsx-pyright-strict-coverage base=<BASE>`
   - Если `BASE` неизвестен — спроси один раз: «На какую base branch/ref
     сверять pyright-strict / external-call coverage?» Не выдумывай base.
   - After pyright-coverage `PASS`: recommend
     `/opsx-external-call-coverage base=<BASE>`, затем после его `PASS`
     (`focus=all`):
     - если diff попадает под performance trigger
       (`PERFORMANCE_REVIEW_REQUIRED` / `RECOMMENDED` —
       DB/query/repository; Queue/TasksManager/`run_tasks`/`gather`/
       `create_task`; Semaphore/Lock/Redis NX; pool/cap/rate-limit/
       retry/backpressure; или неоднозначный hot async path) →
       `/opsx-performance-review scope=base base=<BASE>`;
     - иначе → `/opsx-antipattern-gate base=<BASE>`;
     - после performance `PASS` | `PASS_WITH_RISK` (или
       `NOT_APPLICABLE` / empty surfaces) →
       `/opsx-antipattern-gate base=<BASE>`;
     - после antipattern-gate `PASS` | `PASS_WITH_SUSPECTS`
       (Owner may continue with suspects) → `/opsx-static-check`,
       затем `/opsx-verify mode=archive <change-name>`.
   - Performance review **не** обязателен для каждого diff
     (docs/typing-only / нерелевантный tests-only → skip).
   - Antipattern-gate — soft over-report; не archive gate. `FAIL` →
     fix pasteable exit или `accept=`/`reject=` practice ledger, затем
     re-run `/opsx-antipattern-gate base=<BASE>`.
2. После `IMPL_OK`, если нет in-policy production `.py`:
   - Next: `/opsx-verify mode=archive <change-name>`.
   - Если в diff есть `tests/**` / process surfaces — soft recommend
     `/opsx-antipattern-gate base=<BASE> focus=tests|process` before archive verify.

Не объявляй archive readiness из apply.
Не объявляй bug-card closed из apply.
`DO_NOT_DO_YET: /opsx-archive` until `mode=archive` ✅ GO.

**Output During Implementation**

```
## Implementing: <change-name> (schema: <schema-name>)

Working on task 3/7: <task description>
[...implementation happening...]
✓ Task complete

Working on task 4/7: <task description>
[...implementation happening...]
✓ Task complete
```

**Output On Completion**

```
## Implementation Complete

**Change:** <change-name>
**Schema:** <schema-name>
**Progress:** 7/7 tasks complete ✓

### Completed This Session
- [x] Task 1
- [x] Task 2
...

Implementation tasks complete.

Always first:
  Next: `/opsx-verify mode=impl <change-name>`
If production Python changed (`app/**/*.py` or top-level production scripts)
after IMPL_OK:
  Then: `/opsx-pyright-strict-coverage base=<BASE>`
  Then: `/opsx-external-call-coverage base=<BASE>` (after pyright PASS)
  Then: `/opsx-performance-review scope=base base=<BASE>` when trigger applies
        (else skip)
  Then: `/opsx-antipattern-gate base=<BASE>` (after external-call PASS, and
        after performance PASS|PASS_WITH_RISK when review ran)
  Then: `/opsx-static-check` (after antipattern-gate PASS|PASS_WITH_SUSPECTS)
  Then: `/opsx-verify mode=archive <change-name>`
Else after IMPL_OK:
  Next: `/opsx-verify mode=archive <change-name>`
  Soft: `/opsx-antipattern-gate base=<BASE> focus=tests|process` when those
        paths changed

Do not claim archive readiness from apply alone.
DO_NOT_DO_YET: `/opsx-archive` until mode=archive ✅ GO.
```

**Output On Pause (Issue Encountered)**

```
## Implementation Paused

**Change:** <change-name>
**Schema:** <schema-name>
**Progress:** 4/7 tasks complete

### Issue Encountered
<description of the issue>

**Options:**
1. <option 1>
2. <option 2>
3. Other approach

What would you like to do?
```



## Bug-episode RED + Owner GO gate

Authority: `.cursor/pipeline/ORCHESTRATION_MVP.md` §1.

When `/opsx-apply` is the bug-episode implementation executor
(`ROUTE_STATE.EXPECTED_EXECUTION_ROUTE=/opsx-apply` or request includes
`case=`/`finding=` after `TASK_DELTA: CHANGED`):

Production implementation is allowed only if:

```text
BUG_CONFIRMED
AND FIX_NOW
AND (
  RED_CONFIRMED
  OR RED_NOT_APPLICABLE_APPROVED
)
AND OWNER_PRODUCTION_GO
```

Hard stops:

* missing classify → `blocked_needs_classify_first` → `/opsx-classify-bug …`
* missing/failed TASK_DELTA YES route → do not apply; return to update/fix-bug
* missing RED → `blocked_needs_red_before_go` → `/opsx-test case= finding=`
* missing Owner GO → do not edit production; wait for Owner

`/opsx-update` is never a substitute for Owner GO.
`TASK_DELTA: CHANGED` is never automatic production permission.

On bug-episode apply start set:

```text
ACTUAL_EXECUTION_ROUTE: /opsx-apply
ROUTE_RECONCILIATION: MATCH | MISMATCH
```

MISMATCH -> BLOCKED_ROUTE_MISMATCH (no production edits).
Also require TASK_DELTA: CHANGED and EXPECTED_EXECUTION_ROUTE=/opsx-apply.


Append ROUTE-TRACE event for `apply`. Update `## ROUTE_STATE`.

Normal OpenSpec apply **without** bug-episode case context keeps the
existing change-lifecycle apply behavior (no RED gate).


## Route-trace event requirements (SCHEMA_VERSION 2)

Authority: `.cursor/pipeline/contracts/bug-episode/ROUTE_TRACE.md`.

On every significant hop that touches a durable case map, append **one**
JSONL event to:

```text
.tmp/opsx-bug-cases/<CASE_ID>/results/ROUTE-TRACE.jsonl
```

Mandatory identity/order fields on every event:

```text
SCHEMA_VERSION
EVENT_ID
EVENT_SEQUENCE
CASE_ID
FINDING_ID
EVENT_TYPE
COMMAND
ACTOR_ROLE
ACTOR_AGENT_ID
ACTOR_CHAT_ID
FROM_STATE
TO_STATE
STARTED_AT
COMPLETED_AT
DURATION_MS
TERMINAL_STATUS
PREVIOUS_EVENT_ID
```

Actor identity:

```text
ACTOR_AGENT_ID: CURRENT_CHAT_AGENT  # if no separate agent id
ACTOR_CHAT_ID:  durable stable chat label (required; not free-text role alone)
```

When this command **selects** or **executes** an implementation route, also set:

```text
EXPECTED_EXECUTION_ROUTE
ACTUAL_EXECUTION_ROUTE
ROUTE_RECONCILIATION   # PENDING | MATCH | MISMATCH | NOT_APPLICABLE
RECONCILIATION_REASON
```

Mismatch → `BLOCKED_ROUTE_MISMATCH` (no production GO; no silent episode close).
Refresh LEDGER `## ROUTE_STATE` to match the latest event (snapshot only).
Never rewrite prior JSONL lines.

**Guardrails**
- Keep going through tasks until done or blocked
- Always read context files before starting (from the apply instructions output)
- Always read `.cursor/rules/testing-rules.mdc` before implementation
- Read `TEST_COVERAGE_PACKET` when present in change artifacts/context; absence does not block legacy apply
- Packet status alone does not block implementation and does not equal verify/archive verdict
- Always perform Architecture Decision Lookup before code edits
- Always perform Semantic write-target preflight before production edits
- Stop with `NO_GO` when the decision-lookup fallback budget is exhausted while ownership / layering / write-path / domain-invariant gaps remain unresolved
- Stop with `NO_GO` when planned placement conflicts with an accepted architecture decision
- Stop with `NO_GO` / `BLOCKED_NEEDS_OWNER_SEMANTIC_DECISION` when a high-risk
  write has multiple plausible targets or when Owner resolution is chat-only;
  route to `/opsx-update` for durable artifact materialization
- Stop with `NO_GO` when planned write symbols are in `FORBIDDEN_ADAPTERS` or
  outside `ALLOWED_ADAPTERS` after a resolved semantic target
- If task is ambiguous, pause and ask before implementing
- If implementation reveals issues, pause and suggest artifact updates
- Keep code changes minimal and scoped to each task
- For new/changed PG/CH boundaries, prefer parent-opened session/client passed into child callables that execute DB/CH logic; treat hidden child-only session/client creation as a refactor gap unless explicitly justified by design constraints
- After implementing tasks, treat any new production/exported symbol whose only callers are tests as dead surface: wire it into a runtime-reachable path or remove it before completion. Passing tests do not prove wiring.
- Update task checkbox immediately after completing each task; never mark `[x]` when mandatory tests for that task fail
- When a completed task closes a decision-delta, sync every status mirror in the same pass: the tasks.md checkbox, the decision.md review-checklist annotation, and the design.md checklist/status mirror if present. Do not leave a shipped delta marked "proposed / not yet applied".
- Pause on errors, blockers, or unclear requirements - don't guess product write targets from similar names
- Use contextFiles from CLI output, don't assume specific file names
- Do not invent mandatory test scenarios without spec/decision/task/invariant/packet evidence
- Do not change invariants for test convenience
- Do not declare final adequacy or archive readiness; after completion follow **Post-apply next-step recommend** (`/opsx-verify mode=impl` first, then `/opsx-pyright-strict-coverage` → `/opsx-external-call-coverage` → conditional `/opsx-performance-review` → `/opsx-antipattern-gate` → `/opsx-static-check` → `/opsx-verify mode=archive` when production `.py` changed; else `mode=impl` then `mode=archive`)

**Fluid Workflow Integration**

This skill supports the "actions on a change" model:

- **Can be invoked anytime**: Before all artifacts are done (if tasks exist), after partial implementation, interleaved with other actions
- **Allows artifact updates**: If implementation reveals design issues, suggest updating artifacts - not phase-locked, work fluidly
