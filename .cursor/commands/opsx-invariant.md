---
description: "Сформировать именованный инвариант из OpenSpec change, diff, bug report или описания пользователя и подготовить handoff в /opsx-bug-hunt или /opsx-fix-bug."
argument-hint: "change=<id> OR desc=<описание> [base=<branch>] [head=<branch>] [scope=<paths>] [target=bug-hunt|fix-bug|both]"
---

# /opsx-invariant

Используй эту команду, когда перед bug hunt / fix-bug нужен точный behavioral invariant.

Цель команды — не чинить код, а превратить размытое описание, OpenSpec change, diff или bug report в проверяемый инвариант с границами, allowed/blocked cases, write-boundaries, reachability hints и готовым handoff для следующей команды.

## Ввод пользователя

```text
$ARGUMENTS
```

## Когда использовать

Используй команду, если пользователь говорит:

- «сформулируй инвариант»;
- «поймай баг локальным bug hunter»;
- «надо проверить change на bypass»;
- «bug-hunt требует invariant»;
- «сначала создай invariant, потом передай в fix-bug»;
- «по этому change / описанию / багу сделай контракт для проверки».

## Важное разделение ролей

Эта команда НЕ должна:

- исправлять production code;
- делать stage/commit/push;
- запускать deploy/restart/migrations;
- превращаться в общий diff review;
- подменять `/opsx-bug-hunt`;
- подменять `/opsx-fix-bug`.

Эта команда должна:

1. собрать входные данные;
2. извлечь или предложить invariant;
3. уточнить недостающие границы;
4. развернуть invariant в проверяемый пакет;
5. выдать готовый handoff для `/opsx-bug-hunt` и/или `/opsx-fix-bug`.

## Read-only режим

Команда всегда read-only.

Разрешено:

- читать repo;
- читать OpenSpec artifacts;
- читать diff;
- искать entrypoints/write-boundaries/tests;
- готовить команды/handoff.

Запрещено:

- менять файлы;
- stage/commit/push;
- править OpenSpec artifacts;
- править Cursor commands;
- запускать destructive commands.

## Минимальные входные данные

Достаточно одного из вариантов:

### Вариант A: OpenSpec change

```text
change=<change-id>
```

Нужно прочитать:

- `openspec/changes/<change-id>/proposal.md`
- `openspec/changes/<change-id>/design.md`, если есть
- `openspec/changes/<change-id>/tasks.md`, если есть
- `openspec/changes/<change-id>/specs/**`, если есть
- `openspec/changes/<change-id>/decisions/**`, если есть

### Вариант B: описание пользователя

```text
desc="<что должно быть верно>"
```

Используй описание как черновик, но не считай его готовым invariant. Разверни его до проверяемого контракта.

### Вариант C: bug report

```text
bug="<текст Bugbot / CI / manual finding>"
```

Извлеки из bug report не fix instruction, а доменный invariant, который мог быть нарушен.

### Вариант D: diff range

```text
base=<branch-or-commit> head=<branch-or-commit>
```

Если нет `change`, `desc` или `bug`, diff range сам по себе недостаточен. В этом случае задай уточнение или предложи 2–5 candidate invariants из diff, но не запускай handoff как final.

## Если данных недостаточно

Если нельзя сформировать проверяемый invariant, остановись и выдай:

```text
Статус:
- needs_input

Почему остановлено:
- ...

Нужно от пользователя:
- change=<id> или desc="..." или bug="..."
- base/head, если нужен diff-aware hunt
- scope, если надо ограничить поиск

Кандидаты invariant, если видны из контекста:
1. ...
2. ...
3. ...
```

Не передавай в `/opsx-bug-hunt` общий текст вида «найди баги в diff».

## Как извлекать invariant из OpenSpec change

Ищи в артефактах:

- Desired behavior;
- Requirements;
- Scenarios;
- Acceptance criteria;
- Decisions;
- Forbidden behavior;
- Rollback/disable plan;
- affected modules;
- task wording around tests/review;
- фразы MUST / MUST NOT / SHALL / SHOULD NOT.

Если в change есть несколько независимых контрактов, не смешивай их в один invariant. Выдай список candidate invariants и выбери primary invariant только если цель пользователя ясна.

## Как развивать invariant

Каждый готовый invariant должен иметь структуру:

```text
Invariant packet:
- name:
- short statement:
- protected states/entities:
- forbidden behavior:
- allowed behavior:
- owner module:
- runtime entrypoint candidates:
- candidate/filter boundary:
- handler/adapter boundary:
- write boundaries:
- data boundaries:
- feature flags / modes / enums:
- related tests:
- weak tests to avoid:
- evidence needed:
- severity if violated:
```

## Критерии хорошего invariant

Хороший invariant:

- проверяет поведение, а не конкретный патч;
- содержит forbidden и allowed cases;
- называет protected state/entity;
- называет границу, где нарушение должно быть остановлено;
- применим к runtime-reachable paths;
- может быть проверен regression test или bug-hunt pass;
- не зависит от одной конкретной функции, если invariant шире;
- не маскирует process gap как code bug.

Плохой invariant:

```text
Добавить filter_structural_act_candidates в delete_keywords_from_wl_by_mean_auto_ctr.
```

Хороший invariant:

```text
A/B Hold structural freeze: campaigns in PENDING_SETUP or ACTIVE must not reach any runtime-reachable structural mutation boundary for whitelist, blacklist, keyword structure, bid/setup/hold writes, while OFF campaigns must keep allowed ACT behavior.
```

## Reachability hints

Если invariant связан с background jobs, campaign state, WB writes, Redis/DB/ClickHouse, Telegram writes или paid/free boundary, обязательно добавь reachability hints:

```text
Reachability hints:
- expected runtime entrypoints:
- scheduler/job/bot/API source:
- manager methods to inspect:
- service/helper paths to inspect:
- tests/inventory to inspect:
- paths that are probably dead/test-only:
```

Не утверждай reachability без доказательства. Для handoff формулируй это как то, что следующая команда должна проверить.

## Handoff target

Определи target:

- `target=bug-hunt` — нужен поиск bypass / missed bug в diff.
- `target=fix-bug` — есть конкретный bug report, надо разобрать и, возможно, чинить.
- `target=both` — сначала bug-hunt, потом fix-bug для найденного конкретного report.

Если target не указан:

- при наличии конкретного bug report используй `fix-bug`;
- при наличии change/diff без конкретного bug report используй `bug-hunt`;
- если пользователь явно просит «передать дальше» — используй `both`.

## Output contract

Выдай результат в такой структуре:

```text
Статус:
- ready / needs_input / ambiguous / blocked

Источник invariant:
- change:
- desc:
- bug:
- base/head:
- scope:

Primary invariant:
- name:
- statement:
- protected states/entities:
- forbidden behavior:
- allowed behavior:
- owner module:
- boundaries:
  - candidate/filter:
  - handler/adapter:
  - write:
  - data:
- runtime entrypoint candidates:
- tests to inspect:
- weak tests to avoid:
- severity if violated:

Candidate invariants not selected:
- ...

Assumptions:
- ...

Open questions:
- ...

Handoff to /opsx-bug-hunt:
```text
/opsx-bug-hunt base=<base> head=<head> invariant="<primary invariant statement>" scope="<scope>" deep
```

Handoff to /opsx-fix-bug:
```text
/opsx-fix-bug bug="<bug report or finding>" invariant="<primary invariant statement>" scope="<scope>"
```

Recommended next step:
- ...
```

Если `status=needs_input`, не выдавай финальную `/opsx-bug-hunt` команду как готовую к запуску. Можно выдать только шаблон с placeholders.

## Специальное правило: bug-hunt handoff

Handoff в `/opsx-bug-hunt` должен содержать:

- base;
- head;
- invariant;
- scope;
- deep, если риск высокий;
- expected boundary types;
- stop condition: no invariant bypass found / needs_entrypoint_map / confirmed bug.

Пример:

```text
/opsx-bug-hunt base=stage head=implement-ab-wb-card-test-mode invariant="A/B Hold structural freeze: campaigns in PENDING_SETUP or ACTIVE must not reach any runtime-reachable structural mutation boundary for whitelist, blacklist, keyword structure, bid/setup/hold writes, while OFF campaigns must keep allowed ACT behavior" scope="app/modules/shop_runner tests/unit/auto_updater_v3/card_ab_hold tests/test_wb_shop_run_coroutines.py openspec/changes/card-ab-hold-mode" deep
```

## Специальное правило: fix-bug handoff

Handoff в `/opsx-fix-bug` должен содержать:

- сам bug report;
- named invariant;
- known/expected write boundary;
- forbidden files/actions, если известны;
- указание, что bug report — гипотеза;
- требование проверить reachability.

Не добавляй `GO` автоматически.

Пример:

```text
/opsx-fix-bug bug="Bugbot: WL trim bypasses hold freeze..." invariant="A/B Hold structural freeze: campaigns in PENDING_SETUP or ACTIVE must not reach runtime-reachable whitelist mutation boundaries, while OFF campaigns must keep allowed WL trimming behavior" scope="app/modules/shop_runner tests/unit/auto_updater_v3/card_ab_hold tests/test_wb_shop_run_coroutines.py"
```

## Специальное правило: если invariant про A/B Hold

Для `card-ab-hold`, `PENDING_SETUP`, `ACTIVE`, `setup`, `hold`, `freeze`, `structural`, `whitelist`, `blacklist`, `bid`, `keyword`, `ACT` обязательно проверить, что invariant packet содержит:

- protected states: `PENDING_SETUP`, `ACTIVE`;
- allowed state: `OFF`, если применимо;
- runtime tick: `WBShop.run -> CoroutinesManager.<method>` или другой доказанный scheduler;
- candidate/filter boundary;
- handler/write boundary;
- tests for blocked and allowed behavior;
- warning: sibling pattern evidence is not reachability evidence.

## Специальное правило: если invariant про paid/free boundary

Обязательно раздели:

- free-visible UI;
- paid automation;
- allowed manual/self-service behavior;
- forbidden paid-core execution;
- Telegram callback boundary;
- service call boundary;
- DB/billing/subscription gates;
- regression tests for both free and paid paths.

## Специальное правило: если invariant про campaign state

Обязательно раздели:

- source state;
- target state;
- trigger/event;
- allowed transitions;
- forbidden transitions;
- idempotency;
- stale stats behavior;
- retries/ticks;
- write boundaries.

## Review checklist

Перед финалом проверь:

- invariant не является патч-инструкцией;
- есть protected и allowed cases;
- есть boundary, где нарушение должно быть поймано;
- base/head не выдуманы;
- scope не слишком широкий;
- handoff не предлагает production changes;
- `/opsx-fix-bug` не получает `GO` автоматически;
- если данных мало — команда остановилась и запросила input.
