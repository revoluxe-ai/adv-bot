---
description: "Audit base..head production changes for external-call surfaces (HTTP/WB/PG/CH/Redis/…) and map each to adequate tests per testing-rules. Read-only."
argument-hint: "base=<branch|ref> [head=<ref>] [focus=all|http|wb|pg|ch|redis|other] [change=<name>]"
---

# /opsx-external-call-coverage

Проверь, что все **in-policy** production surfaces с внешними вызовами из
`base...head` имеют адекватное тестовое evidence по
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
* NOT archive / adequacy verdict (→ `/opsx-verify`).
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
| `head=<ref>` | optional; default `HEAD` |
| `focus=all\|http\|wb\|pg\|ch\|redis\|other` | optional; default `all`. Узкий прогон для отладки; **полный gate** перед verify = `all` |
| `change=<name>` | optional; читать change artifacts / приложить report context |
| иное неизвестное | `STATUS=BLOCKED`, не менять файлы |

Примеры:

- `/opsx-external-call-coverage base=main`
- `/opsx-external-call-coverage base=origin/main head=HEAD`
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
* Опционально (если `change=` и owner явно просит persist): можно
  предложить путь для durable report, но **не писать** без отдельного
  owner GO на persist (v1: chat report only).

### No write GO in v1

В v1 **нет** `GO` режима для автофиксов. Gaps → `/opsx-test` или
`/opsx-apply` (seams), затем rerun этого audit.

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

1. `git diff --name-status <base>...<head>` (three-dot).
2. Для каждого in-policy path: `git diff <base>...<head> -- <path>` +
   Grep/AST-oriented inspection changed functions/methods/classes.
3. Считай surface, если изменённый callable (или его прямо достигнутый
   helper в том же diff) вызывает / планирует вызов внешней границы:
   - client/session execute, request, publish, enqueue;
   - repository/adapter write/read к PG/CH/Redis/WB/HTTP;
   - явный side-effect boundary из domain (WB write, CH insert, …).
4. Не инвентаризируй весь файл «на всякий случай» — только **touched**
   callables и их очевидные callees в том же diff hunk set.
5. Bounded I/O: следуй `.cursor/commands/opsx-execution-preflight.md` и
   `.cursor/commands/opsx-source-resolution.md` (Grep-first; parallel Read ≤ 2).

При сомнении между KIND — выбери наиболее specific (`WB_WRITE` >
`HTTP`; конкретный store > `OTHER`) и запиши `KIND_NOTE`.

## Minimum test level (per testing-rules)

Для каждого surface назначь `MINIMUM_LEVEL` по
`.cursor/rules/testing-rules.mdc` § Minimum test level:

* `unit_component`
* `orchestration_seam`
* `runtime_entrypoint`
* `boundary_adapter`
* `integration`

Правила:

* Не требуй full E2E / `-m integration` автоматически.
* Write-gate / WB destructive → evidence должен доказывать filtering до
  write boundary (не только `assert_not_called()`).
* Mock внешней destructive dependency допустим **после** causal boundary,
  если orchestration path реален.
* Pure DTO/mapping без I/O → обычно не surface (`NO_EXTERNAL_SURFACE`).

## Test mapping

Для каждого surface найди candidate tests:

1. Targeted tests under `tests/` matching module/symbol path.
2. Adjacent feature suite if shared symbol signature changed.
3. Inspect whether test actually exercises the production seam (not only
   a similarly named test).

Dispositions (per surface):

| DISPOSITION | Meaning |
|-------------|---------|
| `COVERED` | есть test evidence ≥ `MINIMUM_LEVEL` с real causal path |
| `MISSING_TEST` | surface testable; адекватного test нет |
| `WEAK_EVIDENCE` | test есть, но name/green без seam proof / write-gate weak |
| `UNTESTABLE_SEAM` | нельзя написать адекватный test без production seam/DI change |
| `OUT_OF_POLICY` | не in-policy |
| `NO_EXTERNAL_SURFACE` | in-policy file/hunk без внешней границы |
| `DEFERRED_OWNER` | нужна owner decision (спорный KIND/level) |

## Steps

1. Разобрать `base` / `head` / `focus` / `change`.
2. `git rev-parse` оба ref; при ошибке → `BLOCKED`.
3. Прочитать `.cursor/rules/testing-rules.mdc` (authority для level/mocking).
4. Если `change=` — optional read change artifacts / existing
   `TEST_COVERAGE_PACKET` / prior report (не реконструируй из chat).
5. Inventory in-policy changed paths; detect surfaces; assign KIND +
   MINIMUM_LEVEL.
6. Map tests; assign DISPOSITION.
7. Apply `focus=` filter for summary FAIL set.
8. Печать Final report (обязательный completion gate).
9. Не писать файлы.

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

## Final report (required)

```text
STATUS: PASS | FAIL | BLOCKED

BASE: <ref>
HEAD: <ref>
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
  BOUNDARY: <short>
  MINIMUM_LEVEL: <level>
  MATCHED_TESTS: <list|none>
  DISPOSITION: <disposition>
  NOTE: <short>

GAPS:
- <SYMBOL> (<KIND>): <DISPOSITION> → <pasteable next>

WHAT_HAPPENED:
WHY:
CURRENT_STATE: external_call_pass | external_call_gaps | focus_pass_incomplete_gate | blocked_needs_base
OWNER_DECISION_REQUIRED: false | true (<what>)
NEXT_ACTION:
DO_NOT_DO_YET:
```

### NEXT_ACTION rules

* `BLOCKED` (no base) → pasteable ask for `base=`.
* `FAIL` + `MISSING_TEST` / `WEAK_EVIDENCE` (testable) →
  `/opsx-test` (targeted) затем
  `/opsx-external-call-coverage base=<BASE>`.
* `FAIL` + `UNTESTABLE_SEAM` → owner GO на минимальный seam via
  `/opsx-apply` (или явный seam task), затем `/opsx-test`, затем rerun.
* `FAIL` + `DEFERRED_OWNER` → один уточняющий вопрос владельцу.
* `PASS` + `focus=all` → `/opsx-static-check`, затем
  `/opsx-verify <change-name>` если есть активный change.
* `PASS` + `focus≠all` →
  `/opsx-external-call-coverage base=<BASE>` (full `focus=all`).

### DO_NOT_DO_YET

* Не archive.
* Не считать `/opsx-static-check` PASS доказательством external-call coverage.
* Не считать unit green / похожее имя test доказанным coverage.
* Не писать production/tests из этой команды.
* Не запускать kind-specific «замену» полного gate.

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
| this PASS (`focus=all`) | `/opsx-static-check` → `/opsx-verify` |
| this FAIL testable | `/opsx-test` → rerun |
| this FAIL untestable | `/opsx-apply` (seam) → `/opsx-test` → rerun |
| this report present | `/opsx-verify` additive consume |

## Regression checks (self)

- [ ] Без `base=` → `BLOCKED`, файлы не менялись
- [ ] Нет write/GO autifix в v1
- [ ] `tests/**` не в FAIL как MISSING production surface
- [ ] Kind split только в отчёте; нет рекомендации создавать
      `/opsx-ch-coverage` и аналоги
- [ ] Не заявлен verify/archive verdict
- [ ] `focus≠all` PASS не закрывает pre-verify chain
- [ ] Final report напечатан
- [ ] MINIMUM_LEVEL следует testing-rules (не «всегда integration»)
