---
description: "Разобрать и, только если безопасно, исправить баг-репорт через reachability, invariant, write-boundary и regression-test gates."
argument-hint: "GO [bug report / Bugbot verdict / CI failure / manual finding]"
---

# /opsx-fix-bug

Используй эту команду для разбора и исправления конкретного баг-репорта от Bugbot, Cursor, Codex, CI, ручного ревью, логов или наблюдения пользователя.

Баг-репорт — это гипотеза, а не инструкция к фиксу.

Перед любыми изменениями команда обязана проверить достижимость runtime-пути, владельца инварианта, write-boundary impact и качество regression-теста.

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
```

Все пояснения, выводы, причины, риски, next action, review checklist и hunter feedback должны быть на русском.

Запрещено выдавать англоязычные секции вроде `Verdict`, `Decision`, `Minimal fix plan`, `Next action`. Используй русские заголовки из output contract ниже.

## Ввод пользователя

```text
$ARGUMENTS
```

## Разрешение на запись

Можно изменять файлы только если ввод пользователя содержит точный отдельный токен:

```text
GO
```

Если `GO` отсутствует:

- не изменяй файлы;
- не делай stage;
- не делай commit;
- не делай push;
- не запускай разрушительные команды;
- выдай только анализ, план, тесты и точное следующее действие.

Даже если `GO` есть, не редактируй production-код, пока итоговый вердикт не стал `fix_now`.

Никогда не делай deploy, restart сервисов, работу с production data, миграции, изменение secrets, merge, rebase, force-push, изменение Kubernetes/infra/CI или unrelated refactor.

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

Используй поиск по репозиторию. Не используй похожесть sibling-кода как доказательство reachability.

Рекомендуемые read-only команды:

```bash
git branch --show-current
git status --short
rg -n "<reported_function>|<reported_class>|<reported_symbol>" .
rg -n "<related_invariant_symbol>|<write_adapter>|<handler_name>" app tests openspec .cursor .github
```

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

Stop conditions:
- ...

Следующее действие:
- точная команда или prompt, который надо выполнить дальше
```

Если вердикт `needs_entrypoint_map`, `Следующее действие` не должно быть `GO to apply`.

Оно должно быть read-only prompt/command для поиска entrypoints.

## Поведение с GO

Когда `GO` есть:

1. сначала выполни тот же forensics;
2. если вердикт не `fix_now`, не редактируй production code;
3. если вердикт `fix_now`, добавь/обнови regression tests до фикса или вместе с фиксом;
4. держи diff минимальным;
5. не патчь dead code без явного обоснования;
6. не трогай forbidden files/actions;
7. запусти targeted verification command, если он доступен;
8. отчитайся по changed files, tests run и unresolved risks.

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

- определи state/mode, который защищается;
- определи, может ли campaign попасть в mutation path из runtime tick;
- определи точную mutation boundary;
- проверь, что protected states blocked;
- проверь, что normal states still proceed;
- не используй sibling ACT paths как доказательство reachability;
- не патчь service internals, если invariant принадлежит manager/candidate/write-boundary level.

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

- diff соответствует invariant, а не только тексту report;
- reachability доказана или явно отмечена как unknown;
- unrelated files не изменены;
- dead-code-only patch не сделан без обоснования;
- regression test падает до fix;
- test доходит до real boundary;
- allowed behavior продолжает работать;
- forbidden behavior blocked;
- source-inspection test не является единственным proof для production bug;
- Bugbot/hunter/OpenSpec updates предложены, если gap находится на process-level.
