---
description: "Разобрать и, только если безопасно, исправить баг-репорт через reachability, invariant, write-boundary и regression-test gates."
argument-hint: "[case=<CASE_ID>] [intake=<INTAKE_ID>] [finding=<FINDING_ID>] [claim_token=<TOKEN>] [GO] [bug report / Bugbot verdict / CI failure / manual finding]"
---

# /opsx-fix-bug

Используй эту команду для разбора и исправления конкретного баг-репорта от Bugbot, Cursor, Codex, CI, ручного ревью, логов или наблюдения пользователя.

Баг-репорт — это гипотеза, а не инструкция к фиксу.

Перед любыми изменениями production-кода или tests команда обязана проверить достижимость runtime-пути, владельца инварианта, write-boundary impact и качество regression-теста.

Перед глубоким анализом сырой bug signal обязан быть записан в durable case map, если `case`/`intake` ещё не переданы.

## Язык ответа

Всегда отвечай пользователю на русском языке.

Допустимы только технические английские токены, если они являются командами, enum-значениями, именами файлов, именами функций, именами тестов, git-хешами или литералами из кода.

Примеры допустимых технических токенов:

```text
GO
fix_now
plan_only
false_positive
needs_entrypoint_map
needs_openspec_update
runtime_reachable
filter_structural_act_candidates
poetry run pytest ...
case=
intake=
finding=
COMMAND_RECEIPT
```

Все пояснения, выводы, причины, риски, next action, review checklist и hunter feedback должны быть на русском.

Запрещено выдавать англоязычные секции вроде `Verdict`, `Decision`, `Minimal fix plan`, `Next action`. Используй русские заголовки из output contract ниже.

## Ввод пользователя

```text
$ARGUMENTS
```

Извлеки при наличии:

```text
case=<CASE_ID>
intake=<INTAKE_ID>
finding=<FINDING_ID>
claim_token=<CLAIM_TOKEN>
GO
```

Оставшийся текст считай raw bug report / finding payload.

## Разрешение на запись

### Production code и tests

Можно изменять production code и tests только если ввод пользователя содержит точный отдельный токен:

```text
GO
```

и итоговый вердикт стал `fix_now`.

### Process artifacts без GO

Если `GO` отсутствует, всё равно разрешены записи только process artifacts внутри:

```text
.tmp/opsx-bug-cases/**
```

Разрешённые process-writes без `GO`:

* создать raw intake через shared contract `/opsx-materialize-bug-queue mode=intake`;
* обновить case/intake/finding/ledger/INDEX через `/opsx-materialize-bug-queue mode=update`;
* сохранить `SOURCE_INTAKE_ID` и recovery fields.

Запрещено без `GO`:

* изменять production code;
* изменять tests;
* изменять любые другие repo paths вне `.tmp/opsx-bug-cases/**`;
* делать stage, commit, push;
* запускать разрушительные команды.

Пользователь не обязан помнить или вручную запускать отдельную materialization-команду перед `/opsx-fix-bug`.

Даже если `GO` есть, не редактируй production-код, пока итоговый вердикт не стал `fix_now`.

Никогда не делай deploy, restart сервисов, работу с production data, миграции, изменение secrets, merge, rebase, force-push, изменение Kubernetes/infra/CI или unrelated refactor.

## Type-check routing

Если вход — пакетный сырой вывод `pyright` / `pyright-strict` / `mypy` (или явный typing-only packet без behavioral defect) — не разбирай его как production bug здесь.

Верни:

```text
NEXT_ACTION: /opsx-fix-types
```

Owner: `.cursor/commands/opsx-fix-types.md`.

`/opsx-fix-bug` остаётся владельцем behavioral production bugs. Если typing fix вскроет behavioral regression — возвращайся сюда уже с bug signal, без автоматического `GO`.

## Durable intake и case map

Единственный authoritative storage:

```text
.tmp/opsx-bug-cases/**
```

Не создавай второй storage layout и не копируй логику записи файлов вне контракта `/opsx-materialize-bug-queue`.

## Source resolution (mandatory)

Следуй `.cursor/commands/opsx-source-resolution.md` до любого широкого repo exploration.
Также следуй `.cursor/commands/opsx-execution-preflight.md` для git/shell ops.

Если переданы `case` / `intake` / `finding` / exact path / receipt `OUTPUT_PATH`:

1. сначала прочитай canonical/exact path;
2. не ищи эти artifacts через `rg` / `find` / glob / Task-explore по всему repo;
3. **не** запускай `git status` / `git branch` до чтения durable source и не делай их обязательными для read-only adjudication без GO;
4. forensics/`rg` разрешены только для **символов кода**, указанных packet'ом после успешного чтения durable source;
5. в output заполни `SOURCE_RESOLUTION` и `EXECUTION_PREFLIGHT`.

Canonical paths:

```text
.tmp/opsx-bug-cases/<CASE_ID>/intakes/<INTAKE_ID>.md
.tmp/opsx-bug-cases/<CASE_ID>/findings/<FINDING_ID>.md
.tmp/opsx-bug-cases/<CASE_ID>/LEDGER.md
.tmp/opsx-bug-cases/INDEX.md
```

Если durable source не найден после direct resolution — `blocked_needs_exact_source` / существующий blocker, а не бесконечный search и не hang на git.

### Если `case` и `intake` отсутствуют

Без `GO` выполни в одном запуске:

1. Persist raw intake через shared contract:

```text
/opsx-materialize-bug-queue mode=intake
```

используя raw bug text текущего ввода как `RAW_REPORT`.

2. Получи `CASE_ID` и `INTAKE_ID` из результата materialize.
3. Только после записи intake продолжай read-only adjudication / forensics.
4. После adjudication выбери ровно один `PERSISTENCE_DECISION` (см. ниже) и persist через `mode=update`.
5. Обнови INDEX recovery row через тот же materialize contract.
6. Верни обычный output contract без `GO` плюс `COMMAND_RECEIPT`.

Intake обязан быть на диске до глубокого анализа. Не начинай широкий forensics, пока raw intake не записан.

### Если `case` и `intake` присутствуют

1. Прочитай durable intake из `.tmp/opsx-bug-cases/<CASE_ID>/intakes/<INTAKE_ID>.md`.
2. Используй `RAW_REPORT` / symptom / context из intake как source of truth для сигнала.
3. Выполни read-only adjudication.
4. Выбери ровно один `PERSISTENCE_DECISION` и persist через `mode=update`.
5. Верни output contract и `COMMAND_RECEIPT`.

### Persistence decision после adjudication

После adjudication для **текущего** `INTAKE_ID` выбери ровно один исход:

```text
PERSISTENCE_DECISION:
- new_finding
- duplicate_intake
```

Similarity / похожесть формулировок **недостаточны** для `duplicate_intake`.

#### Вариант 1 — `new_finding`

Создай новый `FINDING_ID`.

Обязательно:

```text
SOURCE_INTAKE_ID: <current INTAKE_ID>
```

Запрещено обновлять существующий finding, чей `SOURCE_INTAKE_ID` отличается от текущего intake, без явного `relation=duplicate_intake`.

Если уверенности в duplicate нет — выбирай `new_finding`, а не перезапись старого finding.

#### Вариант 2 — `duplicate_intake`

Используй только когда новый raw report и adjudication относятся к уже существующему canonical finding **и** выполнены все условия:

* тот же literal claim либо доказанная эквивалентность claim;
* тот же affected boundary;
* тот же adjudication result;
* есть ссылка на canonical finding;
* нет нового самостоятельного evidence scope.

Тогда persist:

```text
INTAKE_STATUS: closed_duplicate
DISPOSITION: duplicate_intake
CANONICAL_INTAKE_ID: <existing intake>
RELATED_FINDING_ID: <existing finding>
```

Canonical finding **не переписывать** (`unchanged: true`).

Сохрани отдельный результат проверки нового intake:

```text
results/<INTAKE_ID>-duplicate-check.md
```

Вызов materialize:

```text
/opsx-materialize-bug-queue mode=update
case=<CASE_ID>
intake=<current INTAKE_ID>
relation=duplicate_intake
canonical_intake=<CANONICAL_INTAKE_ID>
related_finding=<RELATED_FINDING_ID>
```

#### Запрещённое состояние

Недопустимо:

```text
current INTAKE_ID: INTAKE-002
updated FINDING_ID: FP-001
finding SOURCE_INTAKE_ID: INTAKE-001
relation: absent
```

Такая запись обязана быть остановлена blocker'ом:

```text
cross_intake_finding_update_without_relation
```

### Если передан только `case` или только `intake`

* только `case` без `intake`: используй `PRIMARY_INTAKE_ID` из `CASE.md`, если он есть; иначе создай новый intake в этом case через `mode=intake`;
* только `intake` без `case`: stop с blocker `missing_case_for_intake`, не угадывай case.

### Запрет требовать отдельный intake-командный шаг

Никогда не останавливайся только с текстом «сначала запустите materialize», если можешь сам выполнить shared `mode=intake` в этом же запуске.

Отдельная готовая materialize-команда допустима лишь как recovery blocker, когда process-write объективно невозможен.

## Главная цель

Не патчить функцию, на которую указал баг-репорт, пока не доказано, что это правильная runtime-граница.

Перед фиксом определить, является ли указанный путь:

1. достижимым из реального runtime entrypoint;
2. достижимым только из тестов или dev scripts;
3. dead/legacy code;
4. недостижимым, но указывающим на реальный пропущенный инвариант в sibling path;
5. уже защищённым в другом месте;
6. false positive из-за stale code, stale tests или неполного static analysis.

Если runtime reachability неизвестна, остановись до implementation.

## Обязательный первый проход: bug forensics

Сначала read-only проверь:

1. указанный файл/функцию/класс;
2. всех прямых callers;
3. всех косвенных callers до runtime entrypoints;
4. scheduler/job/bot/API entrypoints;
5. тесты, которые вызывают указанную функцию напрямую;
6. feature flags, modes, guards, enum states и eligibility filters;
7. write boundaries: WB API writes, DB writes, Redis writes, ClickHouse writes, Telegram writes;
8. существующие regression tests вокруг того же инварианта.

Используй поиск по репозиторию только после чтения durable finding/intake (если они переданы) и только для символов/boundaries из этого source. Не используй похожесть sibling-кода как доказательство reachability. Не rediscover finding/intake по всему repo.

Рекомендуемые read-only команды (purpose-driven; см. `opsx-execution-preflight.md`):

```bash
# only if REQUIRED_FOR dirty-tree / branch identity; else skip
# TIME_BUDGET: branch 5s / status 10s; on timeout continue read-only adjudication
git branch --show-current
git status --short

# only after durable source resolved; scope to packet-referenced modules when known
rg -n "<reported_function>|<reported_class>|<reported_symbol>" <packet-scoped-roots-or-app>
rg -n "<related_invariant_symbol>|<write_adapter>|<handler_name>" <packet-scoped-roots>
```

Default without `GO` when `case`/`finding`/`intake` already resolved:

* skip git preflight;
* mark branch/dirty as `deferred_not_required` unless the verdict depends on local dirty state.

Запрещено как первый шаг при известных `case`/`finding`:

```bash
git status --short
rg -n "ROOT-001|FINDING_ID" .
find . -name "ROOT-001.md"
```

Budget: ≤ 3 targeted searches per unresolved code symbol after direct sources are read. Исчерпанный budget → `needs_entrypoint_map` / blocker, не бесконечный explore.
## Классификация достижимости

Каждый баг-репорт должен получить эту классификацию до любого fix plan:

```text
Достижимость:
- runtime_reachable: yes/no/unknown
- runtime_entrypoints:
  - ...
- direct_callers:
  - ...
- indirect_callers:
  - ...
- test_only_callers:
  - ...
- dead_or_legacy_path: yes/no/unknown
- write_boundary_reachable: yes/no/unknown
- evidence_chain:
  - entrypoint -> caller -> reported function -> handler/write boundary
```

Если evidence chain отсутствует, вердикт не может быть `fix_now`.

## Hard stop: reachability unknown

Если репорт заявляет пропущенный guard в функции, но runtime reachability не доказана, вердикт обязан быть:

```text
needs_entrypoint_map
```

В этом случае:

- не выдавай `fix_now`;
- не предлагай `GO to apply`;
- не предлагай production-code changes как основное следующее действие;
- выдай точные поисковые команды/файлы, которые нужны для доказательства или опровержения reachability;
- предложи обновить bug-hunter rule, чтобы он требовал entrypoint evidence.

Доказательства, обязательные перед фиксом:

```text
Цепочка entrypoint:
- scheduler/job/bot/API entrypoint:
- manager coroutine caller:
- direct call site:
- runtime condition:
- handler/write boundary:
```

Если такая цепочка не найдена:

```text
Решение:
- reported path не доказан как runtime-reachable
- пока не патчить reported helper/coroutine
- обновить bug-hunter, чтобы он проверял reachability перед report
- опционально создать отдельную задачу на dead-code или entrypoint inventory
```

## Проверка Bugbot report

Bugbot report подозрителен, пока не доказан.

Перед принятием Bugbot severity:

1. Найди все call sites указанной функции.
2. Классифицируй каждый call site:
   - runtime scheduler/job;
   - bot/API handler;
   - service/manager production path;
   - test-only;
   - dev script;
   - dead/legacy;
   - unknown.
3. Если есть только test-only/dead/unknown callers, понизь до `false_positive` или `needs_entrypoint_map`.
4. Не используй sibling methods как reachability evidence.
5. Не считай missing local guard production-багом, пока не доказан путь к реальному write boundary.
6. Не патчь dead code только чтобы успокоить Bugbot.

## Обязательный invariant analysis

Извлеки доменный инвариант за баг-репортом.

Плохая формулировка:

```text
Добавить filter X в function Y.
```

Хорошая формулировка:

```text
В protected state Z структурная мутация не должна доходить до candidate construction, handler creation, adapter call или external write boundary из любого runtime-reachable path.
```

Всегда разделяй:

- локальный symptom из report;
- реальный domain invariant;
- owner module инварианта;
- все известные write paths, которые могут его нарушить;
- существующие guards;
- missing guards;
- sibling paths, которые дают только pattern evidence;
- tests, которые доказывают invariant на правильной границе.

## Follow-up scope после adjudication

`/opsx-fix-bug` обязан завершить adjudication исходного сигнала и не должен автоматически превращать соседние гипотезы в новые bug cases.

После основного вердикта команда может определить только один follow-up status:

```text
FOLLOW_UP_SCOPE:
- none
- invariant_candidate
- research_candidate_only
```

### `none`

Используй, если после forensics нет отдельного, доказательно сформулированного соседнего риска.

Тогда:

```text
NEXT_ACTION: none
```

### `invariant_candidate`

Используй только если текущий forensics уже дал достаточное evidence для конкретной проверяемой границы:

- сформулирован forbidden effect;
- названа causal boundary;
- названа write boundary или защищаемый state transition;
- есть текущий runtime path или authoritative decision/source;
- candidate не является свободной идеей, общей рекомендацией или повтором отвергнутого literal finding.

Команда должна сохранить в текущем finding:

```text
INVARIANT_CANDIDATE:
ADJACENT_RISK_NOTES:
EVIDENCE_BASIS:
AUTO_MATERIALIZE: false
```

Не создавай новый intake, finding, case или promotion автоматически.

`NEXT_ACTION` должен быть точным handoff в `/opsx-invariant`. Если `/opsx-invariant` принимает `case` и `source_finding`, используй:

```text
/opsx-invariant case=<CASE_ID> source_finding=<FINDING_ID>
```

Если такой input contract ещё не поддержан, верни автономный pasteable prompt для `/opsx-invariant`, включающий:

- `CASE_ID`;
- `SOURCE_FINDING_ID`;
- literal verdict исходного finding;
- `INVARIANT_CANDIDATE`;
- `EVIDENCE_BASIS`;
- запрет создавать production fix;
- требование подтвердить либо отвергнуть invariant candidate.

### `research_candidate_only`

Используй, если появилась соседняя гипотеза, но текущих evidence недостаточно для invariant candidate.

Обязательные поля:

```text
RESEARCH_CANDIDATE:
EVIDENCE_GAP:
REQUIRED_EXTRACTION:
AUTO_MATERIALIZE: false
```

Не создавай новый bug case.

`NEXT_ACTION` должен быть read-only extraction prompt или `none`, если extraction не оправдан.

### Надёжностный gate

Нельзя выбирать `invariant_candidate` только потому, что:

- false positive «может намекать» на другой баг;
- существует теоретический риск freshness/lag/race;
- sibling code выглядит подозрительно;
- отсутствует тест;
- можно придумать более строгий invariant.

Если evidence не проходит gate, выбирай `research_candidate_only` или `none`.

`/opsx-fix-bug` не выполняет bug hunt, не группирует fixes и не материализует соседние bugs.

## Boundary-ownership gate (перед вердиктом выше `plan_only`)

Сопоставь reported write boundary с границей, которой ВЛАДЕЕТ named invariant. Reported boundary, которая ортогональна и обратима (resume/self-heal) и НЕ мутирует замороженную сущность → `false_positive` (или cited allowed-adjudication из accepted decision), не `fix_now`/`needs_openspec_update`. Не патчь границу, которой invariant не владеет — это «починка другой проблемы».

## Decision matrix

### Case A: reachable bug

Используй вердикт `fix_now` только если:

- путь runtime-reachable;
- инвариант нарушен;
- write boundary или внешний side effect достижим;
- fix можно ограничить текущим bug scope;
- regression test может падать до фикса и проходить после.

Тогда:

- добавь или обнови regression test;
- патчь самую узкую правильную границу;
- предпочитай shared guard/candidate filter вместо локального дублирования;
- проверь blocked и allowed behavior.

### Case B: unreachable reported path, invariant protected elsewhere

Используй вердикт `false_positive` или `plan_only`.

Не меняй production logic только ради report.

Корректные действия:

- обновить bug-hunter rules;
- добавить entrypoint inventory;
- удалить или задокументировать dead code только отдельной явной задачей;
- обновить stale tests.

### Case C: unreachable reported path, sibling path may violate same invariant

Используй вердикт `needs_entrypoint_map` или `plan_only`.

Пока не патчь literal reported function.

Вместо этого:

- проверь sibling runtime entrypoints;
- найди реальные write paths;
- исправляй только reachable violating path;
- добавь regression tests против реального entrypoint/write boundary.

### Case D: direct unit-test-only path

Если функцию вызывают только тесты:

- не считай это production impact;
- реши, представляет ли тест intended public behavior;
- если да, перепиши тест вокруг реального entrypoint или documented boundary;
- если нет, обнови/удали stale test с объяснением.

### Case E: process gap, not code bug

Если главная проблема — отсутствующая ownership/entrypoint документация, используй вердикт `needs_openspec_update`.

Не маскируй process gap локальным code patch.

## Output contract без GO

Если `GO` отсутствует, выдай ровно такую структуру и на русском языке:

```text
Вердикт:
- fix_now / plan_only / false_positive / needs_entrypoint_map / needs_openspec_update

Классификация бага:
- источник:
- reported file/function:
- reported severity:
- accepted severity:
- symptom:
- invariant:
- affected write boundary:

Достижимость:
- runtime_reachable:
- runtime_entrypoints:
- direct_callers:
- indirect_callers:
- test_only_callers:
- dead_or_legacy_path:
- write_boundary_reachable:
- evidence_chain:

Решение:
- почему это production bug или не production bug:
- почему предложенный fix находится или не находится на правильной границе:

Минимальный fix plan:
- files allowed:
- files forbidden:
- exact behavior change:
- no-op/dead-code handling:

Regression tests:
- failing-before-fix test:
- blocked case:
- allowed case:
- mutation/write-boundary assertion:
- weak tests to avoid:

Verification commands:
- ...

Bug-hunter / OpenSpec updates:
- entrypoint inventory update needed: yes/no
- hunter rule update needed: yes/no
- source-of-truth update needed: yes/no

Follow-up scope:
- status: none / invariant_candidate / research_candidate_only
- invariant_candidate:
- adjacent_risk_notes:
- evidence_basis:
- research_candidate:
- evidence_gap:
- required_extraction:
- auto_materialize: false

Stop conditions:
- ...

Durable case map:
- CASE_ID:
- INTAKE_ID:
- FINDING_ID:
- SOURCE_INTAKE_ID:
- INDEX_PATH: .tmp/opsx-bug-cases/INDEX.md
- INTAKE_PATH:
- FINDING_PATH:

SOURCE_RESOLUTION:
- mode: exact_path | canonical_id | referenced_source | bounded_fallback
- primary_path:
- fallback_used: true | false
- search_operations:
- search_scope:
- unresolved_gap:

EXECUTION_PREFLIGHT:
- git_branch: skipped | ok | timeout | failed | deferred_not_required
- git_status: skipped | ok | timeout | failed | deferred_not_required
- other_ops:
- blocked_on_preflight: true | false

Persistence:
- decision: new_finding / duplicate_intake
- current_intake:
- canonical_intake:
- finding:
- related_finding:
- relation:

Следующее действие:
- точная pasteable команда или prompt, который надо выполнить дальше

COMMAND_RECEIPT:
  COMMAND: /opsx-fix-bug
  CASE_ID:
  INTAKE_ID:
  FINDING_ID:
  RESULT:
  OUTPUT_PATH:
  NEXT_ACTION:
  PERSISTENCE_DECISION:
  CANONICAL_INTAKE_ID:
  RELATED_FINDING_ID:
```

`RESULT` в receipt без `GO` обычно одно из: `adjudicated`, `false_positive`, `needs_entrypoint_map`, `plan_only`, `blocked`, `duplicate_intake`.

Для `PERSISTENCE_DECISION=duplicate_intake`:

* `FINDING_ID` в receipt = `RELATED_FINDING_ID` (canonical, unchanged);
* `CANONICAL_INTAKE_ID` обязателен;
* `OUTPUT_PATH` указывает на `results/<INTAKE_ID>-duplicate-check.md`.

Для `PERSISTENCE_DECISION=new_finding`:

* `FINDING_ID` = новый finding;
* `SOURCE_INTAKE_ID` finding = текущий `INTAKE_ID`;
* `CANONICAL_INTAKE_ID` / `RELATED_FINDING_ID` пусты.

`NEXT_ACTION` в receipt обязан соответствовать `FOLLOW_UP_SCOPE`:

- `none` → `none`;
- `invariant_candidate` → точный handoff в `/opsx-invariant`;
- `research_candidate_only` → точный read-only extraction handoff либо `none`.

`OUTPUT_PATH` указывает на finding packet или intake path, если finding ещё не создан.

Если вердикт `needs_entrypoint_map`, `Следующее действие` не должно быть `GO to apply`.

Оно должно быть read-only prompt/command для поиска entrypoints.

После потери чатов продолжение восстанавливается из `.tmp/opsx-bug-cases/INDEX.md` по полям recovery row case.

## Поведение с GO

Когда `GO` есть:

1. если `case`/`intake` отсутствуют, всё равно сначала создай durable intake через shared `mode=intake`, затем forensics;
2. выполни тот же forensics;
3. если вердикт не `fix_now`, не редактируй production code; process-artifacts updates через `mode=update` всё ещё допустимы;
4. если вердикт `fix_now`, добавь/обнови regression tests до фикса или вместе с фиксом;
5. держи diff минимальным;
6. не патчь dead code без явного обоснования;
7. не трогай forbidden files/actions;
8. запусти targeted verification command, если он доступен;
9. отчитайся по changed files, tests run, durable case/intake/finding ids и unresolved risks;
10. заверши `COMMAND_RECEIPT` с `CASE_ID` / `INTAKE_ID` / `FINDING_ID` / `PERSISTENCE_DECISION`.

Если баг требует более широкого изменения поведения, чем покрывает текущий report, остановись и предложи OpenSpec change вместо silent scope expansion.

## Testing rules

Regression tests должны доказывать invariant на правильной границе.

Для write-gate bugs тесты должны доказать, что запрещённая entity не доходит до одного из уровней:

- candidate list;
- handler construction;
- write adapter;
- WB API call;
- DB mutation;
- Redis mutation;
- ClickHouse mutation;
- Telegram output;
- scheduler/runtime entrypoint.

Слабые тесты запрещены как главное доказательство:

- только `assert_not_called()` без доказательства call path;
- только `count == 0`;
- mock guard/filter, который как раз проверяется;
- direct test dead helper без доказательства runtime reachability;
- source-inspection-only test как единственный regression;
- тест, который всё ещё проходит после удаления нужного guard.

Предпочитай paired tests:

- blocked case: protected entity не должна дойти до write boundary;
- allowed case: normal entity всё ещё должна доходить до write boundary.

Source-inspection wiring tests допустимы только как secondary guardrails. Они недостаточны для доказательства production impact.

## WB Sky high-risk areas

Для багов в этих зонах будь строже:

- campaign state;
- bidding;
- CPO/CPA/budget logic;
- whitelist/blacklist mutations;
- keyword structural mutations;
- WB API writes;
- Redis/PostgreSQL/ClickHouse consistency;
- async jobs/schedulers/workers;
- paid/free boundary;
- Telegram callback/UI write behavior.

Для этих зон всегда определи:

```text
runtime entrypoint -> manager/service -> candidate/filter -> handler/adapter -> write boundary
```

Не принимай fix plan, который сводится к “add guard in helper”.

## Specific rule: A/B Hold / structural freeze

Для reports про A/B Hold, freeze, setup, pending, active, hold, structural-act, whitelist, blacklist, keyword или bid mutation:

- state/mode, mutation boundary, reachability; protected blocked/OFF proceeds; sibling ACT ≠ reachability; не патчь helper если owner — manager/candidate/write-boundary.
- Scheduling (PG SoT) vs Redis ENTER; local PG miss ≠ fix_now если schedule режет non-OFF; stale ComplexAdv.mode ≠ «игнор PG»; no fresh read — wrong boundary.
- Interrupt: structural exits (apply + finally sync/target-place).

## Specific rule: entrypoint inventory

Если баг вскрывает, что entrypoints не задокументированы, предложи обновить entrypoint inventory.

Inventory должен фиксировать:

```text
Entrypoint name:
- scheduler/job/bot/API source:
- manager method:
- service/handler path:
- write boundaries:
- protected invariants:
- tests covering it:
```

Не создавай большой documentation refactor внутри bugfix, если пользователь явно этого не попросил.

## Specific rule: hunter feedback loop

Если Bugbot, opsx-hunt-bug или другой hunter пропустил или неправильно классифицировал проблему, выдай hunter update note:

```text
Hunter feedback:
- missed/misclassified condition:
- required new check:
- example false positive/false negative:
- suggested rule:
- suggested fixture/test:
```

Текст значений должен быть на русском, кроме имён функций, файлов, тестов и технических токенов.

Цель — не дать тому же классу багов снова дойти до Bugbot.

## Final output after GO

Если изменения внесены, выдай:

```text
Вердикт:
- fixed / not_fixed

Изменённые файлы:
- ...

Что изменено:
- ...

Regression tests:
- ...

Verification:
- command:
- result:

Оставшиеся риски:
- ...

Follow-up:
- bug-hunter update:
- OpenSpec/source update:
- review checklist:
```

Если изменения не внесены, потому что вердикт не `fix_now`, выдай:

```text
Вердикт:
- no_code_change

Причина:
- ...

Следующее правильное действие:
- ...
```

## Review checklist

Перед завершением проверь:

- raw intake записан до глубокого анализа, если case/intake не были переданы;
- выбран ровно один `PERSISTENCE_DECISION`: `new_finding` или `duplicate_intake`;
- при `new_finding` создан новый finding с `SOURCE_INTAKE_ID` = текущий intake;
- при `duplicate_intake` canonical finding не изменён; intake закрыт как `closed_duplicate`;
- не обновлён finding чужого intake без `relation=duplicate_intake`;
- finding persisted через `mode=update` согласно persistence decision;
- INDEX recovery row обновлён и содержит pasteable `NEXT_ACTION`;
- без `GO` изменены только paths под `.tmp/opsx-bug-cases/**`;
- diff соответствует invariant, а не только тексту report;
- reachability доказана или явно отмечена как unknown;
- unrelated files не изменены;
- dead-code-only patch не сделан без обоснования;
- regression test падает до fix;
- test доходит до real boundary;
- allowed behavior продолжает работать;
- forbidden behavior blocked;
- source-inspection test не является единственным proof для production bug;
- Bugbot/hunter/OpenSpec updates предложены, если gap находится на process-level;
- `FOLLOW_UP_SCOPE` выбран по evidence, а не по свободной гипотезе;
- при `invariant_candidate` сохранены `INVARIANT_CANDIDATE` и `EVIDENCE_BASIS`;
- при `research_candidate_only` сохранены `EVIDENCE_GAP` и `REQUIRED_EXTRACTION`;
- `AUTO_MATERIALIZE` всегда `false`;
- adjacent note не создал новый intake/finding/case автоматически;
- `COMMAND_RECEIPT` содержит `CASE_ID`, `INTAKE_ID`, `FINDING_ID`, `PERSISTENCE_DECISION`.

## Acceptance scenario (durable intake)

Ожидаемый путь одной команды без `GO`:

```text
raw user bug report
→ /opsx-fix-bug <report>          # без GO, без case/intake
→ mode=intake пишет intakes/<INTAKE_ID>.md до глубокого анализа
→ CASE_ID и INTAKE_ID созданы
→ read-only adjudication
→ PERSISTENCE_DECISION=new_finding
→ mode=update пишет новый finding с SOURCE_INTAKE_ID=<current intake>
→ INDEX.md recovery row обновлён
→ чаты потеряны
→ продолжение из .tmp/opsx-bug-cases/INDEX.md через pasteable NEXT_ACTION
```

## Acceptance scenario (intake dedup / linkage)

```text
1. INTAKE-001 → new_finding FP-001 (SOURCE_INTAKE_ID=INTAKE-001)
2. повторный аналогичный raw signal → INTAKE-002
3. adjudication доказывает duplicate (тот же claim/boundary/result, нет нового evidence scope)
4. PERSISTENCE_DECISION=duplicate_intake
5. ожидаемый результат:

INTAKE-002:
  STATUS: closed_duplicate
  DISPOSITION: duplicate_intake
  CANONICAL_INTAKE_ID: INTAKE-001
  RELATED_FINDING_ID: FP-001

FP-001:
  SOURCE_INTAKE_ID: INTAKE-001
  unchanged: true

results/INTAKE-002-duplicate-check.md существует

6. если второй сигнал содержит новый evidence scope:

INTAKE-002
→ PERSISTENCE_DECISION=new_finding
→ новый FINDING_ID
→ SOURCE_INTAKE_ID: INTAKE-002

7. запрещённый исход останавливается blocker'ом cross_intake_finding_update_without_relation
```