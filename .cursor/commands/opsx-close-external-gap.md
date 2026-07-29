---
description: "Close PG/CH (refactor+integration) external-call gaps from a prior EXTERNAL_CALL_COVERAGE_REPORT. No base= — packet is the input."
argument-hint: "[paste EXTERNAL_CALL_COVERAGE_REPORT / GAPS] [kind=pg|ch] [symbols=…]"
---

# /opsx-close-external-gap

Закрой **REFACTOR_AND_TEST** gaps из предыдущего
`/opsx-external-call-coverage` отчёта: минимальный production seam +
живой integration test (PG / CH).

Это **не** inventory и **не** `base=` diff-audit.
Вход = packet предыдущей команды (BASE/HEAD/GAPS уже внутри).

## What this is

* Closure writer для направлений, где session/client mock **не** доказывает
  работу: прежде всего `PG` и `CH`.
* Два шага в одном coherent pass: (1) минимальный refactor для
  testability, (2) `tests/integration/**` на живой fixture
  (`async_session` / `clickhouse_client`).
* После CLOSED → pasteable focused re-audit:
  `/opsx-external-call-coverage base=<BASE_FROM_PACKET> focus=<kind>`.

## What this is NOT

* NOT `/opsx-external-call-coverage` (inventory / PASS|FAIL audit).
* NOT TEST_ONLY path (Redis fakeredis, WB write-gate, HTTP fake после
  готового seam) → `/opsx-test`.
* NOT полный OpenSpec apply / archive / static-check / verify.
* NOT per-kind audit front-doors (`/opsx-pg-coverage`, …).
* NOT ослабление PG/CH до unit session-mock как «закрытие» gap.

## Authority split

| Concern | Owner |
|---------|--------|
| Diff inventory + dispositions | `/opsx-external-call-coverage` |
| TEST_ONLY (уже тестируемо) | `/opsx-test` |
| REFACTOR_AND_TEST (PG/CH / UNTESTABLE_SEAM) | **this command** |
| Broad feature implementation | `/opsx-apply` (если scope шире seam) |
| Archive | `/opsx-verify` |

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
```

## Required input

Если нет packet / GAPS / SURFACES с FAIL dispositions для PG|CH →
`STATUS=BLOCKED_NEEDS_PACKET`.

Спроси один раз:

```text
Вставь EXTERNAL_CALL_COVERAGE_REPORT (или GAPS) из
/opsx-external-call-coverage. base= здесь не нужен.
```

Не выдумывай gaps из git diff.

## Closure mode (derived)

Для каждого выбранного gap выставь ровно один:

| MODE | Когда |
|------|--------|
| `REFACTOR_AND_TEST` | KIND `PG`/`CH`, или `UNTESTABLE_SEAM`, или evidence только session/client mock |
| `TEST_ONLY_REDIRECT` | seam уже injectible и нужен только integration test без production edit → redirect `/opsx-test` (эта команда может сразу написать integration, **если** production не трогает; иначе redirect) |

Default для PG/CH FAIL = `REFACTOR_AND_TEST`.

## Evidence rules (PG / CH)

COVERED после close **только** если:

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
  Seam, который оставляет bare `sm()` или wrong polarity, **не** CLOSED.
  При production edit на WRITE/READ path: bare → переписать в required call.

**Не** считать закрытием:

* unit + `AsyncMock` session;
* orchestration, где writer всегда patched;
* green по имени без re-read из store;
* PG WRITE / READ_AFTER_WRITE на `read_only=True` (write-on-replica);
* bare `sm()` на любом PG INTENT (`PG_IMPLICIT_SESSION_MODE`).

Policy: `.cursor/rules/testing-rules.mdc` § Minimum test level / external-call /
PG session mode.

## Write boundary

Allowed:

* минимальный production seam в `app/**` для inject session/CH client /
  DI (без бизнес-переписывания вне gap);
* на том же seam pass: bare `sm()` → явный `sm(read_only=…)` по INTENT;
* `tests/integration/**` (+ fixtures/helpers под integration);
* docstring на изменённых публичных символах (project documentation rule).

Forbidden unless owner явно расширяет scope:

* unrelated refactors;
* OpenSpec artifact edits;
* `.cursor/**` process edits;
* commit / push / deploy.

Если нужный seam раздувается в feature rewrite →
`STATUS=BLOCKED_NEEDS_SEAM_SCOPE` + предложи `/opsx-apply` / change task.

## Steps

1. Разобрать packet; извлечь `BASE`, `HEAD`, FAIL gaps; filter `kind` /
   `symbols`.
2. Если `base=` в args → `BLOCKED` (не путать с BASE внутри packet).
3. Если нет PG/CH FAIL gaps → `BLOCKED_NEEDS_PACKET` или
   `BLOCKED_REDIRECT_TEST_ONLY`.
4. Прочитать testing-rules + production symbols из gap PATH.
5. На gap с `REFACTOR_AND_TEST`: минимальный seam; затем integration test;
   targeted `poetry run pytest … -m integration` (или точный node).
6. Не гонять полный suite без нужды.
7. Печать Final report + pasteable re-audit (BASE из packet).

## Status

| STATUS | Когда |
|--------|--------|
| `CLOSED` | все выбранные gaps имеют живой integration evidence |
| `PARTIAL` | часть gaps закрыта; остальные перечислены |
| `BLOCKED_NEEDS_PACKET` | нет входа из coverage |
| `BLOCKED_REDIRECT_TEST_ONLY` | gaps не PG/CH refactor path → `/opsx-test` |
| `BLOCKED_NEEDS_SEAM_SCOPE` | seam шире минимального; нужен apply/change |
| `BLOCKED` | неизвестный token / `base=` в args / preflight |

## Final report (required)

```text
STATUS: CLOSED | PARTIAL | BLOCKED | BLOCKED_NEEDS_PACKET | BLOCKED_REDIRECT_TEST_ONLY | BLOCKED_NEEDS_SEAM_SCOPE

PACKET_BASE: <from report>
PACKET_HEAD: <from report>
KIND_FILTER: pg|ch|pg+ch|…
GAPS_SELECTED: <n>
CLOSED: <n>
REMAINING: <n>

SEAMS_WRITTEN:
- <path>::<symbol> — <one-line seam>

INTEGRATION_TESTS:
- <path>::<node> — <PASS|FAIL>

CLOSE_RESULTS:
- SYMBOL: <name>
  KIND: PG|CH
  MODE: REFACTOR_AND_TEST|TEST_ONLY_REDIRECT
  DISPOSITION_BEFORE: …
  RESULT: CLOSED|REMAINING|REDIRECTED
  NOTE: …

WHAT_HAPPENED:
WHY:
CURRENT_STATE: gaps_closed | gaps_partial | blocked_needs_packet | redirect_test_only
OWNER_DECISION_REQUIRED: false | true (<what>)
NEXT_ACTION:
DO_NOT_DO_YET:
```

### NEXT_ACTION rules

* `CLOSED` →  
  `/opsx-external-call-coverage base=<PACKET_BASE> focus=<kind>`  
  затем при PASS focused →  
  `/opsx-external-call-coverage base=<PACKET_BASE>` (`focus=all`).
* `PARTIAL` → продолжить эту команду с remaining GAPS **или**
  re-audit focus для видимости.
* `BLOCKED_REDIRECT_TEST_ONLY` → `/opsx-test` затем coverage rerun.
* `BLOCKED_NEEDS_PACKET` → попросить paste report.
* `BLOCKED_NEEDS_SEAM_SCOPE` → `/opsx-apply` (или явный task) с описанием
  нужного seam.

### DO_NOT_DO_YET

* Не archive / verify GO.
* Не считать unit session-mock закрытием PG/CH.
* Не считать CLOSED PG WRITE/RAW на `read_only=True`.
* Не считать CLOSED bare `sm()` (нужен явный `read_only=`).
* Не invent gaps без packet.
* Не передавать `base=` этой команде.
* Не дробить на `/opsx-pg-coverage` / `/opsx-ch-coverage`.

## Handoff

| From | To |
|------|-----|
| `/opsx-external-call-coverage` FAIL PG/CH / UNTESTABLE | this (paste report) |
| this CLOSED | coverage `focus=<kind>` → `focus=all` |
| TEST_ONLY gaps | `/opsx-test` |
| oversized seam | `/opsx-apply` |

## Regression checks (self)

- [ ] `base=` в args → BLOCKED
- [ ] без packet → BLOCKED_NEEDS_PACKET
- [ ] REDIS-only gaps → BLOCKED_REDIRECT_TEST_ONLY
- [ ] CLOSED требует integration + live fixture + re-read store
- [ ] PG CLOSED: explicit `read_only=` matches WRITE|PURE_READ|READ_AFTER_WRITE (no bare)
- [ ] NEXT_ACTION re-audit использует PACKET_BASE, не выдуманный base
- [ ] Final report напечатан
