---
description: "READ_ONLY performance review of changed Python: N+1/async/queue/concurrency findings, PERFORMANCE_FIX_PACKET, independent re-audit, measurement authorization. Never writes."
argument-hint: "[scope=staged|working|base|full] [base=<ref>] [paths=…] [symbols=…] [focus=…] [paste FIX_RESULT / MEASUREMENT_RESULT]"
---

# /opsx-performance-review

Независимый READ_ONLY performance review изменённого Python-кода.

Единственный issuer финальных performance verdict:
`PASS` | `PASS_WITH_RISK` | `FAIL` | `DATA_GAP`.

## What this is

* Semantic performance reviewer (causal scope, finding taxonomy, evidence, verdict).
* Covers DB/N+1, ClickHouse, async, external I/O, memory, complexity, cache,
  serialization, **queues / TasksManager / run_tasks / TaskGroup**,
  **Semaphore / Lock / Redis NX**, scheduler overlap, nested fan-out,
  retry amplification, pool/cap/rate-limit/backpressure alignment.
* Producer of `PERFORMANCE_FIX_PACKET` and optional
  `PERFORMANCE_MEASUREMENT_AUTHORIZATION`.
* Independent re-auditor after `/opsx-performance-fix`.
* Soft conditional gate **after** pyright/external-call flow and **before**
  `/opsx-static-check` when trigger policy applies.

## What this is NOT

* NOT `/opsx-static-check` pack runner (no deterministic LLM-as-pack).
* NOT `/opsx-external-call-coverage` (testability of external calls).
* NOT `/opsx-close-external-gap` (PG/CH seam closure).
* NOT fixer / writer / measurement executor / committer.
* NOT hard archive gate for every diff (soft + additive verify report).
* NOT `/opsx-performance-run` — that command does not exist; measurement
  executes only inside `/opsx-performance-fix` under one-shot auth.

## Hard rules

* **READ_ONLY** end-to-end: no production / tests / process file edits.
* No stage / commit / push / commit-command invoke.
* No Docker / real PG/CH/Redis / network / benchmark / load / EXPLAIN /
  worker execution.
* Do not invent findings from keyword hits alone — require causal path +
  performance impact.
* **Serial `await` is not a defect** without proof that awaits are
  independent (no shared mutable state / same-shop / same-key /
  serialization / ordering contract).
* Preserve existing serialization, rate-limit, single_run, shop lease,
  Queue, Semaphore, Lock, Redis NX, and resource-cap contracts in analysis
  and in `DO_NOT_CHANGE` / `SERIALIZATION_CONTRACTS_TO_PRESERVE`.
* Fixer self-report is never independent `PASS`.
* All-skipped tests are not evidence.
* LOC_LINK mandatory for findings (`path:line`). Authority:
  `.cursor/rules/opsx-clickable-loc-link-contract.mdc`.
* Follow `.cursor/commands/opsx-source-resolution.md` and
  `.cursor/commands/opsx-execution-preflight.md` (Grep-first; parallel Read ≤ 2).

## User input

```text
$ARGUMENTS
```

Tokens (order free):

| Token | Effect |
|-------|--------|
| (default) / `scope=staged` | `git diff --cached` |
| `scope=working` | staged + unstaged + relevant untracked |
| `scope=base` + `base=<ref>` | diff from base to current HEAD/working as resolved |
| `scope=full` | bounded project performance surfaces, then selected modules — never unbounded dump |
| `paths=a,b` | exact comma-separated paths |
| `symbols=…` | exact symbols |
| `focus=…` | see Focus; comma-combine allowed |
| pasted `PERFORMANCE_FIX_RESULT` | independent re-audit mode |
| pasted `PERFORMANCE_MEASUREMENT_RESULT` | measurement re-audit |
| unknown token | `STATUS=BLOCKED` |

### Focus

```text
all | db | nplus1 | async | external | memory | complexity |
cache | serialization | benchmark | queue | orchestration |
ratelimit | backpressure
```

Default: `focus=all` within resolved scope.

## Trigger policy (companions + this command)

| Policy | When |
|--------|------|
| `PERFORMANCE_REVIEW_REQUIRED` | DB/query/repository changes; Queue / TasksManager / `run_tasks` / `gather` / `create_task`; Semaphore / Lock / Redis NX; pool / cap / rate-limit / retry / backpressure changes |
| `PERFORMANCE_REVIEW_RECOMMENDED` | Ambiguous hot async paths without clear I/O-in-loop |
| `NOT_APPLICABLE` | docs / typing-only; irrelevant tests-only diff |

Do **not** make performance review mandatory for every diff.

When triggered but no performance-sensitive surfaces → `STATUS=PASS` with
`NOTE=no_performance_surfaces` (or empty staged → `NOTE=empty_scope`);
no `PERFORMANCE_FIX_PACKET`.

## Modes

1. **Initial review** — scope / focus tokens.
2. **Re-audit** — consume `PERFORMANCE_FIX_RESULT` and/or
   `PERFORMANCE_MEASUREMENT_RESULT`; independently verify claimed fixes
   and measurement evidence (never trust fixer self-report alone).

## Scope resolution

1. Resolve file set from scope mode (default staged).
2. In-policy: `app/**/*.py` (+ top-level production scripts if in scope).
3. `tests/**` alone → usually `NOT_APPLICABLE` unless re-audit of authored tests.
4. Empty staged (default) → `STATUS=PASS`, `NOTE=empty_scope`, no FIX_PACKET.

## Performance surfaces (check applicability)

### Database / N+1

SQL/repository in loop; lazy relationship access; per-item lookup;
linear query growth; missing batch/bulk; repeated count/exists;
repeated flush/commit/refresh; session/engine per item; extra round trips;
large IN; unbounded SELECT; missing pagination/limit; over-fetch columns;
expensive join/sort/group; index suspicion; missing query-count regression.

### ClickHouse

Per-row inserts; missing batching; tiny frequent inserts; repeated scans;
bad filters; large materialization; wrong granularity; serial independent queries.

### Async / concurrency / queue / orchestration

* Sync/blocking I/O in async; **independent** awaits run serially
  (only when independence is proven).
* Unbounded `gather` / `create_task` / TasksManager queue.
* Missing semaphore / pool bounds; client/session per iteration.
* Event-loop blocking CPU; wrong executor use; retry amplification;
  task leaks; queues without backpressure.
* **TasksManager / `run_tasks` / TaskGroup** fan-out; nested fan-out;
  scheduler overlap / missing single_run.
* **Semaphore / Lock / Redis NX** correctness vs performance (do not
  recommend removal for speed).
* Pool alignment: task/HTTP/PG/CH caps vs nested concurrency.
* Same-shop / same-key serialization contracts.

### External / memory / complexity / cache / serialization / ratelimit / backpressure

HTTP-in-loop; serial requests; missing batch/reuse; auth re-init;
pagination amplification; cache bypass; unbounded materialization;
O(N²) on variable input; stampede; rate-limit / backpressure violations
or unsafe cap increases.

## Finding schema

Each finding MUST include:

```text
FINDING_ID:
CATEGORY:
SEVERITY: critical | high | medium | low
CONFIDENCE: high | medium | low
PATH:
LOC_LINK:
SYMBOL:
CAUSAL_PATH:
TRIGGER:
CURRENT_BEHAVIOR:
PERFORMANCE_IMPACT:
EVIDENCE_LEVEL:
EVIDENCE:
REQUIRED_VALIDATION:
RECOMMENDED_FIX:
FIX_SCOPE:
DO_NOT_CHANGE:
DISPOSITION:
  STATIC_FIX | UNIT_TEST_REQUIRED | QUERY_COUNT_REQUIRED |
  INTEGRATION_TEST_REQUIRED | BENCHMARK_REQUIRED | EXPLAIN_REQUIRED |
  MEMORY_PROFILE_REQUIRED | LOAD_TEST_REQUIRED | DATA_GAP | ACCEPTED_RISK
```

For **concurrency / queue / orchestration / ratelimit / backpressure**
findings, also require:

```text
NESTED_CONCURRENCY_NOTE:
POOL_ALIGNMENT_NOTE:
SERIALIZATION_CONTRACT:
```

## Evidence levels

`STATIC_SUSPECT` | `STATIC_CONFIRMED` | `UNIT_CONFIRMED` |
`QUERY_COUNT_CONFIRMED` | `INTEGRATION_CONFIRMED` | `BENCHMARK_CONFIRMED` |
`EXPLAIN_CONFIRMED` | `LOAD_CONFIRMED` | `PRODUCTION_OBSERVED` | `DATA_GAP`

Rules:

* Suspicious ≠ measurable regression.
* Explicit DB/API call in loop may be `STATIC_CONFIRMED`; prefer query-count close.
* Index without query shape / EXPLAIN → not hard FAIL alone.
* No invented benchmark thresholds / latency baselines.
* Serial await under same-shop / same-key / lock → not FAIL for “missing gather”.

## Verdicts

| STATUS | When |
|--------|------|
| `PASS` | surfaces checked; no blocking findings; required evidence present |
| `PASS_WITH_RISK` | no confirmed regression; bounded medium/low risks remain |
| `FAIL` | confirmed N+1 / per-item I/O / unbounded behavior / blocking sync in hot async / high-confidence O(N²) on scalable input / unbounded queue or nested fan-out without bounds / pool misalignment with proven amplification / measurable regression / broken mandatory perf or serialization contract |
| `DATA_GAP` | missing baseline / query-count / EXPLAIN / cardinality / stale audited state / measurement required for verdict |
| `BLOCKED` | bad tokens / unresolvable base |

Only this command may emit these performance verdicts as authoritative.

## PERFORMANCE_FIX_PACKET (omit if no fixable findings)

Required fields:

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

Concurrency findings inside `FINDINGS` must carry
`NESTED_CONCURRENCY_NOTE`, `POOL_ALIGNMENT_NOTE`, `SERIALIZATION_CONTRACT`.

## Measurement authorization (produce only; never execute)

When executable evidence is required and code/tests are ready after fix:

```text
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

Canonical hash recipe (Git only; SHA-256 of exact stdout bytes) — same as
`/opsx-close-external-gap` B2:

1. `git -c color.ui=false -c core.quotepath=false status --porcelain=v1 -z`
2. `git -c color.ui=false -c core.quotepath=false diff --binary --full-index --no-ext-diff --no-textconv HEAD --`
3. Untracked manifest: `ls-files --others --exclude-standard -z` → sorted
   path/size/content_sha256 records
4. `ALLOWED_RUN_BLOCK_SHA256` of the **full frozen** block text

Owner unlocks execution **only** via `/opsx-performance-fix` with
`AUTHORIZE_ONE_PERFORMANCE_RUN` + this packet. One process; one attempt;
no auto-retry; token consumed on first launch attempt; retry needs new
independent re-audit + new authorization. Final verdict only after
independent re-review of `PERFORMANCE_MEASUREMENT_RESULT`.

## Steps

1. Parse args; resolve scope / focus / re-audit packets.
2. Inventory in-policy paths; detect performance surfaces (incl. queue/
   concurrency checklist).
3. Classify findings with causal path; apply serial-await independence rule.
4. Assign evidence / dispositions / verdict.
5. If fixable findings → emit `PERFORMANCE_FIX_PACKET` with required fields
   + serialization contracts.
6. If measurement needed after ready fix → emit authorization (do not run).
7. Print Final report. Do not write files.

## Final report

```text
STATUS: PASS | PASS_WITH_RISK | FAIL | DATA_GAP | BLOCKED
MODE: READ_ONLY

SCOPE_MODE:
BASE:
HEAD:
STAGED_FILES:
WORKING_FILES:
PATHS_INSPECTED:
SYMBOLS_INSPECTED:
FOCUS:
TRIGGER_POLICY: REQUIRED | RECOMMENDED | NOT_APPLICABLE | n/a

PERFORMANCE_SURFACES:
- ...

FINDINGS:
- ...

EVIDENCE_SUMMARY:
- ...

RISKS:
- ...

PERFORMANCE_FIX_PACKET:   # omit if none
  ...

PERFORMANCE_MEASUREMENT_AUTHORIZATION:  # optional
PERFORMANCE_REVIEW_REPORT:
  STATUS:
  BASE:
  HEAD:
  FOCUS:
  FINDINGS_OPEN:
  EVIDENCE_SUMMARY:
  SERIALIZATION_CONTRACTS_NOTED:

WHAT_HAPPENED:
WHY:
CURRENT_STATE:
OWNER_DECISION_REQUIRED:
NEXT_ACTION:
DO_NOT_DO_YET:
```

### NEXT_ACTION rules

* `FAIL` with FIX_PACKET → `/opsx-performance-fix` + paste packet
* Re-audit after fix still needs measurement → emit
  `READY_FOR_ONE_AUTHORIZED_PERFORMANCE_RUN`; owner may authorize fix
  measure mode
* After measurement result → this command again for final verdict
* `PASS` | `PASS_WITH_RISK` → `/opsx-static-check` (then
  `/opsx-verify mode=archive <change>` if change active)
* Empty / no surfaces → `/opsx-static-check` when in pre-verify chain
* `BLOCKED` → fix args

### DO_NOT_DO_YET

* Do not run live / bench / Docker / workers from this command
* Do not treat fixer self-report as PASS
* Do not send performance findings to `/opsx-close-external-gap`
* Do not recommend removing Queue / Semaphore / Lock / Redis NX /
  single_run / shop lease / caps without proof they are unused and safe
* Do not treat serial await as defect without independence proof
* Do not stage / commit / push

## Handoff

| From | To |
|------|-----|
| apply / external-call PASS + trigger | this |
| this FAIL | `/opsx-performance-fix` |
| fix `READY_FOR_PERFORMANCE_REAUDIT` | this (re-audit) |
| this `READY_FOR_ONE_AUTHORIZED_PERFORMANCE_RUN` | owner auth → fix measure |
| fix measurement result | this (final) |
| this PASS / PASS_WITH_RISK | `/opsx-static-check` → verify → commit |

## Regression checks (self)

- [ ] Default scope=staged
- [ ] READ_ONLY; no live/bench
- [ ] Serial await not FAIL without independence proof
- [ ] Queue/TasksManager/Semaphore/Lock/Redis NX / nested fan-out / pool alignment covered
- [ ] FIX_PACKET has SERIALIZATION_CONTRACTS_TO_PRESERVE + AUDITED_* hashes
- [ ] Concurrency findings have NESTED_CONCURRENCY_NOTE / POOL_ALIGNMENT_NOTE / SERIALIZATION_CONTRACT
- [ ] Only this command issues independent PASS/FAIL
- [ ] LOC_LINK on every finding
- [ ] No `/opsx-performance-run`
