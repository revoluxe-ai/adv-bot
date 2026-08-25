---
description: "Write targeted tests from the user's request without changing production code."
argument-hint: "<test request / bug / behavior> | case=<CASE_ID> finding=<FINDING_ID> [verify] [CACHE_OFF|CACHE_FORCE|CACHE_DEV] [optional OpenSpec change-id]"
---

# /opsx-test

Write or update targeted tests based on the user's request.

You are allowed to edit tests only (plus durable RED/GREEN evidence under the case map in bug-regression / verify modes).

## Destructive cache (all runs that select `destructive_local`)

Contract SoT:
`.cursor/static-check/contracts/destructive-selective-cache.md`.

When a pytest invocation under this command would collect any
`@pytest.mark.destructive_local` node:

| Token / default | Effect |
|-----------------|--------|
| (no `CACHE_*`) | `CACHE_MODE=dev` — run `MUST_RUN` only via shared planner |
| `CACHE_OFF` | run all selected destructive |
| `CACHE_FORCE` | run all selected destructive; rewrite local cache receipts |
| `CACHE_DEV` | alias of default |

Always print `CACHE_MODE` + `destructive ran/cached` counts when destructive
nodes were in the plan. `CACHE_HIT` ≠ archive / certify EXECUTED green.
`authorized_live` certify stays on `/opsx-close-external-gap` (out of scope).

Planner: `.cursor/static-check/bin/destructive_cache_plan.py` (same artifact
as `/opsx-static-check` FULL).

**INTERIM:** planner missing/broken → run all selected destructive
(`CACHE_DEGRADED=yes`); forbidden to invent skip/deselect/“branch already
green” filters or claim `CACHE_HIT` without planner receipt.

## Modes

### Default (general test authoring)

Unchanged: author/update tests from a free-form request. Production code forbidden.

When free-form input cites `SCENARIO_TEST_COVERAGE_FAIL`, `change=<id>`,
stub gaps, or a pasted/prior `SCENARIO_TEST_ONLY_PACKET` — treat as scenario
closure work: apply **Stub inventory before AUTHORED** (below), not a single
obvious ContractCase family while other seam stubs remain open.

### Bug-regression mode (RED producer)

When both are present:

```text
case=<CASE_ID>
finding=<FINDING_ID>
```

and `verify` is **absent**, this command is the **RED producer** for the
bug-episode orchestration contract
(`.cursor/pipeline/contracts/bug-episode/RED_EVIDENCE.md`).

### Verify mode (GREEN writer — sole)

When `verify` is present with `case=` + `finding=`:

```text
GREEN_WRITER: /opsx-test verify mode
```

This is the **only** GREEN evidence writer. `/opsx-fix-bug` must not write
GREEN packets or approve `NON_WEAKEN_DELTA`.

```text
IMPLEMENTATION_STATUS: LIVE_ACTIVATED
VALIDATION_STATUS: INDEPENDENT_TEST_PASS
RUNTIME_ENFORCEMENT: ACTIVE
LIVE_COMMAND_BEHAVIOR_CHANGED: YES
GO_ACTIVATE: ISSUED
```


User input:

```text
$ARGUMENTS
```

## Packetized TEST_ONLY input

Команда поддерживает пакетный вход из
`/opsx-external-call-coverage` (`ROUTE_PACKETS`):

```text
TEST_ONLY_PACKET:
- SOURCE: EXTERNAL_CALL_COVERAGE_REPORT
- BASE: <BASE>
- HEAD: <HEAD>
- KINDS: [REDIS|WB_WRITE|HTTP|OTHER]
- ITEMS:
  - SYMBOL:
    KIND:
    PATH:
    DISPOSITION:
    NEXT: /opsx-test
```

Правила:

- Если передан `TEST_ONLY_PACKET`, обрабатывай его как первичный input.
- Если вместе с ним переданы PG/CH `REFACTOR_AND_TEST` items →
  не закрывай их здесь; верни redirect на `/opsx-close-external-gap`.
- Если packet пустой (`ITEMS` нет) → `NEXT_ACTION: /opsx-external-call-coverage base=<BASE>`
  для повторной проверки.

## Packetized Scenario coverage input

Authority:
`.cursor/pipeline/contracts/SCENARIO_TEST_COVERAGE.md`.
Taxonomy:
`.cursor/pipeline/contracts/TEST_EVIDENCE_TAXONOMY.md`.

Команда принимает:

```text
SCENARIO_TEST_ONLY_PACKET:
  SCHEMA_VERSION: 1
  SOURCE: SCENARIO_TEST_COVERAGE_REPORT
  CHANGE_ID:
  SOURCE_SPEC_SHA:
  WORKTREE_FINGERPRINT:
  ITEMS:
    - GAP_ID:
      GAP_FILE_ID:
      SCENARIO_ID:
      DISPOSITION: TEST_ONLY
      REQUIRED_ARTIFACTS:
      PRODUCTION_ENTRYPOINT:
      REAL_BOUNDARY_SYMBOLS:
      REALITY_CONSTRAINTS:
      MOCKING_CONSTRAINTS:
```

### Validation

До edits:

1. проверить `SCHEMA_VERSION=1`, `SOURCE`, `CHANGE_ID`, непустые `ITEMS`;
2. сохранить `GAP_ID`, Windows-safe `GAP_FILE_ID` и `SCENARIO_ID` без
   переименования;
3. сверить `SOURCE_SPEC_SHA` с текущим Scenario source;
4. при stale spec вернуть `STATUS=BLOCKED_STALE_SCENARIO_PACKET`;
5. принимать только `DISPOSITION=TEST_ONLY`;
6. PG/CH `REFACTOR_AND_TEST` и `CERTIFY` items не поглощать — вернуть их
   неизменными для `/opsx-close-external-gap`.

### Authorship responsibility

Для каждого item пакетно создать или обновить только необходимое в `tests/**`:

- reviewed `ContractCase`/case vectors;
- test fixtures/factories;
- fake/stub после causal boundary;
- `scenario_seam` test;
- `stub_contract` test;
- test-only `boundary_adapter` test, если production seam уже пригоден.

`ContractCase` MUST быть общим executable source для scenario fake assertions
и downstream provider integration. Запрещено:

- автоматически генерировать или обновлять expected golden текущим live output;
- полностью mock-ать `PRODUCTION_ENTRYPOINT` или causal/business boundary;
- придумывать DTO/model fields;
- заменять PG/CH provider proof session-mock unit-тестом;
- менять `app/**` ради прохождения packet.

### Stub inventory before AUTHORED

Перед `RESULT=AUTHORED` (packet batch **или** free-form closure после
scenario FAIL) MUST:

1. Построить `STUB_INVENTORY`: каждый stub/mock/fake thin end, используемый
   mapped failing `scenario_seam` tests (WB pause/start, notify, Telegram
   transport, injected PG/CH adapter после orchestration, и т.п.).
2. Для каждого inventory entry либо:
   - author shared `ContractCase` + scenario assert + `stub_contract` (+
     `boundary_adapter` если seam уже пригоден), **или**
   - оставить явный `REMAINING_GAPS` item с тем же GAP identity / stub symbol.
3. Запрещено закрывать batch как «готово», если inventory непуст и gaps не
   перечислены (пример дефекта: WB ContractCase authored, notify AsyncMock
   без ContractCase, silent omit).

В `SCENARIO_TEST_AUTHORSHIP_RESULT` при scenario context добавь поле
`STUB_INVENTORY` (symbols + closed|remaining) на уровне результата или
per-item `REMAINING_GAPS`.

Если item невозможно закрыть без production seam:

```text
ITEM_RESULT: REDIRECT_REFACTOR_AND_TEST
NEXT: /opsx-close-external-gap
```

сформируй/сохрани совместимый `SCENARIO_REFACTOR_AND_TEST_PACKET`, не теряя
identity/freshness fields.

Если все test code написано, но требуется destructive/live provider run:

```text
ITEM_RESULT: AUTHORED_AWAITING_CERTIFICATION
NEXT: /opsx-close-external-gap
```

сохрани `SCENARIO_CERTIFY_PACKET`. Не запускай live/destructive test из
обычного `/opsx-test`.

### Scenario packet result

Верни per-item:

```text
SCENARIO_TEST_AUTHORSHIP_RESULT:
  SCHEMA_VERSION: 1
  CHANGE_ID:
  SOURCE_SPEC_SHA:
  WORKTREE_FINGERPRINT:
  ITEMS:
    - GAP_ID:
      GAP_FILE_ID:
      SCENARIO_ID:
      RESULT: AUTHORED | ALREADY_COVERED | REDIRECT_REFACTOR_AND_TEST |
              AUTHORED_AWAITING_CERTIFICATION | BLOCKED
      CONTRACT_ID:
      CONTRACT_CASES_PATH:
      CONTRACT_SHA:
      FAKE_OR_STUB_PATH:
      FAKE_SHA:
      TEST_IDS:
      TEST_CONTENT_SHA:
      TESTS_EXECUTED:
      EXECUTION_RESULTS:
      REMAINING_GAPS:
      NEXT:
```

`AUTHORED` — writer self-report, не independent coverage PASS. После test-only
items основной возврат:

```text
NEXT_ACTION: /opsx-spec-scenario-coverage mode=audit change=<CHANGE_ID>
```

При remaining PG/CH refactor/certify items основной `NEXT_ACTION` —
`/opsx-close-external-gap` с соответствующим packet; повторный scenario audit
остаётся следующим после writer closure.


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

## Hard rules

- Do not modify production code.
- Do not modify OpenSpec artifacts unless the user explicitly asks.
- Do not commit, push, merge, rebase, deploy, restart services, touch secrets, run migrations, or change Kubernetes/CI.
- If the requested test cannot be written without changing production code, stop and explain the smallest required production seam/change. Do not implement it.
- If the request is a **PG/CH external-call gap** from
  `/opsx-external-call-coverage` that needs seam + live integration
  (REFACTOR_AND_TEST), do **not** pretend session-mock unit closes it.
  Redirect:

```text
NEXT_ACTION: /opsx-close-external-gap
```

  (paste the coverage report; no `base=` on close).
- If input is `TEST_ONLY_PACKET`, process all `ITEMS` batch-wise and report
  per-item closure; do not require manual split from mixed coverage report.
- If input is `SCENARIO_TEST_ONLY_PACKET`, process all `TEST_ONLY` items
  batch-wise, preserve Scenario/GAP identity, and return
  `SCENARIO_TEST_AUTHORSHIP_RESULT`; never claim final Scenario coverage PASS.
- PG `sm(...)`: только явный `read_only=` (testing-rules § PG session mode).
  Bare `sm()` / wrong polarity — не TEST_ONLY; → `/opsx-close-external-gap`
  (или apply), не unit session-mock.
- Prefer minimal targeted tests over broad rewrites.
- Do not create fake passing tests that only assert trivial behavior.
- In bug-regression / verify modes: also allow durable writes under
  `.tmp/opsx-bug-cases/<CASE_ID>/results/` for RED/GREEN evidence only
  (and materialize field updates for evidence paths via
  `/opsx-materialize-bug-queue mode=update`).

## Type-check routing

If the user input is raw `pyright` / `pyright-strict` / `mypy` output, a saved type-check log, or an explicit request to fix static typing diagnostics — do **not** triage or fix typing here.

Return immediately:

```text
NEXT_ACTION: /opsx-fix-types
```

Owner command: `.cursor/commands/opsx-fix-types.md`. Do not invent a manual typing plan inside `/opsx-test`.

## Allowed edits

Allowed:

- `tests/**`
- test fixtures under `tests/**`
- test factories under `tests/**`
- test-only helpers under `tests/**`
- `.tmp/opsx-bug-cases/<CASE_ID>/results/RED-<FINDING_ID>.md` (bug-regression)
- `.tmp/opsx-bug-cases/<CASE_ID>/results/GREEN-<FINDING_ID>.md` (verify mode only)
- case-map evidence path fields via materialize `mode=update` (paths only)

Forbidden unless explicitly approved:

- `app/**`
- `alembic/**`
- `.github/**`
- `.cursor/**`
- `openspec/**`
- Docker/Kubernetes/infra files
- production config
- secrets

## Pre-check

Before writing tests, inspect only what is REQUIRED_FOR the test-authoring decision.

Follow `.cursor/commands/opsx-source-resolution.md` and `.cursor/commands/opsx-execution-preflight.md`.

```bash
# OPTIONAL metadata — SKIP_IF not required; TIME_BUDGET branch 5s / status 10s
# git branch --show-current
# git status --short
```

If `change=<id>` is provided, read only:

```text
openspec/changes/<id>/proposal.md
openspec/changes/<id>/design.md
openspec/changes/<id>/tasks.md
openspec/changes/<id>/specs/
```

Then inspect only owner modules / existing tests referenced by the request.

Do **not** default to:

```bash
git status --short
find tests -maxdepth 5 -type f | sort
find app -maxdepth 6 -type f | sort
```

Those inventories / git status are bounded fallback only after `EVIDENCE_GAP` (unknown test location or dirty-tree claim) with budgets from the execution-preflight contract. Include `SOURCE_RESOLUTION` and `EXECUTION_PREFLIGHT` in the final output.

## Classify the request

Classify the requested test as one or more:

- regression test;
- characterization test;
- write-gate / no-write test;
- positive/negative gate pair;
- Telegram UI/message test;
- SQLAlchemy/query behavior test;
- async/concurrency test;
- Redis/PostgreSQL/ClickHouse consistency test;
- paid/free boundary test;
- Excel/UI parity test.

## Test quality requirements

Every new or changed test must make clear:

- what behavior is protected;
- what regression risk is being prevented;
- which owner function/module is involved;
- why the assertion would fail if the intended behavior is removed.

Use clear test names. Add comments only where the invariant is non-obvious.

## Regression tests

For regression tests:

- The test must fail on the broken behavior.
- The assertion must target the actual risk, not an incidental implementation detail.
- If you cannot prove the test fails before the fix, say so explicitly.

## Write-gate tests

For write-gate / no-write tests:

- Do not only assert `assert_not_called()` or `count == 0`.
- Prove that the forbidden entity is filtered before candidate selection, handler execution, or write-adapter boundary.
- Add a paired positive allowed case when possible.
- Check that the allowed path still writes or proceeds.

## Async tests

For async tests:

- Do not manually mutate shared module-level dependencies around `await`.
- Forbidden pattern: assigning `module.attr = fake` before `await` with manual `try/finally` restore.
- Prefer dependency injection, instance-level patching, write-adapter seams, external API client fakes, or pytest `monkeypatch` with justification.
- Avoid sleeps unless testing timeout behavior directly.

## Telegram UI/message tests

If the request touches Telegram messages, callbacks, keyboards, or bot UI:

- Check text length limits where relevant.
- Check parse mode / HTML validity.
- Check key phrases.
- Check buttons.
- Check callback data.
- Check keyboard shape.
- Check absence of raw technical text.
- If messages are parameterized, use realistic max-length substituted values, not tiny toy strings.

## Paid/free boundary tests

If the request touches paid/free behavior:

- Test free denial path.
- Test paid allowed path.
- Check that paid-only automation is not reachable from free UI/API path.
- Check that the user-facing explanation is present where relevant.

## SQLAlchemy/query tests

If the request touches ORM/query behavior:

- Test the exact filter/join/load behavior.
- Avoid tests that only check that a query object exists.
- Prefer fixtures with both matching and non-matching rows.
- Include edge cases for empty result, inactive rows, or unrelated shop/campaign where relevant.

## Verification

Run the most focused pytest command first (no xdist — worker overhead on tiny suites).

Example:

```bash
poetry run pytest tests/path/to/test_file.py::test_specific_case -vv
```

If useful, also provide a broader path command (still without `-n`):

```bash
poetry run pytest tests/path/to/test_file.py -vv
```

Only when the request requires the **full** unit marker suite (no path filter):

```bash
poetry run pytest -m unit -n 8 --dist=worksteal
```

Do not run unrelated slow suites unless required by the request.
Do not apply `-n` / `--dist` to focused/adjacent/`--lf` runs by default.


## Bug-regression mode (RED)

Required inputs:

```text
case=<CASE_ID>
finding=<FINDING_ID>
```

Resolve durable finding packet first
(`.tmp/opsx-bug-cases/<CASE_ID>/findings/<FINDING_ID>.md`).

### Allowed / forbidden

**Allowed:** `tests/**` (+ fixtures), RED evidence under case map, materialize
evidence-path updates.

**Forbidden:** production / `app/**` changes; claim steal; `GO` production apply.

### Required procedure

1. Author or select a regression test that must fail on the unrepaired bug.
2. Run targeted pytest **without** changing production.
3. Compute:

```text
TEST_ID = <repo-relative-path>::<pytest-nodeid>
TEST_CONTENT_SHA256 = sha256 of authoritative test source
  (and assertion-defining fixtures if separate)
PRODUCTION_HASH_BEFORE = hash/ref of production paths under test (unchanged)
FAILURE_MATCH: YES | NO
```

4. Write durable RED evidence:

```text
.tmp/opsx-bug-cases/<CASE_ID>/results/RED-<FINDING_ID>.md
```

Schema: `.cursor/pipeline/contracts/bug-episode/RED_EVIDENCE.md`.

5. Update finding/LEDGER evidence fields via materialize `mode=update`
   (`RED_EVIDENCE_PATH`, `TEST_ID`, `TEST_CONTENT_SHA256`).

6. Append one ROUTE-TRACE event for `test RED` (or `test GREEN` in verify
   mode). Update LEDGER `## ROUTE_STATE` (`LAST_COMMAND`, `OWNER_GATE_STATUS`
   when RED_CONFIRMED → Owner may issue GO, `NEXT_ACTION`).

### Exact RED statuses

Return exactly one:

```text
RED_CONFIRMED
TEST_NOT_REPRODUCING
RED_WRONG_REASON
TEST_SETUP_DEFECT
BUG_NOT_TESTABLE
BLOCKED
TIMEOUT
```

Rules:

* `RED_CONFIRMED` only if the test failed **and** `FAILURE_MATCH: YES`
  on unchanged production.
* Immediate green ⇒ `TEST_NOT_REPRODUCING` (no production GO handoff).
* Failed for wrong reason ⇒ `RED_WRONG_REASON`.
* Fixture/setup broken ⇒ `TEST_SETUP_DEFECT`.
* Automated RED not applicable ⇒ `BUG_NOT_TESTABLE` + exception packet
  fields from ORCHESTRATION §1.5 (Owner may later set
  `RED_NOT_APPLICABLE_APPROVED`; this command does not invent Owner approval).

### Pasteable next after RED_CONFIRMED

Default (Route A / TASK_DELTA NO):

```text
/opsx-fix-bug case=<CASE_ID> intake=<INTAKE_ID> finding=<FINDING_ID> claim_token=<CLAIM_TOKEN>
```

If `ROUTE_STATE` / TASK_DELTA says `EXPECTED_EXECUTION_ROUTE=/opsx-apply`:

```text
/opsx-apply <change-id>
```

Owner may append production `GO` only when
`BUG_CONFIRMED ∧ FIX_NOW ∧ (RED_CONFIRMED ∨ RED_NOT_APPLICABLE_APPROVED)`.

### ROUTE_TRANSITION (bug-regression / verify — mandatory for supervisor)

Authority: `.cursor/pipeline/contracts/bug-episode/ROUTE_TRANSITION.md`.
Narrative `NEXT_ACTION` is UX only. `MISSION_COMPLETE` on this worker is
always `no`. Finding close is owned by CLOSE_POLICY / materialize — not by
a lone `GREEN_CONFIRMED` unless close evidence is already recorded.

```text
RED_CONFIRMED:
  FROM_STATE: AWAITING_RED | <prior>
  RESULT: RED_CONFIRMED
  TO_STATE: AWAITING_OWNER_GO | AWAITING_FIX_BUG_RED
  NEXT_COMMAND: /opsx-fix-bug   # or /opsx-apply when EXPECTED_EXECUTION_ROUTE says so
  NEXT_ARGS: case=… finding=… claim_token=…   # WITHOUT inventing GO
  PRECONDITIONS.GO_TOKEN: REQUIRED            # Owner appends GO separately
  PRECONDITIONS.RED_REQUIRED: satisfied
  REQUIRED_EVIDENCE: RED_EVIDENCE_PATH
  RECOVERY_CLASS: ADVANCE
  MISSION_COMPLETE: no
  FINDING_TERMINAL: no

RED fail statuses (TEST_NOT_REPRODUCING | RED_WRONG_REASON | TEST_SETUP_DEFECT |
BUG_NOT_TESTABLE | BLOCKED | TIMEOUT):
  RECOVERY_CLASS: BLOCKED | PAUSED | NEEDS_OWNER
  MISSION_COMPLETE: no
  FINDING_TERMINAL: no
  NEXT_COMMAND: per existing recovery / none (no guessed route)

GREEN_CONFIRMED (evidence written; close not yet proven):
  FROM_STATE: AWAITING_GREEN | <prior>
  RESULT: GREEN_CONFIRMED
  TO_STATE: AWAITING_CLOSE | HANDBACK
  NEXT_COMMAND: HANDBACK_COMMAND | materialize close=fixed | per CLOSE_POLICY
  REQUIRED_EVIDENCE: GREEN_EVIDENCE_PATH
  RECOVERY_CLASS: ADVANCE
  MISSION_COMPLETE: no
  FINDING_TERMINAL: no

GREEN_CONFIRMED + durable close evidence already recorded this turn
(solo auto_after_green / materialize close=fixed succeeded):
  FINDING_TERMINAL: yes
  FINDING_TERMINAL_KIND: CLOSED_GREEN
  RECOVERY_CLASS: TERMINAL
  MISSION_COMPLETE: no
  NEXT_COMMAND: none | next-eligible via supervisor

GREEN_BLOCKED_PENDING_TEST_DELTA_REVIEW:
  RECOVERY_CLASS: PAUSED | NEEDS_OWNER
  MISSION_COMPLETE: no
  FINDING_TERMINAL: no
```

## Verify mode (GREEN writer)

Required:

```text
case=<CASE_ID>
finding=<FINDING_ID>
verify
```

### Rules

1. Read RED evidence; require same `TEST_ID`.
2. Re-run that exact `TEST_ID` (no assertion edits in this mode).
3. Compare `TEST_CONTENT_SHA256` to RED.
4. If hash differs without Owner-approved `NON_WEAKEN_DELTA` explaining
   every change and preserving the failing expectation ⇒ return:

```text
GREEN_BLOCKED_PENDING_TEST_DELTA_REVIEW
```

   Do **not** write `STATUS: GREEN_CONFIRMED`.
5. If pass + hash match (or approved non-weaken delta): write

```text
.tmp/opsx-bug-cases/<CASE_ID>/results/GREEN-<FINDING_ID>.md
```

   Schema: `.cursor/pipeline/contracts/bug-episode/GREEN_EVIDENCE.md`.
6. Update finding/LEDGER `GREEN_EVIDENCE_PATH` via materialize `mode=update`.
7. Append ROUTE-TRACE event for `test GREEN`; update `## ROUTE_STATE`.
8. **Post-GREEN next** (authority:
   `.cursor/pipeline/contracts/bug-episode/CLOSE_POLICY.md`):
   - Read `POST_GREEN_OWNER`, `CLOSE_FINDING_INTENT`, `HANDBACK_COMMAND`
     from LEDGER (defaults: `bug-team` + `ask_after_green`).
   - **Never** silent-return to bug-team; always pasteable.
   - If `POST_GREEN_OWNER=bug-team` (default):
     **PRIMARY** `NEXT_ACTION` =
     `HANDBACK_COMMAND` or
     `/opsx-bug-team case=<CASE_ID> mode=resume-family-fanout`
     **ALSO_OK**: solo close pasteables below; OpenSpec coverage/verify.
   - If `POST_GREEN_OWNER=solo` + `auto_after_green`:
     call materialize `mode=update … close=fixed` (same turn allowed for
     evidence+close field write via materialize contract).
   - If `POST_GREEN_OWNER=solo` + `ask_after_green`:
     emit pasteable pair:
     `/opsx-materialize-bug-queue mode=update case=… finding=… close=fixed`
     vs leave open with `LEAVE_OPEN_REASON=…`
   - If `never`: leave open; still show handback as ALSO_OK when team case.
   - Do **not** close error class / lesson from verify mode.

Silent test weakening is forbidden.

## Scenario packet simulation matrix

| Input | Expected |
|---|---|
| valid `SCENARIO_TEST_ONLY_PACKET` | batch all TEST_ONLY items; preserve ids |
| stale `SOURCE_SPEC_SHA` | `BLOCKED_STALE_SCENARIO_PACKET`; no edits |
| empty Scenario packet | BLOCKED; request producer rerun |
| item needs production seam | preserve item; `REDIRECT_REFACTOR_AND_TEST` |
| PG/CH live proof required | author code only; `AUTHORED_AWAITING_CERTIFICATION` |
| fake uses a private invented shape | reject; satisfy reality constraints |
| real causal boundary patched away | reject as weak evidence |
| ContractCase/fake/scenario tests authored | return ids + hashes; never coverage PASS |
| all test-only items authored | rerun `/opsx-spec-scenario-coverage mode=audit` |

## Output format

Return (default mode):

```text
Result:
- changed test files:
- behavior covered:
- why the test fails without the intended behavior:
- targeted command:
- broader command, if needed:
- remaining risks:
- packet_source: none | TEST_ONLY_PACKET | SCENARIO_TEST_ONLY_PACKET
- scenario_authorship_result: none | SCENARIO_TEST_AUTHORSHIP_RESULT
```

Return (bug-regression / verify):

```text
MODE: bug-regression | verify
CASE_ID:
FINDING_ID:
TEST_ID:
TEST_CONTENT_SHA256:
FAILURE_MATCH:          # RED only
STATUS:                 # RED_* or GREEN_* / GREEN_BLOCKED_*
RED_EVIDENCE_PATH:      # or GREEN_EVIDENCE_PATH
NEXT_ACTION:
ROUTE_TRANSITION:       # mandatory; schema ROUTE_TRANSITION.md
  MISSION_COMPLETE: no
  FINDING_TERMINAL:
  RECOVERY_CLASS:
  NEXT_COMMAND:
SOURCE_RESOLUTION:
EXECUTION_PREFLIGHT:
```

If tests fail because production code is currently wrong, do not fix production code. Report:

```text
Failing test result:
- command:
- failure:
- likely production issue:
- suggested next step:
```
