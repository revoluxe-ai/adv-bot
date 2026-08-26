---
description: "Audit committed or dirty-worktree production changes for external-call surfaces (HTTP/WB/PG/CH/Redis/…) and map each to adequate tests per testing-rules. Read-only."
argument-hint: "base=<branch|ref> [head=<ref>|working] [focus=all|http|wb|pg|ch|redis|other] [change=<name>]"
---

# /opsx-external-call-coverage

Проверь, что все **in-policy** production surfaces с внешними вызовами из
`base...target` имеют адекватное тестовое evidence по
`.cursor/rules/testing-rules.mdc` (не слепо требовать `-m integration`).

Цель: нельзя считать diff «готовым к verify/static», если новая/изменённая
внешняя граница не покрыта на минимально достаточном уровне
(`orchestration_seam` / `boundary_adapter` / `integration` / …).

## What this is

* Diff-scoped external-call coverage audit (sibling UX к
  `/opsx-pyright-strict-coverage`).
* Один gate на **все** kinds: HTTP, WB_WRITE, PG, CH, REDIS, OTHER —
  taxonomy внутри отчёта, не отдельные команды.
* Рекомендуемый шаг **после** `/opsx-pyright-strict-coverage` PASS (или
  параллельно, если typing allowlist уже закрыт), **до**
  `/opsx-static-check` и `/opsx-verify`, когда в diff есть production `.py`.
* Default **READ_ONLY** — не пишет production, tests, configs.

## What this is NOT

* NOT allowlist pyright (→ `/opsx-pyright-strict-coverage`).
* NOT запуск `pyright-strict` / static suite (→ `/opsx-static-check`).
* NOT archive / adequacy verdict (→ `/opsx-verify mode=archive`).
* NOT authoring regression/tests (→ `/opsx-test`).
* NOT production seam / DI refactor (→ `/opsx-apply` после owner GO).
* NOT change-specific invariant packet (→ `/opsx-invariant` /
  `TEST_COVERAGE_PACKET`); этот audit **дополняет**, не заменяет packet.
* NOT `/opsx-project-bug-hunt` и не product-bug triage.
* NOT отдельные `/opsx-*-ch|pg|redis|http-coverage` команды.

## User input

```text
$ARGUMENTS
```

Токены (порядок свободный):

| Token | Effect |
|-------|--------|
| `base=<ref>` | обязательный comparison base (branch/tag/commit) |
| `head=<ref>` | optional immutable comparison target |
| `head=working` | explicit dirty-worktree target |
| `focus=all\|http\|wb\|pg\|ch\|redis\|other` | optional; default `all`. Узкий прогон для отладки; **полный gate** перед verify = `all` |
| `change=<name>` | optional; читать change artifacts / приложить report context |
| иное неизвестное | `STATUS=BLOCKED`, не менять файлы |

Примеры:

- `/opsx-external-call-coverage base=main`
- `/opsx-external-call-coverage base=origin/main head=HEAD`
- `/opsx-external-call-coverage base=origin/main head=working`
- `/opsx-external-call-coverage base=main focus=redis`
- `/opsx-external-call-coverage base=main change=add-auth`

## Required input

Если `base=` отсутствует или ref не резолвится → `STATUS=BLOCKED`.

Спроси один раз:

```text
На какую base branch/ref сверять external-call coverage?
Пример: /opsx-external-call-coverage base=main
```

Не выдумывай base.

## Modes

### Default — READ_ONLY

* Не менять репозиторий.
* Только отчёт + pasteable `NEXT_ACTION`.
* Если `head=` не задан, target по умолчанию — текущий `WORKTREE`, а не
  committed `HEAD`; staged, unstaged и релевантные untracked in-policy paths
  должны попасть в audit.
* Опционально (если `change=` и owner явно просит persist): можно
  предложить путь для durable report, но **не писать** без отдельного
  owner GO на persist (v1: chat report only).

### No write GO in v1

В v1 **нет** `GO` режима для автофиксов. Gaps → `/opsx-test` (TEST_ONLY) или
`/opsx-close-external-gap` (REFACTOR_AND_TEST), затем rerun этого audit.

## Target resolution

1. Resolve `base` to an immutable commit.
2. Resolve target:
   - explicit `head=<ref>` → immutable ref target;
   - explicit `head=working` or omitted `head=` → current worktree target.
3. For the worktree target use the base-to-working diff, not
   `base...HEAD`; include staged and unstaged tracked changes, deletions, and
   relevant untracked in-policy files as added paths.
4. Report:

```text
AUDIT_TARGET: WORKTREE | REF
BASE_SHA: <sha>
TARGET_REF: WORKTREE | <sha>
WORKTREE_TRACKED_CHANGED: <n>
WORKTREE_UNTRACKED_IN_POLICY: <n>
WORKTREE_DELETED: <n>
```

5. A clean worktree target may be equivalent to `HEAD`, but the report must
   still state `AUDIT_TARGET: WORKTREE`. No commit is required for a
   read-only worktree re-audit.

## Policy scope (in / out)

**In-policy** (сканировать на external surfaces):

* изменённые или добавленные `*.py` под `app/`;
* изменённые/добавленные top-level production scripts `*.py` в корне репо
  (например `updater.py`), если они есть в diff.

**Out-of-policy** (`OUT_OF_POLICY_SCOPE`, не требуют coverage):

* `tests/**`;
* `.cursor/**`, `openspec/**`, `docs/**`, `docks/**`, `k8s/**`;
* non-`.py` файлы;
* удалённые пути (delete) — coverage не требуется на deleted symbol;
* чисто typing/docstring-only hunks без executable external boundary
  (зафиксируй `NO_EXTERNAL_SURFACE` на файл, не FAIL).

Rename/copy: проверяй **новый** путь (destination).

## Kind taxonomy (inside one command)

Каждый найденный surface получает ровно один primary `KIND`:

| KIND | Примеры границ |
|------|----------------|
| `HTTP` | httpx / aiohttp / requests / generic HTTP client |
| `WB_WRITE` | WB API write adapters, adv mutate, destructive marketplace writes |
| `PG` | SQLAlchemy / asyncpg / psycopg / Postgres repositories |
| `CH` | ClickHouse client / CH SQL execute / insert |
| `REDIS` | Redis get/set/pipeline / cache keys |
| `OTHER` | Telegram, filesystem write, ARQ enqueue, S3, прочие внешние I/O |

`focus=` фильтрует отчёт и FAIL-вклад по KIND (`wb` → `WB_WRITE`,
`http` → `HTTP`, …). При `focus≠all` полный pre-verify gate **не**
считается закрытым — в `NEXT_ACTION` напомни rerun с `focus=all`.

## External surface detection (minimum)

1. Resolve the target using **Target resolution** above.
2. Inventory the base-to-target changed paths, including relevant untracked
   worktree paths.
3. Для `AUDIT_TARGET: REF` используй
   `git diff <base>...<head> -- <path>`; для `AUDIT_TARGET: WORKTREE`
   используй `git diff <base> -- <path>`. Для untracked path прочитай файл как
   добавленный содержимый diff.
4. Для каждого in-policy path выполни Grep/AST-oriented inspection changed
   functions/methods/classes.
5. Считай surface, если изменённый callable (или его прямо достигнутый
   helper в том же diff) вызывает / планирует вызов внешней границы:
   - client/session execute, request, publish, enqueue;
   - repository/adapter write/read к PG/CH/Redis/WB/HTTP;
   - явный side-effect boundary из domain (WB write, CH insert, …).
6. Не инвентаризируй весь файл «на всякий случай» — только **touched**
   callables и их очевидные callees в том же diff hunk set.
7. Bounded I/O: следуй `.cursor/commands/opsx-execution-preflight.md` и
   `.cursor/commands/opsx-source-resolution.md` (Grep-first; parallel Read ≤ 2).

При сомнении между KIND — выбери наиболее specific (`WB_WRITE` >
`HTTP`; конкретный store > `OTHER`) и запиши `KIND_NOTE`.

## LOC_LINK (line-aware, mandatory)

Authority: `.cursor/rules/opsx-clickable-loc-link-contract.mdc`.

Для каждого найденного surface и каждого gap/packet item печатай
`LOC_LINK` в кликабельном для Cursor формате:

`<repo-relative-path>:<line>`

Правила:

1. `LOC_LINK` обязателен в `SURFACES`, `GAPS`, `ROUTE_PACKETS` items и
   `PASTE_AND_GO_BLOCKS` items.
2. `PATH` оставляй как путь к файлу (без строки), а `LOC_LINK` — тот же
   путь + номер строки.
3. Строку бери из boundary call / changed hunk; если точка boundary не
   однозначна — fallback на строку сигнатуры `def/class` целевого symbol.
4. Не печатай только `PATH` без `LOC_LINK`.

## Minimum test level (per testing-rules)

Для каждого surface назначь `MINIMUM_LEVEL` по
`.cursor/rules/testing-rules.mdc` § Minimum test level + kind defaults ниже:

* `unit_component`
* `orchestration_seam`
* `runtime_entrypoint`
* `boundary_adapter`
* `integration`

### Kind defaults (mandatory)

| KIND | Default MINIMUM_LEVEL for durable I/O adapters | Notes |
|------|-----------------------------------------------|-------|
| `PG` | `integration` | живой `async_session` / real sm; session `AsyncMock` alone → **not** COVERED; также проверить **session mode** (ниже) |
| `CH` | `integration` | живой `clickhouse_client`; mocked CH client alone → **not** COVERED; SQL rewrite mocked away → `WEAK` `SQL_REWRITE_MOCKED_AWAY` |
| `REDIS` | `boundary_adapter` or `integration` (fakeredis OK) | fakeredis roundtrip acceptable |
| `WB_WRITE` | `orchestration_seam` | mock WB **after** causal/write-gate boundary OK |
| `HTTP` | `orchestration_seam` / `boundary_adapter` | client fake after seam OK |
| `OTHER` | per boundary | Telegram/fs/ARQ — case-by-case |

Правила:

* Не требуй full E2E автоматически.
* Write-gate / WB destructive → evidence filtering до write boundary
  (не только `assert_not_called()`).
* Mock внешней destructive dependency допустим **после** causal boundary,
  если orchestration path реален — **кроме** заявленного proof самого
  PG/CH adapter (тогда нужен live store).
* Pure DTO/mapping без I/O → обычно не surface (`NO_EXTERNAL_SURFACE`).
* Unit session-mock для PG/CH writer = `WEAK_EVIDENCE` (или
  `UNTESTABLE_SEAM`, если без DI нельзя подставить test session).
* Для **new/changed** PG/CH boundary-кода отсутствие injectable seam
  (session/client создаётся только внутри target callable и не передаётся через
  аргументы/provenance seam) классифицируй как `UNTESTABLE_SEAM` с
  `NOTE=NO_INJECTABLE_SEAM`; не закрывай gap через unit session-mock.
* Предпочтительный seam для PG/CH: parent orchestration открывает session/client
  и передаёт в child callable, где выполняется store-работа. Если changed
  boundary оставляет child-only создание session/client без handoff — помечай
  `UNTESTABLE_SEAM` с `NOTE=NO_PARENT_SESSION_HANDOFF`.
* Для KIND=`CH`|`PG` surfaces, чей changed hunk включает SQL/query text или
  db/table qualification: если единственные tests `patch`/`AsyncMock` **producer
  callable**, так что новый SQL никогда не выполняется →
  `DISPOSITION=WEAK_EVIDENCE` с `NOTE=SQL_REWRITE_MOCKED_AWAY` (FAIL-set).
  Handoff-only green **недостаточен** для `COVERED` на этом surface.
  (Capturing fake client, вызывающий rewritten callable, — минимум для
  снятия этого NOTE; live fixture всё ещё нужен для `COVERED`.)

### PG session mode check (mandatory for KIND=PG)

Authority: `.cursor/rules/testing-rules.mdc` § PG session mode.
Для каждого PG surface назначь `INTENT` и сверь call site
(`sm` / `get_async_session_maker` / provenance injected session).
**Каждый** call MUST иметь явный `read_only=`; bare `sm()` запрещён.

| INTENT | Required | Disposition impact |
|--------|----------|--------------------|
| `WRITE` | `sm(read_only=False)` | bare → `WEAK_EVIDENCE` NOTE=`PG_IMPLICIT_SESSION_MODE`; `True` → `WEAK_EVIDENCE` NOTE=`PG_WRONG_SESSION_MODE` |
| `PURE_READ` | `sm(read_only=True)` | bare → `WEAK_EVIDENCE` NOTE=`PG_IMPLICIT_SESSION_MODE`; `False` → `WEAK_EVIDENCE` NOTE=`PG_WRONG_SESSION_MODE` |
| `READ_AFTER_WRITE` | `sm(read_only=False)` | bare → `WEAK_EVIDENCE` NOTE=`PG_IMPLICIT_SESSION_MODE`; `True` → `WEAK_EVIDENCE` NOTE=`PG_WRONG_SESSION_MODE` |

SoT политики — testing-rules + этот gate; **не** дублировать полный policy в
`/opsx-project-bug-hunt` (hunt — optional thin checklist later, не SoT).
`PG_SESSION_HYGIENE` (non-FAIL note) **снят** — bare всегда FAIL-set WEAK.

### HANDLER_INLINE_SM_CHECK (mandatory for KIND=PG changed callables)

Human-native seam check. **Не останавливайся** на одном `PG_IMPLICIT_SESSION_MODE`,
если session создаётся внутри target callable без handoff.

Для каждого changed PG callable (handler / orchestration / writer) ответь:

1. Есть `async with sm(...)` / `get_async_session_maker(...)` **внутри**
   target callable?
2. Session передаётся в child callable аргументом / provenance seam? (`yes`/`no`)
3. Если шаг 1 = yes и шаг 2 = **no** → `DISPOSITION=UNTESTABLE_SEAM` с
   `NOTE=NO_INJECTABLE_SEAM` и/или `NOTE=NO_PARENT_SESSION_HANDOFF`.
4. Если при этом ещё и bare `sm()` → добавь `NOTE=PG_IMPLICIT_SESSION_MODE`,
   но **primary disposition остаётся** `UNTESTABLE_SEAM` (не downgrade до
   только `WEAK_EVIDENCE`).

Example FAIL (must catch):

```python
async def open_change_auto_bid(...):
    async with sm() as session:  # session created inside handler
        ...  # no helper(session, ...) child receiving the session
```

→ `UNTESTABLE_SEAM` (`NO_INJECTABLE_SEAM` / `NO_PARENT_SESSION_HANDOFF`),
optionally also `PG_IMPLICIT_SESSION_MODE`.

Preferred pattern (not a FAIL for handoff):

```python
async def open_change_auto_bid(...):
    async with sm(read_only=True) as session:
        adv = await load_adv_for_change_auto_bid(session, adv_id)
```

где store-работа живёт в child, принимающем `session`.

## Test mapping

Для каждого surface найди candidate tests:

1. Targeted tests under `tests/` matching module/symbol path.
2. Adjacent feature suite if shared symbol signature changed.
3. Inspect whether test actually exercises the production seam (not only
   a similarly named test).
4. Для PG/CH: предпочитай `tests/integration/**` + re-read persisted
   rows/query results.

Dispositions (per surface):

| DISPOSITION | Meaning |
|-------------|---------|
| `COVERED` | есть test evidence ≥ `MINIMUM_LEVEL` с real causal path |
| `MISSING_TEST` | surface testable; адекватного test нет |
| `WEAK_EVIDENCE` | test есть, но name/green без seam proof / write-gate weak / **PG\|CH только session-mock** / **PG_WRONG_SESSION_MODE** / **PG_IMPLICIT_SESSION_MODE** / **SQL_REWRITE_MOCKED_AWAY** (changed SQL/qualification, producer fully mocked) |
| `UNTESTABLE_SEAM` | нельзя написать адекватный (esp. live PG/CH) test без production seam/DI; для new/changed PG/CH include `NOTE=NO_INJECTABLE_SEAM` когда session/client создаётся только внутри callable |
| `OUT_OF_POLICY` | не in-policy |
| `NO_EXTERNAL_SURFACE` | in-policy file/hunk без внешней границы |
| `DEFERRED_OWNER` | нужна owner decision (спорный KIND/level) |

## KIND_CLOSURE (pasteable handoff)

В Final report после `GAPS:` добавь блок маршрутизации:

```text
KIND_CLOSURE:
- KIND: REDIS|WB_WRITE|HTTP|OTHER
  MODE: TEST_ONLY
  NEXT: /opsx-test
  THEN: /opsx-external-call-coverage base=<BASE> focus=<kind>
- KIND: PG|CH
  MODE: REFACTOR_AND_TEST
  NEXT: /opsx-close-external-gap
  PACKET: paste this EXTERNAL_CALL_COVERAGE_REPORT (no base= on close)
  THEN: /opsx-external-call-coverage base=<BASE> focus=pg|ch
```

Не смешивай TEST_ONLY и REFACTOR_AND_TEST в одном «просто допиши тест».

## ROUTE_PACKETS (mandatory for mixed FAIL)

Если в `GAPS` одновременно есть TEST_ONLY и REFACTOR_AND_TEST, добавь
после `KIND_CLOSURE` блоки пакетной маршрутизации:

```text
ROUTE_PACKETS:
- TEST_ONLY_PACKET:
  - SOURCE: EXTERNAL_CALL_COVERAGE_REPORT
  - BASE: <BASE>
  - HEAD: <HEAD>
  - KINDS: [REDIS|WB_WRITE|HTTP|OTHER]
  - ITEMS:
    - SYMBOL: <name>
      KIND: <kind>
      PATH: <path>
      LOC_LINK: <path>:<line>
      DISPOSITION: <MISSING_TEST|WEAK_EVIDENCE>
      NEXT: /opsx-test
- REFACTOR_AND_TEST_PACKET:
  - SOURCE: EXTERNAL_CALL_COVERAGE_REPORT
  - BASE: <BASE>
  - HEAD: <HEAD>
  - KINDS: [PG|CH]
  - ITEMS:
    - SYMBOL: <name>
      KIND: <PG|CH>
      PATH: <path>
      LOC_LINK: <path>:<line>
      DISPOSITION: <WEAK_EVIDENCE|UNTESTABLE_SEAM|MISSING_TEST>
      NEXT: /opsx-close-external-gap
```

Правила:

* При отсутствии mixed FAIL `ROUTE_PACKETS` можно опустить.
* Для `REFACTOR_AND_TEST_PACKET` не требуй и не передавай `base=` в close-команду.
* Для `TEST_ONLY_PACKET` не включай PG/CH REFACTOR_AND_TEST items.
* Каждый item в packet MUST содержать `LOC_LINK`.

## MIXED_FAIL_PIPELINE (mandatory when both packet types exist)

Если одновременно сформированы `TEST_ONLY_PACKET` и `REFACTOR_AND_TEST_PACKET`,
добавь в `NEXT_ACTION` стандартный pipeline **и** секцию
`PASTE_AND_GO_BLOCKS` (см. ниже).

```text
MIXED_FAIL_PIPELINE:
1) /opsx-close-external-gap
   <paste REFACTOR_AND_TEST_PACKET>
2) /opsx-test
   <paste TEST_ONLY_PACKET>
3) /opsx-external-call-coverage base=<RESOLVED_BASE> focus=pg|ch
4) /opsx-external-call-coverage base=<RESOLVED_BASE>
```

### PASTE_AND_GO_BLOCKS (mandatory for mixed FAIL)

Печатай **ровно 4** отдельных fenced `text` блока. Внутри блока —
только команды/пакет (первая строка = команда). Без пояснений внутри блока.
Подставь уже резолвнутый `BASE` (запрещены плейсхолдеры `<BASE>` /
`<HEAD>` когда refs уже известны).

Блок 1 — close PG/CH:

```text
/opsx-close-external-gap

REFACTOR_AND_TEST_PACKET:
- SOURCE: EXTERNAL_CALL_COVERAGE_REPORT
- BASE: <resolved>
- HEAD: <resolved>
- KINDS: [PG|CH]
- ITEMS:
  - SYMBOL: <name>
    KIND: <PG|CH>
    PATH: <path>
    LOC_LINK: <path>:<line>
    DISPOSITION: <WEAK_EVIDENCE|UNTESTABLE_SEAM|MISSING_TEST>
    NEXT: /opsx-close-external-gap
```

Блок 2 — TEST_ONLY:

```text
/opsx-test

TEST_ONLY_PACKET:
- SOURCE: EXTERNAL_CALL_COVERAGE_REPORT
- BASE: <resolved>
- HEAD: <resolved>
- KINDS: [REDIS|WB_WRITE|HTTP|OTHER]
- ITEMS:
  - SYMBOL: <name>
    KIND: <kind>
    PATH: <path>
    LOC_LINK: <path>:<line>
    DISPOSITION: <MISSING_TEST|WEAK_EVIDENCE>
    NEXT: /opsx-test
```

Блок 3 — focus re-audit:

```text
/opsx-external-call-coverage base=<resolved> focus=pg
```

Блок 4 — full gate:

```text
/opsx-external-call-coverage base=<resolved>
```

## COPY_PASTE_RUNBOOK (mandatory in every Final report)

После `DO_NOT_DO_YET` всегда печатай секцию `COPY_PASTE_RUNBOOK` с
готовыми к вставке fenced-блоками. Правила:

1. Если `BASE`/`HEAD` уже резолвнуты — **запрещены** плейсхолдеры
   `<BASE>` / `<HEAD>` / `<ref>` внутри runbook-блоков; только literal refs.
2. Каждый блок начинается с команды первой строкой.
3. Без «описательного» NEXT_ACTION вместо runbook: краткий `NEXT_ACTION`
   + полный `COPY_PASTE_RUNBOOK`.

Минимальные варианты по STATUS:

* `BLOCKED` (no base):

```text
COPY_PASTE_RUNBOOK:
```

```text
/opsx-external-call-coverage base=stage
```

* `FAIL` + только TEST_ONLY: блок `/opsx-test` + пакет, затем
  `/opsx-external-call-coverage base=<resolved>`.
* `FAIL` + только REFACTOR_AND_TEST (PG/CH / UNTESTABLE): блок
  `/opsx-close-external-gap` + пакет (без `base=`), затем
  `/opsx-external-call-coverage base=<resolved> focus=pg`.
* `FAIL` + mixed → используй `PASTE_AND_GO_BLOCKS` (4 блока) как runbook.
* `PASS` + `focus=all`:

```text
/opsx-performance-review scope=base base=<resolved>
```

(when performance trigger applies — DB/query/repository, Queue/TasksManager/
`run_tasks`/`gather`/`create_task`, Semaphore/Lock/Redis NX, pool/cap/
rate-limit/retry/backpressure, or recommended hot async; otherwise skip)

```text
/opsx-static-check
```

```text
/opsx-verify mode=archive <change-name-if-any>
```

* `PASS` + `focus≠all`:

```text
/opsx-external-call-coverage base=<resolved>
```

## Steps

1. Разобрать `base` / `head` / `focus` / `change`.
2. `git rev-parse` оба ref; при ошибке → `BLOCKED`.
3. Прочитать `.cursor/rules/testing-rules.mdc` (authority для level/mocking).
4. Если `change=` — optional read change artifacts / existing
   `TEST_COVERAGE_PACKET` / prior report (не реконструируй из chat).
5. Inventory in-policy changed paths; detect surfaces; assign KIND +
   MINIMUM_LEVEL (kind defaults выше) + `LOC_LINK`. Для PG — также INTENT +
   session mode + `HANDLER_INLINE_SM_CHECK`.
6. Map tests; assign DISPOSITION (PG/CH mock → WEAK / UNTESTABLE;
   `PG_WRONG_SESSION_MODE` / `PG_IMPLICIT_SESSION_MODE` → WEAK;
   no injectable / no parent handoff → `UNTESTABLE_SEAM`, не stop на WEAK).
7. Apply `focus=` filter for summary FAIL set.
8. Если в chat / pasted packet есть prior `GAPS` / `REFACTOR_AND_TEST_PACKET`
   / `CLOSE_RESULTS` / `EXTERNAL_CALL_COVERAGE_REPORT` — построй
   `PROGRESS_VS_PRIOR_PACKET` и `CONVERGENCE` (см. ниже). Если prior нет —
   печатай `PROGRESS_VS_PRIOR_PACKET: not_applicable (no prior packet)`.
9. Печать Final report + `KIND_CLOSURE` + `COPY_PASTE_RUNBOOK`
   (и `PASTE_AND_GO_BLOCKS` при mixed FAIL).
10. Не писать файлы.

## Status

| STATUS | Когда |
|--------|--------|
| `PASS` | нет FAIL-dispositions в активном focus-наборе (`MISSING_TEST`, `WEAK_EVIDENCE`, `UNTESTABLE_SEAM`); `DEFERRED_OWNER` → не PASS |
| `FAIL` | есть хотя бы один `MISSING_TEST` / `WEAK_EVIDENCE` / `UNTESTABLE_SEAM` / `DEFERRED_OWNER` в focus |
| `BLOCKED` | нет/битый `base`, неизвестный token, git error |

`PASS` при нуле in-policy Python или нуле external surfaces — допустим
(`nothing in policy scope` / `no external surfaces in diff`).

`focus≠all` + локальный PASS → `CURRENT_STATE=focus_pass_incomplete_gate`
(не закрывает pre-verify chain).

## Authority boundaries

* Не объявляй archive `GO` / `NO_GO`.
* Не подменяй `/opsx-verify`, `/opsx-static-check`, `/opsx-test`, `/opsx-apply`.
* Не считай PASS доказательством typing allowlist или static-check PASS.
* Не считай PASS доказательством `TEST_COVERAGE_PACKET` adequacy.
* Soft recommend после apply/pyright — этот command сам по себе не hard
  archive gate; verify может additive-сверить report, если он передан.
* Не рефакторь production «чтобы тестировалось» внутри этой команды.
* Не дроби front-door на kind-команды.

## Progress vs prior packet (mandatory when prior exists)

После close↔coverage циклов STATUS часто снова `FAIL`, даже когда работа
сходится. Без явного progress owner воспринимает это как бесконечный круг.

Когда в chat или pasted input есть prior packet / prior GAPS /
`CLOSE_RESULTS` / prior report:

1. Сравни prior symbols с текущим FAIL-set.
2. Печатай блок `PROGRESS_VS_PRIOR_PACKET` (шаблон в Final report).
3. `UNTESTABLE_SEAM` → `WEAK_EVIDENCE` (handoff/mock-only) = **progress**,
   не regression.
4. Назначь `CONVERGENCE: improving | stalled | regressed`:
   - `improving` — есть RESOLVED_TO_COVERED и/или
     PROGRESSED_UNTESTABLE_TO_WEAK, и NEW_GAPS не доминируют без смысла;
   - `stalled` — STILL_SAME_DISPOSITION ≈ prior без прогресса;
   - `regressed` — есть REGRESSED (COVERED→FAIL или WEAK→UNTESTABLE).
5. В `WHAT_HAPPENED` / `WHY` при `FAIL` + progress>0 явно пиши
   `converging loop, not stuck` + краткие counts.
6. Раздели `GAPS` (или аннотируй каждую строку) минимум на:
   - `NEED_SEAM` — `UNTESTABLE_SEAM` / `NO_INJECTABLE_SEAM` /
     `NO_PARENT_SESSION_HANDOFF`;
   - `NEED_INTEGRATION_EVIDENCE` — `WEAK_EVIDENCE` handoff/session-mock
     при уже существующем seam (не reinvent seam);
   - `OTHER_WEAK` — session-mode / `SQL_REWRITE_MOCKED_AWAY` / прочее.

Если prior packet отсутствует — не выдумывай history; пиши
`PROGRESS_VS_PRIOR_PACKET: not_applicable (no prior packet)`.

## Final report (required)

```text
STATUS: PASS | FAIL | BLOCKED

BASE: <ref>
HEAD: <ref>
AUDIT_TARGET: WORKTREE | REF
BASE_SHA: <sha>
TARGET_REF: WORKTREE | <sha>
WORKTREE_TRACKED_CHANGED: <n>
WORKTREE_UNTRACKED_IN_POLICY: <n>
WORKTREE_DELETED: <n>
FOCUS: all | http | wb | pg | ch | redis | other
CHANGE: <name|none>
POLICY: .cursor/rules/testing-rules.mdc

IN_POLICY_CHANGED: <n>
EXTERNAL_SURFACES: <n>
COVERED: <n>
MISSING_TEST: <n>
WEAK_EVIDENCE: <n>
UNTESTABLE_SEAM: <n>
DEFERRED_OWNER: <n>
NO_EXTERNAL_SURFACE_FILES: <n>
OUT_OF_POLICY_SCOPE: <n>

SURFACES_BY_KIND:
  HTTP: <n>
  WB_WRITE: <n>
  PG: <n>
  CH: <n>
  REDIS: <n>
  OTHER: <n>

SURFACES:
- KIND: <kind>
  SYMBOL: <qualname>
  PATH: <path>
  LOC_LINK: <path>:<line>
  BOUNDARY: <short>
  MINIMUM_LEVEL: <level>
  INTENT: <WRITE|PURE_READ|READ_AFTER_WRITE|n/a>   # required when KIND=PG
  MATCHED_TESTS: <list|none>
  DISPOSITION: <disposition>
  NOTE: <short>   # e.g. PG_WRONG_SESSION_MODE | PG_IMPLICIT_SESSION_MODE | …

GAPS:
- NEED_SEAM:
  - <SYMBOL> (<KIND>) @ <LOC_LINK>: <DISPOSITION> → <pasteable next>
- NEED_INTEGRATION_EVIDENCE:
  - <SYMBOL> (<KIND>) @ <LOC_LINK>: <DISPOSITION> → <pasteable next>
- OTHER_WEAK:
  - <SYMBOL> (<KIND>) @ <LOC_LINK>: <DISPOSITION> → <pasteable next>
  # (flat GAPS list OK only if each line is annotated with one of the
  # three labels above)

PROGRESS_VS_PRIOR_PACKET:
- not_applicable (no prior packet)
  # OR when prior exists:
- PRIOR_ITEMS: <n>
- RESOLVED_TO_COVERED: <symbols|none>
- PROGRESSED_UNTESTABLE_TO_WEAK: <symbols|none>  # progress, not regression
- STILL_SAME_DISPOSITION: <symbols|none>
- REGRESSED: <symbols|none>
- NEW_GAPS_NOT_IN_PRIOR: <symbols|none>

CONVERGENCE: improving | stalled | regressed | not_applicable

KIND_CLOSURE:
- KIND: …
  MODE: TEST_ONLY | REFACTOR_AND_TEST
  NEXT: …
  THEN: …

ROUTE_PACKETS:
- TEST_ONLY_PACKET: <present|absent>
- REFACTOR_AND_TEST_PACKET: <present|absent>

MIXED_FAIL_PIPELINE:
- <steps|not_applicable>

PASTE_AND_GO_BLOCKS:
- <4 fenced blocks|not_applicable>

WHAT_HAPPENED:
WHY:
CURRENT_STATE: external_call_pass | external_call_gaps | focus_pass_incomplete_gate | blocked_needs_base
CONVERGENCE: improving | stalled | regressed | not_applicable
OWNER_DECISION_REQUIRED: false | true (<what>)
NEXT_ACTION:
DO_NOT_DO_YET:

COPY_PASTE_RUNBOOK:
- <literal fenced command blocks; no unresolved <BASE>/<HEAD> when refs known>
```

### NEXT_ACTION rules

* Всегда дополняй `COPY_PASTE_RUNBOOK` (и при mixed — `PASTE_AND_GO_BLOCKS`).
* `BLOCKED` (no base) → pasteable ask + runbook блок
  `/opsx-external-call-coverage base=stage` (или другой known base).
* `FAIL` + TEST_ONLY kinds (REDIS / testable WB_WRITE / HTTP) →
  `/opsx-test` затем
  `/opsx-external-call-coverage base=<RESOLVED_BASE> focus=<kind|all>`
  (literal BASE в runbook).
* `FAIL` + PG/CH / `UNTESTABLE_SEAM` / PG|CH `WEAK_EVIDENCE` (mock-only
  / `PG_WRONG_SESSION_MODE` / `PG_IMPLICIT_SESSION_MODE` /
  `NO_INJECTABLE_SEAM` / `NO_PARENT_SESSION_HANDOFF`) →
  `/opsx-close-external-gap` + paste this report (**без** `base=` на close)
  затем coverage `focus=pg|ch` с literal BASE.
  При `NEED_INTEGRATION_EVIDENCE` (WEAK после handoff) — в pasteable
  packet / WHAT_HAPPENED явно: seam уже есть; цель close/test =
  integration evidence, не reinvent `*_in_session`.
* `FAIL` + progress (`CONVERGENCE=improving`) — всё равно FAIL до COVERED,
  но WHAT_HAPPENED MUST сказать `converging loop, not stuck`.
* `FAIL` + mixed (есть и TEST_ONLY, и REFACTOR_AND_TEST) →
  печатай `PASTE_AND_GO_BLOCKS` (4 блока); не оставляй только описание.
* `FAIL` + `DEFERRED_OWNER` → один уточняющий вопрос владельцу.
* `PASS` + `focus=all` → if performance trigger applies →
  `/opsx-performance-review scope=base base=<RESOLVED_BASE>`; else
  `/opsx-static-check`; after performance `PASS`|`PASS_WITH_RISK` (or skip)
  → `/opsx-static-check`, затем `/opsx-verify mode=archive <change-name>` если есть
  активный change. Performance review не обязателен для каждого diff.
* `PASS` + `focus≠all` →
  `/opsx-external-call-coverage base=<RESOLVED_BASE>` (full `focus=all`).

### DO_NOT_DO_YET

* Не archive.
* Не считать `/opsx-static-check` PASS доказательством external-call coverage.
* Не отправлять performance N+1 / queue / concurrency findings в
  `/opsx-close-external-gap` — для них `/opsx-performance-review` /
  `/opsx-performance-fix`.
* Не считать unit green / session-mock PG|CH доказанным coverage.
* Не считать COVERED handoff-only tests, что patch away producer с
  changed PG/CH SQL/qualification (`SQL_REWRITE_MOCKED_AWAY` → WEAK).
* Не считать COVERED PG WRITE / READ_AFTER_WRITE на `read_only=True`.
* Не считать COVERED bare `sm()` (`PG_IMPLICIT_SESSION_MODE`).
* Не считать COVERED PURE_READ на `read_only=False`.
* Не downgrade `UNTESTABLE_SEAM` (`NO_INJECTABLE_SEAM` /
  `NO_PARENT_SESSION_HANDOFF`) до одного только `WEAK_EVIDENCE`.
* Не писать production/tests из этой команды.
* Не делать `/opsx-project-bug-hunt` SoT для session-mode policy.
* Не запускать kind-specific audit front-doors вместо `focus=`.
* Не слать `base=` в `/opsx-close-external-gap`.
* Не использовать `PG_SESSION_HYGIENE` как non-FAIL для bare.
* Не печатать runbook с нерезолвнутыми `<BASE>`/`<HEAD>`, если refs уже известны.
* Не печатать `PATH` без `LOC_LINK` для surface/gap/packet items.
* Не трактовать `FAIL` после close без `PROGRESS_VS_PRIOR_PACKET` как
  «команды зациклились» — при prior packet progress обязателен.
* Не считать `UNTESTABLE`→`WEAK` (handoff) regression или «close ничего
  не сделал».
* Не смешивать `NEED_SEAM` и `NEED_INTEGRATION_EVIDENCE` в один
  undifferentiated GAPS dump без labels.

## Optional handoff artifact (additive)

Если отчёт нужен downstream verify, скопируй блок:

```text
EXTERNAL_CALL_COVERAGE_REPORT:
- STATUS:
- BASE:
- HEAD:
- FOCUS:
- EXTERNAL_SURFACES:
- GAPS: ...
- EVIDENCE_SUMMARY: ...
```

в change context / chat для `/opsx-verify`. Absence of report ≠ auto
`NO_GO` (legacy). Presence → verify independently checks gaps still open.

Не путай с `TEST_COVERAGE_PACKET` (invariant-owned).

## Handoff

| From | To |
|------|-----|
| `/opsx-apply` (recommend chain) | `/opsx-pyright-strict-coverage` then this |
| `/opsx-pyright-strict-coverage` PASS | this with `base=` |
| this PASS (`focus=all`) | conditional `/opsx-performance-review` → `/opsx-static-check` → `/opsx-verify mode=archive` |
| this FAIL TEST_ONLY | `/opsx-test` → rerun |
| this FAIL PG/CH / UNTESTABLE | `/opsx-close-external-gap` (paste report) → focus re-audit |
| this report present | `/opsx-verify` additive consume |

## Regression checks (self)

- [ ] Без `base=` → `BLOCKED`, файлы не менялись
- [ ] Нет write/GO autifix в v1
- [ ] `tests/**` не в FAIL как MISSING production surface
- [ ] Kind split только в отчёте; нет рекомендации создавать
      `/opsx-ch-coverage` и аналоги
- [ ] Не заявлен verify/archive verdict
- [ ] `focus≠all` PASS не закрывает pre-verify chain
- [ ] Final report + KIND_CLOSURE + COPY_PASTE_RUNBOOK напечатаны
- [ ] Prior packet present → `PROGRESS_VS_PRIOR_PACKET` + `CONVERGENCE`
      printed; absent → `not_applicable`
- [ ] FAIL GAPS labeled `NEED_SEAM` / `NEED_INTEGRATION_EVIDENCE` /
      `OTHER_WEAK` (or annotated lines)
- [ ] `UNTESTABLE`→`WEAK` counted as progress, not regression
- [ ] Mixed FAIL → PASTE_AND_GO_BLOCKS (4 literal блока)
- [ ] Runbook без нерезолвнутых `<BASE>`/`<HEAD>` когда refs known
- [ ] MINIMUM_LEVEL следует testing-rules; PG/CH default integration
- [ ] session-mock PG/CH не объявлен COVERED
- [ ] changed CH/PG SQL/qualification + producer fully mocked → WEAK `SQL_REWRITE_MOCKED_AWAY` (не COVERED)
- [ ] PG surfaces имеют INTENT; bare `sm()` → WEAK `PG_IMPLICIT_SESSION_MODE`
- [ ] wrong polarity (WRITE/RAW→True, PURE_READ→False) → WEAK `PG_WRONG_SESSION_MODE`
- [ ] PG/CH FAIL → close-external-gap, не «просто /opsx-test»
- [ ] HANDLER_INLINE_SM_CHECK выполнен для KIND=PG
- [ ] handler/inline `sm(...)` без child session arg → `UNTESTABLE_SEAM`
      (`NO_INJECTABLE_SEAM` / `NO_PARENT_SESSION_HANDOFF`), не только WEAK
- [ ] changed PG/CH boundary без parent→child session/client handoff → `UNTESTABLE_SEAM` (`NO_PARENT_SESSION_HANDOFF`)
- [ ] У каждого surface/gap/packet item есть `LOC_LINK` в формате `<path>:<line>`
