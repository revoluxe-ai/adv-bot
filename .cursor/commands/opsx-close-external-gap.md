---
description: "Close PG/CH (refactor+integration) external-call gaps from a prior EXTERNAL_CALL_COVERAGE_REPORT. No base= — packet is the input."
argument-hint: "[paste EXTERNAL_CALL_COVERAGE_REPORT / GAPS] [kind=pg|ch] [symbols=…]"
---

# /opsx-close-external-gap

Закрой **REFACTOR_AND_TEST** gaps из предыдущего
`/opsx-external-call-coverage` отчёта: автономный минимальный refactor +
integration test authorship (PG / CH), с живым evidence только после
отдельной live-авторизации и независимого re-audit.

Это **не** inventory и **не** `base=` diff-audit.
Вход = packet предыдущей команды (BASE/HEAD/GAPS уже внутри).

## What this is

* Closure writer для направлений, где session/client mock **не** доказывает
  работу: прежде всего `PG` и `CH`.
* Автономный workflow: исследовать → reuse/modify/new helpers → минимальный
  production seam → tests → mock-only checks →
  `READY_FOR_READ_ONLY_REAUDIT` → independent re-audit.
* Живой Docker / real PG/CH / destructive / network запуск — **только** после
  независимого re-audit и `AUTHORIZE_ONE_LIVE_RUN` (единственный обычный
  manual approval в close workflow).
* Эта команда выдаёт только implementation self-report
  (`READY_FOR_READ_ONLY_REAUDIT` / `BLOCKED_*` / `DATA_GAP`), не
  независимый PASS / окончательный CLOSED / `READY_FOR_ONE_AUTHORIZED_RUN`.
* Do not stage, commit, push, or invoke commit commands.

## What this is NOT

* NOT `/opsx-external-call-coverage` (inventory / PASS|FAIL audit).
* NOT TEST_ONLY path (Redis fakeredis, WB write-gate, HTTP fake после
  готового seam) → `/opsx-test`.
* NOT полный OpenSpec apply / archive / static-check / verify.
* NOT per-kind audit front-doors (`/opsx-pg-coverage`, …).
* NOT ослабление PG/CH до unit session-mock как «закрытие» gap.
* NOT independent coverage PASS / final CLOSED verdict.
* NOT auto live/destructive pytest without `AUTHORIZE_ONE_LIVE_RUN`.
* NOT stop-for-owner только потому что нужен refactor / новый helper /
  правка shared test infrastructure.

## Authority split

| Concern | Owner |
|---------|--------|
| Diff inventory + dispositions | `/opsx-external-call-coverage` |
| TEST_ONLY (уже тестируемо) | `/opsx-test` |
| REFACTOR_AND_TEST (PG/CH / UNTESTABLE_SEAM) | **this command** (autonomous) |
| Broad new business feature | `/opsx-apply` |
| Archive | `/opsx-verify` |
| Independent live-ready verdict | `/opsx-external-call-coverage` (or independent re-audit) |

Если packet gap — TEST_ONLY (REDIS / WB_WRITE testable / HTTP с готовым
seam): **не** закрывай здесь.

```text
STATUS: BLOCKED_REDIRECT_TEST_ONLY
NEXT_ACTION: /opsx-test
```

## User input

```text
$ARGUMENTS
```

Обязателен **packet** из coverage (вставка в сообщение или явные поля):

| Token / body | Effect |
|--------------|--------|
| pasted `EXTERNAL_CALL_COVERAGE_REPORT` / `GAPS:` / `SURFACES:` | primary input |
| pasted `REFACTOR_AND_TEST_PACKET` | packetized primary input (preferred for mixed FAIL pipeline) |
| `kind=pg` \| `kind=ch` | optional filter; default = все PG+CH FAIL gaps из packet |
| `symbols=a,b` | optional subset of SYMBOL names |
| `base=` | **запрещён** → `STATUS=BLOCKED`; скажи: base только у coverage |

Примеры:

```text
/opsx-close-external-gap
<paste EXTERNAL_CALL_COVERAGE_REPORT>

/opsx-close-external-gap kind=pg
<paste GAPS block>

/opsx-close-external-gap kind=ch symbols=load_keyword_v3_profile_data
<paste report>

/opsx-close-external-gap
<paste REFACTOR_AND_TEST_PACKET>
```

Если прислан `TEST_ONLY_PACKET` (без REFACTOR_AND_TEST items) →
`STATUS=BLOCKED_REDIRECT_TEST_ONLY_PACKET` и отправь в `/opsx-test`.

## Required input

Если нет packet / GAPS / SURFACES с FAIL dispositions для PG|CH и нет
`REFACTOR_AND_TEST_PACKET` с PG|CH items → `STATUS=BLOCKED_NEEDS_PACKET`.

Спроси один раз:

```text
Вставь EXTERNAL_CALL_COVERAGE_REPORT / GAPS или REFACTOR_AND_TEST_PACKET из
/opsx-external-call-coverage. base= здесь не нужен.
```

Не выдумывай gaps из git diff.

## LOC_LINK (mandatory for report items)

Authority: `.cursor/rules/opsx-clickable-loc-link-contract.mdc`.

Если item ссылается на конкретный code/test location, печатай:

`LOC_LINK: <repo-relative-path>:<line>`

Где применимо:

* входные `REFACTOR_AND_TEST_PACKET` items (consume/preserve в отчёте);
* `SEAMS_AUTHORED`;
* `TESTS_AUTHORED`;
* `SCOPE_EXPANSION`;
* `CLOSE_RESULTS`.

`PATH` без `LOC_LINK` допустим только когда строка объективно не определяется;
в этом случае используй fallback-строку сигнатуры и пометь это в `NOTE`.

## Closure mode (derived)

Для каждого выбранного gap выставь ровно один:

| MODE | Когда |
|------|--------|
| `REFACTOR_AND_TEST` | KIND `PG`/`CH`, или `UNTESTABLE_SEAM`, или evidence только session/client mock |
| `TEST_ONLY_REDIRECT` | seam уже injectible и нужен только integration test без production edit → redirect `/opsx-test` (эта команда может сразу написать integration **code**, **если** production не трогает; иначе redirect) |

Default для PG/CH FAIL = `REFACTOR_AND_TEST`.

## Evidence rules (PG / CH)

Independent COVERED (via re-audit) requires:

* test под `tests/integration/**` (или явно `@pytest.mark.integration`);
* использует живой fixture (`async_session`, `clickhouse_client`, …);
* вызывает production writer/reader (не fully mocked `sm` / CH client как
  единственный path);
* assert читает **persisted** state из PG/CH (re-select / query), не только
  mock call args;
* для **PG**: session mode совпадает с intent символа
  (testing-rules § PG session mode) — **только явный** `read_only=`:
  WRITE / READ_AFTER_WRITE → `sm(read_only=False)`;
  PURE_READ → `sm(read_only=True)`.
  Seam, который оставляет bare `sm()` или wrong polarity, **не** evidence.
  При production edit на WRITE/READ path: bare → переписать в required call.
* для **PG/CH** preferred testability seam: parent callable открывает
  session/client и передаёт в child callable, где выполняется store-операция.
  Child-only создание session/client без handoff для changed boundary считать
  `REFACTOR_AND_TEST` gap (`NOTE=NO_PARENT_SESSION_HANDOFF`) и закрывать
  автономным seam refactor + tests.
* All-skipped live suite **не** считается evidence of close.

**Не** считать закрытием / self-report success as independent close:

* unit + `AsyncMock` session;
* orchestration, где writer всегда patched;
* green по имени без re-read из store;
* PG WRITE / READ_AFTER_WRITE на `read_only=True` (write-on-replica);
* bare `sm()` на любом PG INTENT (`PG_IMPLICIT_SESSION_MODE`);
* own green unit/mock-only tests (`READY_FOR_READ_ONLY_REAUDIT` only);
* handoff/unit test, который **patches away** production callable, чей
  PG/CH SQL / table / database qualification был изменён в этом close
  (`SQL_REWRITE_MOCKED_AWAY` — не proof rewrite).

Policy: `.cursor/rules/testing-rules.mdc` § Minimum test level / external-call /
PG session mode.

## Live-run token (only mandatory manual approval)

Единственный обычный manual approval в close workflow:

| Token | Unlocks |
|-------|---------|
| `AUTHORIZE_ONE_LIVE_RUN` | one live pytest process (requires `INDEPENDENT_REAUDIT`) |

`GO` / `AUTHORIZE_COMMAND_FIX` **не** являются live authorization и не
заменяют `AUTHORIZE_ONE_LIVE_RUN`.

Отдельные design/protected approval tokens этой команде **не нужны** и
**не используются**.

### AUTHORIZE_ONE_LIVE_RUN

Accept **only** together with:

```text
INDEPENDENT_REAUDIT:
  VERDICT: READY_FOR_ONE_AUTHORIZED_RUN
  AUDITED_HEAD: <sha>
  AUDITED_STATUS_SHA256: <sha256>
  AUDITED_TRACKED_DIFF_SHA256: <sha256>
  AUDITED_UNTRACKED_MANIFEST_SHA256: <sha256>
  ALLOWED_RUN_BLOCK_SHA256: <sha256>
```

This command **must not** emit `READY_FOR_ONE_AUTHORIZED_RUN`.

## Autonomous refactor policy

Команда **самостоятельно** выполняет минимально необходимый рефакторинг,
если он прямо требуется для закрытия gap из входного packet.
Дополнительное подтверждение владельца для refactor / helper / shared
test infra **не требуется**.

Разрешены:

* изменение production symbols и их непосредственного call-chain;
* добавление parent→child session/client handoff;
* выделение `*_in_session` / `*_with_client` seam;
* изменение существующего локального или shared test helper;
* создание нового test helper, если корректного нет;
* изменение session/engine factory для тестируемости;
* исправление transaction/cleanup lifecycle;
* изменение integration fixtures / `conftest.py` / test-support;
* добавление новых local integration tests;
* mock-only unit tests для новой инфраструктуры.

Каждое изменение должно быть:

* причинно связано с конкретным gap;
* минимальным;
* без opportunistic refactor;
* отражено в итоговом отчёте (`SEAMS_AUTHORED` / `SCOPE_EXPANSION` /
  `HELPER_STRATEGY`);
* покрыто подходящими mock-only/unit тестами **до** live запуска.

### PG/CH SQL rewrite proof (mandatory when applicable)

Если production edit в рамках gap **меняет** PG/CH SQL-текст, qualification
таблицы/БД или store targeting boundary (пример: снятие/добавление
`default_db.`, переход на unqualified + `client.database`):

1. **До** live MUST author pre-live unit, который вызывает **rewritten**
   callable с capturing fake client/session и assert'ит issued
   SQL/command против DB-targeting contract (нет запрещённого
   `default_db.` под guarded path / ожидаемый unqualified или expected
   qualified test DB — по выбранной seam policy).
2. Тест, который `patch`/`AsyncMock` **саму** rewritten callable/function,
   **не** считается покрытием этого rewrite (только handoff/math OK).
3. В `TESTS_AUTHORED` каждый релевантный node MUST иметь tag:
   `SQL_CONTRACT_UNIT` | `HANDOFF_MOCK_ONLY` | `DESTRUCTIVE_AUTHORED_NOT_RUN`
   (можно комбинировать с `authored` / `mock_unit_pass` / `not_run_live`).
4. Если prod SQL был rewritten и есть только `HANDOFF_MOCK_ONLY` →
   `CLOSE_RESULTS.RESULT=REMAINING` **или** `AUTHORED` с
   `NOTE=SQL_REWRITE_UNPROVEN`; `OWNER_DECISION_REQUIRED=true` с hint
   дописать `SQL_CONTRACT_UNIT` до «implementation complete for store
   path». Не представлять handoff-only как store-path complete.

## HELPER_DISCOVERY (reuse-first, non-blocking)

Перед работой с session/engine/bootstrap helper:

1. Grep existing: `async_session`, `clickhouse_client`, domain
   `_live_*_bootstrap`, `patched_*_session*`, `tests/support/**`,
   related fixtures/factories.
2. Алгоритм:
   1. Если подходящий helper есть — **reuse**.
   2. Если почти подходит — **modify**.
   3. Если корректного нет — **new**.
3. В отчёте:

```text
HELPER_DISCOVERY:
- searched: …
- found: …
HELPER_STRATEGY: reuse | modify | new
JUSTIFICATION: …
```

Не возвращать `BLOCKED_*` только из-за необходимости нового helper или
правки shared helper/fixture.

## Causal scope policy

Initial scope:

* production paths/symbols из packet;
* тесты для этих symbols.

Команда может **автоматически** расширить scope на непосредственно
необходимые:

* callers/callees;
* session/client seam;
* existing shared helper;
* integration fixture / bootstrap / engine factory;
* test-support module;
* mock-only regression tests;
* `conftest.py` when required for the gap.

Перед изменением дополнительного файла напечатать (informational, **не**
запрос разрешения):

```text
SCOPE_EXPANSION:
- PATH: <exact path>
- WHY_REQUIRED: …
- RELATION_TO_GAP: …
```

Запрещено:

* несвязанные handlers/services;
* «заодно» refactor вне causal chain;
* opportunistic cleanup не по gap.

## Shared test infrastructure

Следующее **не запрещено**, если изменение непосредственно необходимо для
входного gap:

* integration fixtures;
* DB/bootstrap helpers;
* engine/session factories;
* disposable-schema helpers;
* test-support modules;
* network/lifecycle guards;
* `conftest.py`.

При изменении shared infrastructure:

1. сначала прочитать существующий контракт;
2. не дублировать инфраструктуру;
3. сохранить обратную совместимость либо явно показать breaking change;
4. добавить mock-only regression tests;
5. перечислить затронутые consumers в отчёте;
6. не запускать live tests без `AUTHORIZE_ONE_LIVE_RUN`.

Ручной approval на сам refactor **не** требуется.

## When to stop (only these)

### Broad feature scope

Нужна полноценная новая бизнес-функциональность, а не seam/refactor:

```text
STATUS: BLOCKED_NEEDS_SEAM_SCOPE
NEXT_ACTION: /opsx-apply
```

### Dangerous operational area

Нужно изменить production deployment / secrets / production credentials /
production database / migrations с реальными данными / CI/CD deployment /
Kubernetes/infra / внешний API contract за пределами packet:

```text
STATUS: DATA_GAP
```

или redirect к соответствующей operational команде. Не «чинить» это здесь.

### Live / destructive execution

Написать integration test code — автономно.
Запускать Docker, real PG/CH, destructive fixture, external network —
только после независимого re-audit и `AUTHORIZE_ONE_LIVE_RUN`.

## Implementation → re-audit → live state machine

1. После autonomous seam/helper/test authorship + mock-only checks:

   ```text
   STATUS: READY_FOR_READ_ONLY_REAUDIT
   LIVE_RUN: not_attempted
   ```

2. Independent `/opsx-external-call-coverage` (or independent re-audit)
   returns one of:
   `READY_FOR_ONE_AUTHORIZED_RUN` | `REVISION_REQUIRED` | `DATA_GAP`.
   This command MUST NOT emit `READY_FOR_ONE_AUTHORIZED_RUN`.

3. Owner may authorize live only after that independent verdict + packet.

4. Re-invoke for live without `AUTHORIZE_ONE_LIVE_RUN` →

   ```text
   STATUS: BLOCKED_NEEDS_LIVE_RUN_AUTH
   ```

5. Token present but missing/invalid `INDEPENDENT_REAUDIT` with
   `VERDICT: READY_FOR_ONE_AUTHORIZED_RUN` →

   ```text
   STATUS: BLOCKED_NEEDS_INDEPENDENT_REAUDIT
   ```

Do **not** use ambiguous wording like
`BLOCKED_NEEDS_LIVE_RUN_AUTH or READY_FOR_READ_ONLY_REAUDIT`.

## Live-run authorization and audited-state manifest (B2)

Allowed without live token: read; edit causal scope; author mock-only /
unit / integration **test code**; run mock-only unit tests; perform
autonomous refactor per policy above.

Forbidden without exact `AUTHORIZE_ONE_LIVE_RUN` + valid
`INDEPENDENT_REAUDIT`: Docker; real PostgreSQL/ClickHouse; destructive
fixtures; live integration tests; external network/API tests.

### Canonical hash commands (Git only; no ext drivers / textconv / color)

Encoding: SHA-256 lowercase hex of exact stdout **bytes**. Do not rewrite
CRLF/LF after capture. Do not include stderr. Non-zero exit → `DATA_GAP`.

**1. `AUDITED_STATUS_SHA256`**

```bash
git -c color.ui=false -c core.quotepath=false \
  status --porcelain=v1 -z
```

→ SHA256 of exact stdout bytes (including NULs).

**2. `AUDITED_TRACKED_DIFF_SHA256`**

```bash
git -c color.ui=false -c core.quotepath=false \
  diff --binary --full-index --no-ext-diff --no-textconv HEAD --
```

→ SHA256 of exact stdout (empty diff → hash of empty).

**3. `AUDITED_UNTRACKED_MANIFEST_SHA256`**

1. Paths: `git ls-files --others --exclude-standard -z`
2. Split on NUL; drop empty; sort by raw repository-relative path (byte order).
3. For each path, one LF-terminated record:

   ```text
   <path>\t<size_decimal>\t<content_sha256_hex>\n
   ```

   - `size` = file size in bytes
   - `content_sha256` = SHA256 of file contents
   - if not a regular file → `DATA_GAP` / `REASON: NON_REGULAR_UNTRACKED`
4. Concatenate records in sorted order → SHA256 of that byte string.

**4. `ALLOWED_RUN_BLOCK_SHA256`**

SHA256 of the **full frozen shell block** from the independent re-audit
(not the pytest line alone). Block MUST include, in order:

1. environment validation steps;
2. exact pytest invocation;
3. teardown verification steps.

Hash the exact frozen block text as published (including newlines as frozen).
Do not hash a human-copied terminal pretty-print as substitute for stdout
bytes of the canonical git commands above.

### Live preflight

Before live run recompute all four hashes and compare `AUDITED_HEAD` to
`git rev-parse HEAD`. Also require:

* exact frozen run block match via `ALLOWED_RUN_BLOCK_SHA256`;
* one pytest process;
* no auto-retry;
* no file mutations between manifest validation and pytest start.

Any mismatch:

```text
STATUS: DATA_GAP
REASON: AUDITED_STATE_CHANGED
```

New independent re-audit required.

### One-shot token

* `AUTHORIZE_ONE_LIVE_RUN` is single-use.
* Consumed after the **first launch attempt**, regardless of exit code.
* Retry requires a new independent re-audit and a new authorization.
* Reuse of a spent token → reject.

## Unsafe legacy helpers

Если обнаружено `engine.sync_engine.dispose()` или другой lifecycle defect,
влияющий на текущий gap:

* не копировать дефект;
* **исправить** его в рамках текущей работы (autonomous);
* добавить mock-only regression test;
* отразить в `SCOPE_EXPANSION`;
* не блокироваться на ручное protected-infra approval.

Новый / исправленный async lifecycle MUST использовать корректный async
cleanup, например `await engine.dispose()`.

## Write boundary

Allowed under autonomous refactor + causal scope:

* production symbols/paths from packet and their necessary call-chain;
* parent→child session/client handoff; bare `sm()` → explicit
  `sm(read_only=…)` by INTENT;
* local and shared test helpers/fixtures/factories when required by gap;
* new local integration tests and mock-only unit tests;
* docstrings on changed public symbols.

Forbidden:

* unrelated handlers/services / opportunistic refactor;
* OpenSpec artifact edits (unless explicitly in packet — normally no);
* `.cursor/**` process edits;
* stage / commit / push / invoke commit commands;
* live/destructive execution without `AUTHORIZE_ONE_LIVE_RUN`.

Если нужный seam раздувается в feature rewrite →
`STATUS=BLOCKED_NEEDS_SEAM_SCOPE` + предложи `/opsx-apply` / change task.

## Steps

1. Разобрать packet; извлечь `BASE`, `HEAD`, FAIL gaps (или items из
   `REFACTOR_AND_TEST_PACKET`); применить filter `kind` / `symbols`.
   Для items с location перенести/сформировать `LOC_LINK`.
2. Если `base=` в args → `BLOCKED` (не путать с BASE внутри packet).
3. Если нет PG/CH FAIL gaps → `BLOCKED_NEEDS_PACKET` или
   `BLOCKED_REDIRECT_TEST_ONLY`.
4. Прочитать testing-rules + production symbols из gap PATH.
5. `HELPER_DISCOVERY` (`reuse | modify | new`); print `SCOPE_EXPANSION`
   when touching files beyond initial packet paths.
6. If injectable seam already exists for gap → prefer tests-only path
   (or `TEST_ONLY_REDIRECT`); do not re-refactor without need.
7. Autonomously author minimal seam / helpers / fixtures / tests; run
   mock-only unit as needed.
8. Do **NOT** run live/destructive pytest unless `AUTHORIZE_ONE_LIVE_RUN`
   + valid `INDEPENDENT_REAUDIT` present and audited-state preflight passes.
9. Print Final report as self-report + pasteable independent re-audit
   (`PACKET_BASE`).

## Status

| STATUS | Когда |
|--------|--------|
| `READY_FOR_READ_ONLY_REAUDIT` | seam/helper/test code authored; mock-only checks done; awaiting independent coverage |
| `BLOCKED_NEEDS_PACKET` | нет входа из coverage |
| `BLOCKED_REDIRECT_TEST_ONLY` | gaps не PG/CH refactor path → `/opsx-test` |
| `BLOCKED_REDIRECT_TEST_ONLY_PACKET` | передан только `TEST_ONLY_PACKET` → `/opsx-test` |
| `BLOCKED_NEEDS_SEAM_SCOPE` | нужна broad business feature, не seam/refactor → `/opsx-apply` |
| `BLOCKED_NEEDS_LIVE_RUN_AUTH` | live invoke without `AUTHORIZE_ONE_LIVE_RUN` |
| `BLOCKED_NEEDS_INDEPENDENT_REAUDIT` | live token without valid independent packet |
| `DATA_GAP` | audited state changed / non-regular untracked / dangerous operational area / missing evidence |
| `BLOCKED` | неизвестный token / `base=` в args / preflight |

This command does **not** emit authoritative `CLOSED` / `PARTIAL` / `PASS`
as independent truth. Optional internal counters (`SEAMS_AUTHORED`,
`TESTS_AUTHORED`, `MOCK_UNIT_PASS`) may appear with
`NOTE=implementation self-report only`.

## Final report (required)

```text
STATUS: READY_FOR_READ_ONLY_REAUDIT | BLOCKED_NEEDS_PACKET | BLOCKED_REDIRECT_TEST_ONLY | BLOCKED_REDIRECT_TEST_ONLY_PACKET | BLOCKED_NEEDS_SEAM_SCOPE | BLOCKED_NEEDS_LIVE_RUN_AUTH | BLOCKED_NEEDS_INDEPENDENT_REAUDIT | DATA_GAP | BLOCKED

PACKET_BASE: <from report>
PACKET_HEAD: <from report>
KIND_FILTER: pg|ch|pg+ch|…
GAPS_SELECTED: <n>

HELPER_DISCOVERY:
- searched: …
- found: …
HELPER_STRATEGY: reuse | modify | new
JUSTIFICATION: …

SCOPE_EXPANSION:
- PATH: …
  WHY_REQUIRED: …
  RELATION_TO_GAP: …

SEAMS_AUTHORED:
- <path>::<symbol> @ <LOC_LINK> — <one-line seam>

TESTS_AUTHORED:
- <path>::<node> @ <LOC_LINK> — authored | mock_unit_pass | not_run_live
  TAG: SQL_CONTRACT_UNIT | HANDOFF_MOCK_ONLY | DESTRUCTIVE_AUTHORED_NOT_RUN | n/a

LIVE_RUN: not_attempted | authorized_pass | authorized_fail | blocked_no_auth

CLOSE_RESULTS:
- SYMBOL: <name>
  PATH: <path>
  LOC_LINK: <path>:<line>
  KIND: PG|CH
  MODE: REFACTOR_AND_TEST|TEST_ONLY_REDIRECT
  DISPOSITION_BEFORE: …
  RESULT: AUTHORED|REMAINING|REDIRECTED|BLOCKED
  EXPECTED_REAUDIT: COVERED | WEAK_HANDOFF_ONLY | REMAINING | UNKNOWN
  NOTE: implementation self-report only; not independent PASS/CLOSED
        (| SQL_REWRITE_UNPROVEN when SQL rewritten + only HANDOFF_MOCK_ONLY)

EXPECTED_REAUDIT_SUMMARY:
- COVERED: <n>
- WEAK_HANDOFF_ONLY: <n>   # re-audit FAIL expected; progress from UNTESTABLE
- REMAINING: <n>

WHAT_HAPPENED:
WHY:
CURRENT_STATE: ready_for_read_only_reaudit | blocked_* | data_gap
OWNER_DECISION_REQUIRED: false | true (<live auth or packet only>)
NOTE: implementation self-report only; not PASS / not final CLOSED /
      not READY_FOR_ONE_AUTHORIZED_RUN
NEXT_ACTION:
DO_NOT_DO_YET:
```

### NEXT_ACTION rules

* `READY_FOR_READ_ONLY_REAUDIT` →  
  `/opsx-external-call-coverage base=<PACKET_BASE> focus=<kind>`  
  **Expected interim:** items with `EXPECTED_REAUDIT=WEAK_HANDOFF_ONLY`
  usually remain `WEAK_EVIDENCE` FAIL on re-audit — that is **progress**
  from `UNTESTABLE_SEAM`, not “close did nothing”. Next work for those
  symbols is integration / live evidence (or close TEST_ONLY_REDIRECT /
  integration authorship), **not** reinventing `*_in_session`.
  WHAT_HAPPENED MUST list AUTHORED counts vs how many are expected
  still-FAIL-as-WEAK.
  Только после focused PASS / independent live-ready verdict → owner may
  authorize one live run; then coverage `focus=all` as needed.
  Do **not** imply focused PASS is the immediate next milestone after
  handoff-only close.
* `BLOCKED_REDIRECT_TEST_ONLY` → `/opsx-test` затем coverage rerun.
* `BLOCKED_REDIRECT_TEST_ONLY_PACKET` → `/opsx-test` с этим packet, затем coverage rerun.
* `BLOCKED_NEEDS_PACKET` → попросить paste report.
* `BLOCKED_NEEDS_SEAM_SCOPE` → `/opsx-apply` (или явный task).
* `BLOCKED_NEEDS_LIVE_RUN_AUTH` → obtain `AUTHORIZE_ONE_LIVE_RUN` only after
  independent `READY_FOR_ONE_AUTHORIZED_RUN`.
* `BLOCKED_NEEDS_INDEPENDENT_REAUDIT` → run independent coverage/re-audit
  first.
* `DATA_GAP` (`AUDITED_STATE_CHANGED` or operational danger) → new re-audit
  and/or redirect to the owning operational command.

### DO_NOT_DO_YET

* Не archive / verify GO.
* Не считать unit session-mock закрытием PG/CH.
* Не считать evidence PG WRITE/RAW на `read_only=True`.
* Не считать evidence bare `sm()` (нужен явный `read_only=`).
* Не считать sole pre-live proof для PG/CH SQL rewrite тест, который
  mocks/patches rewritten store callable (`SQL_REWRITE_MOCKED_AWAY`).
* Не invent gaps без packet.
* Не передавать `base=` этой команде.
* Не дробить на `/opsx-pg-coverage` / `/opsx-ch-coverage`.
* Не run live without `AUTHORIZE_ONE_LIVE_RUN` + valid
  `INDEPENDENT_REAUDIT`.
* Не emit `PASS` / final `CLOSED` / `READY_FOR_ONE_AUTHORIZED_RUN`.
* Не копировать `sync_engine.dispose()`; исправлять lifecycle при impact.
* Не treat `GO` / `AUTHORIZE_COMMAND_FIX` as live auth.
* Не делать opportunistic refactor вне causal scope.
* Do not stage, commit, push, or invoke commit commands.
* Не трактовать post-handoff re-audit `WEAK_EVIDENCE` FAIL как
  «close ничего не сделал» / нулевой прогресс.
* Не подразумевать focused PASS сразу после handoff-only
  `READY_FOR_READ_ONLY_REAUDIT` без `EXPECTED_REAUDIT=COVERED`.
* Не опускать `EXPECTED_REAUDIT` на AUTHORED CLOSE_RESULTS items.

## Handoff

| From | To |
|------|-----|
| `/opsx-external-call-coverage` FAIL PG/CH / UNTESTABLE | this (paste report) |
| this `READY_FOR_READ_ONLY_REAUDIT` | coverage `focus=<kind>` → independent verdict → optional live auth → `focus=all` |
| TEST_ONLY gaps | `/opsx-test` |
| broad business feature | `/opsx-apply` |

## Command simulation matrix (static/dry-run)

| # | Scenario | Expected |
|---|----------|----------|
| 1 | Existing helper found | `HELPER_STRATEGY: reuse` |
| 2 | Near-fit helper | `modify` autonomously; no owner ask |
| 3 | No correct helper | `new` autonomously; no `BLOCKED` for helper alone |
| 4 | Shared bootstrap/fixture must change | edit + mock-only regression; no protected-infra token |
| 5 | Integration test written, no live auth | code OK; `READY_FOR_READ_ONLY_REAUDIT` / `LIVE_RUN: not_attempted` |
| 6 | Live without token | `BLOCKED_NEEDS_LIVE_RUN_AUTH` |
| 7 | Live token without independent packet | `BLOCKED_NEEDS_INDEPENDENT_REAUDIT` |
| 8 | Unsafe legacy dispose impacts gap | fix + regression test + `SCOPE_EXPANSION` |
| 9 | Causal caller/callee needed | `SCOPE_EXPANSION` informational; proceed |
| 10 | Unrelated handler «заодно» | forbidden |
| 11 | Broad new business feature | `BLOCKED_NEEDS_SEAM_SCOPE` → `/opsx-apply` |
| 12 | Own unit tests green | `READY_FOR_READ_ONLY_REAUDIT` only, not PASS |
| 13 | All-skipped integration suite | not independently closed |
| 14 | Injectable seam already exists | prefer tests-only; no needless re-refactor |
| 15 | Untracked content / run-block / HEAD mismatch | `DATA_GAP` / `AUDITED_STATE_CHANGED` |
| 16 | Live token reuse | reject; need new re-audit + token |
| 17 | Prod CH/PG SQL/db qualification rewritten; only handoff mock patches away rewritten callable | forbidden as sole pre-live proof; need `SQL_CONTRACT_UNIT` or `RESULT=REMAINING` / `NOTE=SQL_REWRITE_UNPROVEN` |
| 18 | Prod SQL rewritten + capturing fake client asserts SQL contract | `TESTS_AUTHORED` tag `SQL_CONTRACT_UNIT`; store path may be AUTHORED (still not independent PASS) |

## Regression checks (self)

- [ ] `base=` в args → BLOCKED
- [ ] без packet → BLOCKED_NEEDS_PACKET
- [ ] REDIS-only gaps → BLOCKED_REDIRECT_TEST_ONLY
- [ ] evidence rules require integration + live fixture + re-read store
- [ ] PG evidence: explicit `read_only=` matches WRITE|PURE_READ|READ_AFTER_WRITE (no bare)
- [ ] NEXT_ACTION re-audit использует PACKET_BASE, не выдуманный base
- [ ] Final report напечатан as self-report (no independent PASS/CLOSED)
- [ ] AUTHORED CLOSE_RESULTS include `EXPECTED_REAUDIT`; summary printed
- [ ] READY_FOR_READ_ONLY_REAUDIT warns WEAK-after-handoff is expected interim
- [ ] У каждого relevant result/seam/test item есть `LOC_LINK` (`<path>:<line>`)
- [ ] HELPER_DISCOVERY / HELPER_STRATEGY printed; new helper not auto-BLOCKED
- [ ] no design/protected approval tokens required for normal close
- [ ] only live gate uses `AUTHORIZE_ONE_LIVE_RUN` + B2 audited-state
- [ ] causal SCOPE_EXPANSION is informational, not permission ask
- [ ] simulation matrix scenarios considered (static/dry-run)
- [ ] PG/CH SQL rewrite → `SQL_CONTRACT_UNIT` or REMAINING/`SQL_REWRITE_UNPROVEN`; no sole handoff mock of rewritten callable
- [ ] no stage/commit/push/commit-command invoke| pasted `SCENARIO_REFACTOR_AND_TEST_PACKET` | PG/CH seam + provider integration from Scenario coverage |
| pasted `SCENARIO_CERTIFY_PACKET` | authored PG/CH provider tests awaiting authorized execution |
Если прислан `SCENARIO_TEST_ONLY_PACKET` без PG/CH refactor/certify items →
`STATUS=BLOCKED_REDIRECT_TEST_ONLY_PACKET` и отправь в `/opsx-test`, сохранив
Scenario/GAP identity.
Если нет packet / GAPS / SURFACES с FAIL dispositions для PG|CH, нет
`REFACTOR_AND_TEST_PACKET`, `SCENARIO_REFACTOR_AND_TEST_PACKET` или
`SCENARIO_CERTIFY_PACKET` с PG|CH items →
`STATUS=BLOCKED_NEEDS_PACKET`.
Вставь EXTERNAL_CALL_COVERAGE_REPORT / GAPS / REFACTOR_AND_TEST_PACKET из
/opsx-external-call-coverage либо Scenario packet из
/opsx-spec-scenario-coverage. base= здесь не нужен.
## Scenario coverage packets
Authority:
`.cursor/pipeline/contracts/SCENARIO_TEST_COVERAGE.md`.
Taxonomy:
`.cursor/pipeline/contracts/TEST_EVIDENCE_TAXONOMY.md`.
Для `SCENARIO_REFACTOR_AND_TEST_PACKET`:
1. принять только `SCHEMA_VERSION=1`, `DISPOSITION=REFACTOR_AND_TEST`,
   `KIND=PG|CH`;
2. сохранить `CHANGE_ID`, `GAP_ID`, Windows-safe `GAP_FILE_ID`,
   `SCENARIO_ID`, `CONTRACT_ID` и hashes;
3. сверить `SOURCE_SPEC_SHA`, `WORKTREE_FINGERPRINT` и `CONTRACT_SHA`;
4. stale packet → `DATA_GAP`, без edits;
5. создать минимальный production seam и real provider integration tests;
6. использовать переданный reviewed `ContractCase`;
7. не менять semantic expectation ContractCase/golden.
Если production reality противоречит ContractCase:
STATUS: BLOCKED_CONTRACT_MISMATCH
Не обновляй golden текущим provider output. Material behavior ambiguity
принадлежит Owner/planning route.
Для `SCENARIO_CERTIFY_PACKET`:
1. production/test authorship не повторять без freshness gap;
2. проверить exact provider test ids и все hashes;
3. принять `INDEPENDENT_REAUDIT` только по schema
   `.cursor/pipeline/contracts/SCENARIO_TEST_COVERAGE.md`, включая
   `GAP_FILE_IDS`, audited-state hashes и `ALLOWED_RUN_BLOCK_SHA256`;
4. без valid independent re-audit и `AUTHORIZE_ONE_LIVE_RUN` вернуть
   `BLOCKED_NEEDS_LIVE_RUN_AUTH` либо `BLOCKED_NEEDS_INDEPENDENT_REAUDIT`;
5. после фактического запуска создать `PROVIDER_EXECUTION_RECEIPT`;
6. не выдавать `SCENARIO_TEST_COVERAGE_PASS`.
  SOURCE_COMMAND: /opsx-external-call-coverage | /opsx-spec-scenario-coverage
* `.tmp/opsx-scenario-coverage/<CHANGE_ID>/receipts/PROVIDER-<GAP_FILE_ID>.md`
  только после фактического authorized provider run по Scenario packet.
   `REFACTOR_AND_TEST_PACKET` / Scenario packets); применить filter
   `kind` / `symbols`.
9. После Scenario live run создать `PROVIDER_EXECUTION_RECEIPT` по shared
   schema; receipt не равен final coverage PASS.
10. Print Final report as self-report + pasteable independent re-audit
    (`PACKET_BASE` для ECC или Scenario identity для Scenario route).
| `PROVIDER_EXECUTION_RECEIPT_READY` | authorized Scenario provider tests выполнены; receipt создан; awaiting scenario certify |
| `BLOCKED_CONTRACT_MISMATCH` | provider reality и reviewed ContractCase расходятся; auto-update forbidden |
STATUS: READY_FOR_READ_ONLY_REAUDIT | PROVIDER_EXECUTION_RECEIPT_READY | BLOCKED_NEEDS_PACKET | BLOCKED_REDIRECT_TEST_ONLY | BLOCKED_REDIRECT_TEST_ONLY_PACKET | BLOCKED_NEEDS_SEAM_SCOPE | BLOCKED_NEEDS_LIVE_RUN_AUTH | BLOCKED_NEEDS_INDEPENDENT_REAUDIT | BLOCKED_CONTRACT_MISMATCH | DATA_GAP | BLOCKED
SCENARIO_CHANGE_ID: <from Scenario packet | n/a>
SCENARIO_GAP_IDS: <from Scenario packet | n/a>
PROVIDER_EXECUTION_RECEIPTS:
- PATH: .tmp/opsx-scenario-coverage/<CHANGE_ID>/receipts/PROVIDER-<GAP_FILE_ID>.md
  GAP_ID:
  GAP_FILE_ID:
  SCENARIO_ID:
  CONTRACT_ID:
  CONTRACT_SHA:
  TEST_CONTENT_SHA:
  PRODUCTION_BOUNDARY_SHA:
  SCHEMA_SHA:
  WORKTREE_FINGERPRINT:
  RESULT:
  LOG_SHA:
  SECRETS_REDACTED: YES
  затем при focused PASS / independent live-ready verdict → owner may
  Для Scenario packet → `/opsx-spec-scenario-coverage mode=audit
  change=<SCENARIO_CHANGE_ID>`.
* `PROVIDER_EXECUTION_RECEIPT_READY` →
  `/opsx-spec-scenario-coverage mode=certify change=<SCENARIO_CHANGE_ID>`.
* `BLOCKED_CONTRACT_MISMATCH` → Owner/planning decision; не auto-update
  ContractCase/golden.
| `/opsx-spec-scenario-coverage` PG/CH REFACTOR_AND_TEST | this (paste Scenario packet) |
| this Scenario authorship self-report | `/opsx-spec-scenario-coverage mode=audit` |
| this `PROVIDER_EXECUTION_RECEIPT_READY` | `/opsx-spec-scenario-coverage mode=certify` |
| 19 | Valid Scenario REFACTOR packet | preserve Scenario/GAP/Contract identity; author seam + provider tests |
| 20 | Scenario TEST_ONLY packet | redirect unchanged to `/opsx-test` |
| 21 | Scenario ContractCase differs from provider reality | `BLOCKED_CONTRACT_MISMATCH`; no golden rewrite |
| 22 | Valid Scenario certify + re-audit + live token | one run; Windows-safe provider receipt; no Scenario PASS |
| 23 | Scenario receipt hashes stale after run | receipt remains evidence for old snapshot; certification must re-audit |
