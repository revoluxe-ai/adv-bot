# Team roles (contractual separation)

```text
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: NOT_ACTIVE
```

Roles remain separate even when executed via registry-driven Task workers.

## ORCHESTRATOR

- Parses invocation modes (free-form / context / signal= / case=).
- Rejects ambiguous `case=` + new intake.
- Schedules waves; enforces Owner gates; never production-writes.
- Owns checkpoint / heartbeat supervision / process-tree termination.

## MATERIALIZER

- Accepts raw free-form intake; preserves verbatim `RAW_INTAKE_TEXT`.
- Extracts observations; separates facts vs assumptions.
- Duplicate search before new root.
- Creates/links case/finding. Does **not** classify or propose fix.

## CLAIM_WORKER

- Claims next available finding when `CHAT_REQUIRED=true`.
- Rejects duplicate active claims and claim bypass.
- Legacy resume uses explicit authority mode — never invents backdated claim.

## CLASSIFIER

Returns exactly one:

```text
IMPLEMENTATION_BUG
SPEC_BUG
SPEC_GAP
FALSE_POSITIVE
OUT_OF_SCOPE
INSUFFICIENT_EVIDENCE
```

Does not edit OpenSpec, production, or tests.

## SPEC_UPDATE_WORKER

- Route B only. Runs `/opsx-update` semantics.
- Writes `TASK_DELTA: CHANGED | UNCHANGED`.
- Never sets `EXPECTED_EXECUTION_ROUTE=/opsx-update`.

## RED_TEST_WORKER

- Authors multiple narrow tests per independent invariants.
- Runs each test alone, then targeted pack.
- Freezes `TEST_ID` + SHA-256.
- Distinguishes `RED_CONFIRMED` / `PASS_ALREADY` / `INVALID_RED`.
- Must not force artificial RED on valid `PASS_ALREADY`.

## IMPLEMENTATION_EXECUTOR

- Production writes only after `RED_CONFIRMED` (or approved N/A) **and**
  Owner production GO.
- Route A / B-UNCHANGED → `/opsx-fix-bug GO`.
- Route B-CHANGED → `/opsx-apply` after same gate.
- Test freeze by default (no test mutate on production GO).

## GREEN_VERIFIER

- Independent of implementation executor.
- Verifies frozen hash, same TEST_IDs, RED invariants now PASS,
  targeted pack PASS, scope, route reconciliation.
- Does not fix production or tests.

## TASK_COMPLETION_WORKER

Marks OpenSpec task `[x]` only with evidence mapping:

```text
TASK_ID
CURRENT_TASK_TEXT
IMPLEMENTATION_EVIDENCE
TEST_EVIDENCE
COMPLETION_DECISION
```

## BOUNDED_HUNTER

- Scope: changed production path, direct callers, direct persistence,
  direct renderer/state selectors, nearest relevant tests.
- No repository-wide audit.
- Does not classify or fix candidates.

## FAN_IN_ASSEMBLER

- Sole write: `.tmp/opsx-bug-cases/<CASE_ID>/results/FANIN.md`.
- No LEDGER / ROUTE-TRACE / CASE / finding / INDEX / production /
  tests / OpenSpec / `.cursor` writes.
- No Owner closure authority.

## CLOSURE_OPERATOR

- Stops at `FAN_IN_READY_FOR_OWNER_CLOSURE`.
- Owner final closure decision required.
- Must not auto-close case.
