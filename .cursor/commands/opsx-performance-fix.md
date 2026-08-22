---
description: "Autonomous performance fixer from PERFORMANCE_FIX_PACKET; authors tests; safe unit only; one-shot measurement only with AUTHORIZE_ONE_PERFORMANCE_RUN. Never independent PASS."
argument-hint: "[paste PERFORMANCE_FIX_PACKET] [AUTHORIZE_ONE_PERFORMANCE_RUN + PERFORMANCE_MEASUREMENT_AUTHORIZATION]"
---

# /opsx-performance-fix

Writer for confirmed performance findings. Consumes only a valid
`PERFORMANCE_FIX_PACKET` (or authorized measurement mode).

Does **not** issue independent `PASS` / `PASS_WITH_RISK` / `FAIL` —
that belongs solely to `/opsx-performance-review`.

There is **no** `/opsx-performance-run`. One-shot measurement runs inside
this command only under exact authorization.

## What this is

* Minimal causal performance refactor + regression test authorship.
* Safe unit/mock-only pytest without extra owner approval for ordinary
  causal refactor / helper / fixture.
* Optional **one-shot** measurement executor (live query-count, EXPLAIN,
  benchmark, memory profile, load, real PG/CH/Redis/HTTP) under
  `AUTHORIZE_ONE_PERFORMANCE_RUN` + `PERFORMANCE_MEASUREMENT_AUTHORIZATION`.

## What this is NOT

* NOT independent PASS issuer.
* NOT `/opsx-close-external-gap` / `/opsx-apply` for broad redesign.
* NOT committer / stager / pusher.
* NOT free to parallelize or raise caps without concurrency analysis.

## Hard rules

* Accept only valid `PERFORMANCE_FIX_PACKET` (required fields below).
* Stale packet vs current HEAD/diff → `DATA_GAP` /
  `REASON: PERFORMANCE_PACKET_STALE`.
* No stage / commit / push / commit-command invoke.
* No live DB / Docker / network / benchmark / load / EXPLAIN / workers
  without `AUTHORIZE_ONE_PERFORMANCE_RUN` + valid authorization packet
  with `VERDICT: READY_FOR_ONE_AUTHORIZED_PERFORMANCE_RUN`.
* Self-report only; never claim independent PASS.
* LOC_LINK on fixes and authored tests.
* Causal `SCOPE_EXPANSION` is informational, not a permission ask.
* Forbidden: unrelated cleanup; inventing bench thresholds.

### Concurrency / serialization safety (mandatory)

* Do **not** replace serial `await` with `gather` / unbounded fan-out
  without **independence proof** (and packet notes allowing it).
* Do **not** remove Queue, Semaphore, Lock, Redis NX, `single_run`,
  shop lease, or resource caps without proof they are unused and safe.
* Do **not** raise `MAX_TASKS`, HTTP, PG, or CH caps without nested
  concurrency + downstream pool analysis (must record
  `NESTED_CONCURRENCY_NOTE` / `POOL_ALIGNMENT_NOTE` in fix notes).
* Preserve same-shop and same-key serialization contracts listed in
  `SERIALIZATION_CONTRACTS_TO_PRESERVE` and per-finding
  `SERIALIZATION_CONTRACT`.

## Required packet fields

```text
PACKET_ID:
BASE:
HEAD:
SCOPE_MODE:
FOCUS:
FINDINGS:
INITIAL_PATHS:
ALLOWED_CAUSAL_EXPANSION:
REQUIRED_TESTS:
REQUIRED_MEASUREMENTS:
DO_NOT_CHANGE:
SERIALIZATION_CONTRACTS_TO_PRESERVE:
AUDITED_HEAD:
AUDITED_TRACKED_DIFF_SHA256:
```

If any concurrency finding lacks `NESTED_CONCURRENCY_NOTE` /
`POOL_ALIGNMENT_NOTE` / `SERIALIZATION_CONTRACT` → `STATUS=BLOCKED`
(invalid packet) or ask for re-review — do not invent them silently.

## Allowed fixes

* batch query; bulk insert/update; prefetch map;
  selectinload / joinedload when correct; lazy-amp removal;
* session/client reuse; parent→child handoff;
* pagination / streaming / chunking;
* **bounded** concurrency / semaphore / pool limits when packet allows
  and pool alignment is analyzed;
* parallel **independent** awaits only with independence proof;
* move blocking I/O off event loop; dedupe parse/serialize;
  map/set vs linear scan; O(N²) removal; cache reuse;
  retry amplification fixes that preserve rate-limit contracts;
* related helpers / fixtures / factories / test-support;
* unit / query-count / integration / benchmark **test code**.

## Tests authored

### Unit

Complexity, batching decisions, bounded concurrency, parsing/serialization,
cache behavior, helper lifecycle, serialization-contract preservation.

### Query-count

For N+1 / query amplification:

* scenario with 1 item;
* scenario with N items;
* SQL statement count;
* assert count does not grow linearly as `base + N`;
* persisted behavior remains correct.

Author a local/shared helper if missing (causal scope).

### Integration test code

Real repository/session/client path; no fully mocked store as sole evidence;
persisted re-read; production orchestration/seam.
**Author** autonomously; **run** live only when authorized.

### Benchmark code

Representative workload; deterministic setup; explicit metric; baseline
source; threshold justification; warmup/repetition policy; no invented
threshold. **Author** autonomously; **run** only when authorized.

## Causal scope expansion

May expand to necessary callers/callees/repositories/serializers/helpers/
fixtures/factories/test-support/query instrumentation within
`ALLOWED_CAUSAL_EXPANSION`.

For each extra file:

```text
SCOPE_EXPANSION:
- PATH:
  WHY_REQUIRED:
  RELATION_TO_FINDING:
```

## Measurement mode (one-shot)

Accept **only** together with:

```text
AUTHORIZE_ONE_PERFORMANCE_RUN

PERFORMANCE_MEASUREMENT_AUTHORIZATION:
  AUTHORIZATION_ID:
  VERDICT: READY_FOR_ONE_AUTHORIZED_PERFORMANCE_RUN
  AUDITED_HEAD:
  AUDITED_STATUS_SHA256:
  AUDITED_TRACKED_DIFF_SHA256:
  AUDITED_UNTRACKED_MANIFEST_SHA256:
  ALLOWED_RUN_BLOCK: |
    <exact frozen shell block>
  ALLOWED_RUN_BLOCK_SHA256:
  EXPECTED_ARTIFACTS:
  TEARDOWN:
```

Rules:

1. Recompute audited hashes; compare `AUDITED_HEAD` to `git rev-parse HEAD`.
2. Exact frozen `ALLOWED_RUN_BLOCK` only — no mutation.
3. One process; one attempt; no auto-retry.
4. Token consumed after **first launch attempt** (any exit code).
5. Emit `PERFORMANCE_MEASUREMENT_RESULT` (exit, artifacts, teardown).
6. Reuse of spent token → reject.
7. Audited state changed → `DATA_GAP` / `AUDITED_STATE_CHANGED`.
8. All-skipped suite → not evidence.
9. After measurement → `NEXT_ACTION: /opsx-performance-review` with result
   for **final independent** re-review.

Without token but measurements listed: do **not** run; return
`READY_FOR_PERFORMANCE_REAUDIT` with `MEASUREMENTS_NOT_RUN`.

Hash recipe: identical to review / close-external-gap B2 canonical Git
byte hashes.

## Stop conditions

| STATUS | When |
|--------|------|
| `READY_FOR_PERFORMANCE_REAUDIT` | fixes/tests authored; safe unit run if any; awaiting independent review (and/or measurement not run) |
| `BLOCKED_NEEDS_BROAD_REDESIGN` | needs new business architecture / product contract → `/opsx-apply` |
| `BLOCKED_NEEDS_PERFORMANCE_RUN_AUTH` | live invoke without token |
| `BLOCKED_NEEDS_INDEPENDENT_MEASUREMENT_AUTH` | token without valid `READY_FOR_ONE_AUTHORIZED_PERFORMANCE_RUN` packet |
| `DATA_GAP` | stale packet; audited state changed; ops/secrets/k8s/prod migration area |
| `BLOCKED` | missing/invalid packet; unknown tokens; unsafe gather/cap proposal rejected |

Operational danger (prod migration, secrets, k8s, external contract outside
packet) → `DATA_GAP` or redirect to owning operational command — do not
“fix” here.

## Steps

1. Parse packet or measurement auth; validate required fields.
2. Staleness check vs `AUDITED_HEAD` / `AUDITED_TRACKED_DIFF_SHA256`.
3. If measure mode → preflight hashes → run frozen block once → result → stop.
4. Else apply minimal causal fixes under concurrency safety rules.
5. Author required tests; run **safe unit/mock-only** only.
6. Print Final report as self-report. Do not claim PASS.

## Final report

```text
STATUS: READY_FOR_PERFORMANCE_REAUDIT
  | BLOCKED_NEEDS_BROAD_REDESIGN
  | BLOCKED_NEEDS_PERFORMANCE_RUN_AUTH
  | BLOCKED_NEEDS_INDEPENDENT_MEASUREMENT_AUTH
  | DATA_GAP
  | BLOCKED

PACKET_ID:
HEAD_BEFORE:
HEAD_CURRENT:
FINDINGS_SELECTED:

SCOPE_EXPANSION:
- PATH:
  WHY_REQUIRED:
  RELATION_TO_FINDING:

FIXES_APPLIED:
- FINDING_ID:
  PATH:
  LOC_LINK:
  CHANGE:
  EXPECTED_IMPACT:
  NESTED_CONCURRENCY_NOTE:   # when concurrency
  POOL_ALIGNMENT_NOTE:
  SERIALIZATION_CONTRACT:

TESTS_AUTHORED:
- ...

SAFE_TESTS_RUN:
- ...

MEASUREMENTS_NOT_RUN:
- ...
# or PERFORMANCE_MEASUREMENT_RESULT: ...

REMAINING_RISKS:
- ...

SERIALIZATION_CONTRACTS_PRESERVED:
- ...

NOTE: implementation self-report only; not independent PASS

PERFORMANCE_FIX_RESULT:
  PACKET_ID:
  STATUS:
  FIXES_APPLIED:
  TESTS_AUTHORED:
  HEAD_CURRENT:
  SERIALIZATION_CONTRACTS_PRESERVED:

WHAT_HAPPENED:
WHY:
CURRENT_STATE:
OWNER_DECISION_REQUIRED:
NEXT_ACTION:
DO_NOT_DO_YET:
```

### NEXT_ACTION

* Default → `/opsx-performance-review` + paste `PERFORMANCE_FIX_RESULT`
  (and `PERFORMANCE_MEASUREMENT_RESULT` if any)
* Broad redesign → `/opsx-apply`
* Needs measurement auth → obtain `AUTHORIZE_ONE_PERFORMANCE_RUN` only after
  independent `READY_FOR_ONE_AUTHORIZED_PERFORMANCE_RUN`

### DO_NOT_DO_YET

* Do not treat self-report as PASS
* Do not run live without token
* Do not reuse spent token
* Do not unsafe gather / remove locks / raise caps without analysis
* Do not stage / commit / push
* Do not route into `/opsx-close-external-gap`

## Handoff

| From | To |
|------|-----|
| `/opsx-performance-review` FAIL + FIX_PACKET | this |
| this `READY_FOR_PERFORMANCE_REAUDIT` | `/opsx-performance-review` |
| review measurement auth | this + `AUTHORIZE_ONE_PERFORMANCE_RUN` |
| this measurement result | `/opsx-performance-review` final |
| broad redesign | `/opsx-apply` |

## Simulation matrix (static / dry-run contract)

| # | Scenario | Expected |
|---|----------|----------|
| 1 | SQL in loop | accept STATIC_FIX / QUERY_COUNT; batch or prefetch |
| 2 | Serial await under same-shop | preserve serial; no gather |
| 3 | Independent cross-shop ops | gather/bounded fan-out only with independence proof |
| 4 | Unbounded TasksManager queue | add bounds/backpressure; do not delete Queue |
| 5 | Nested fan-out + shared MAX_TASKS | fix with NESTED_CONCURRENCY_NOTE; no blind cap raise |
| 6 | HTTP pool < task cap | POOL_ALIGNMENT_NOTE; align or bound tasks |
| 7 | Redis NX correctness lock | preserve lock; perf fix elsewhere |
| 8 | Retry amplification after 429 | reduce amplification; keep rate-limit contract |
| 9 | Unsafe gather proposal | BLOCKED / refuse; preserve serial |
| 10 | Same-key serialization | preserve in SERIALIZATION_CONTRACTS_PRESERVED |
| 11 | Measurement without auth | BLOCKED_NEEDS_PERFORMANCE_RUN_AUTH |
| 12 | Reused authorization | reject |
| 13 | Stale HEAD/diff | DATA_GAP PERFORMANCE_PACKET_STALE |
| 14 | Self-report before independent review | READY_FOR_PERFORMANCE_REAUDIT only |
| 15 | Empty packet / missing fields | BLOCKED |
| 16 | No findings packet | BLOCKED (nothing to fix) |

## Regression checks (self)

- [ ] Only PERFORMANCE_FIX_PACKET (or measure auth) accepted
- [ ] Required packet fields including SERIALIZATION_CONTRACTS_TO_PRESERVE + AUDITED_*
- [ ] No unsafe gather / lock removal / cap raise
- [ ] No independent PASS
- [ ] No live without AUTHORIZE_ONE_PERFORMANCE_RUN
- [ ] One-shot token consume; no retry
- [ ] LOC_LINK on fixes/tests
- [ ] No `/opsx-performance-run` file or redirect inventing one
- [ ] No stage/commit/push
