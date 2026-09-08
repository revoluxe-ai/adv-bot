---

description: "Сформировать именованный behavioral invariant, материализовать ROOT_FINDING_PACKET для root-aware bug hunt и дополнительно подготовить additive TEST_COVERAGE_PACKET."
argument-hint: "change=<id> OR desc=<описание> OR bug=<bug-report> [classification=<value>] [verdict=<value>] [base=<branch>] [head=<branch>] [scope=<paths>] [target=bug-hunt|fix-bug|both]"
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# /opsx-invariant

Используй эту команду, когда перед `/opsx-bug-hunt` или `/opsx-fix-bug` нужен точный behavioral invariant.

Команда должна:

1. превратить размытое описание, OpenSpec change, diff или bug report в проверяемый invariant;
2. определить protected states, allowed behavior, forbidden behavior и runtime boundaries;
3. подготовить handoff для следующей команды;
4. при наличии конкретного bug report материализовать отдельный `ROOT_FINDING_PACKET`;
5. передать `ROOT_FINDING_PACKET` в root-aware `/opsx-bug-hunt`;
6. дополнительно сформировать additive `TEST_COVERAGE_PACKET`, связывающий invariant с необходимыми behavioral test scenarios.

Команда не исправляет код или тесты.

Команда не подтверждает баг без evidence.

Команда не должна подменять:

* `/opsx-fix-bug`;
* `/opsx-classify-bug`;
* `/opsx-bug-hunt`;
* `/opsx-learn-from-bug`;
* отдельное test planning или test implementation.

## Ввод пользователя

```text
$ARGUMENTS
```

## Когда использовать

Используй команду, если пользователь говорит:

* «сформулируй инвариант»;
* «подготовь invariant для bug hunt»;
* «проверь change на bypass»;
* «передай корневой баг в bug hunter»;
* «сначала создай invariant, потом fix-bug»;
* «из этого Bugbot finding сделай проверяемый контракт»;
* «нужно найти соседние нарушения того же правила»;
* «нужно надёжно отличить root bug от child findings»;
* «определи, какими тестовыми сценариями должен доказываться invariant».

## Важное разделение ролей

Эта команда НЕ должна:

* исправлять production code;
* создавать или исправлять tests;
* изменять OpenSpec artifacts;
* изменять Cursor commands;
* делать stage, commit или push;
* запускать deploy, restart или migrations;
* создавать Git branch или worktree;
* восстанавливать, применять, удалять или изменять Git stash;
* превращаться в общий diff review;
* превращаться в полный test audit;
* подтверждать production reachability без evidence;
* объявлять сырой Bugbot finding подтверждённым багом;
* объявлять существующее test coverage достаточным только по названию test;
* запускать bug hunt;
* запускать learning;
* запускать implementation commands.

Эта команда должна:

1. собрать входные данные;
2. прочитать релевантные OpenSpec artifacts;
3. прочитать diff и runtime boundaries, если они доступны;
4. извлечь или предложить invariant;
5. уточнить недостающие границы;
6. развернуть invariant в проверяемый packet;
7. при наличии конкретного root bug сформировать `ROOT_FINDING_PACKET`;
8. сформировать additive `TEST_COVERAGE_PACKET`;
9. выдать готовый handoff для `/opsx-bug-hunt` и/или `/opsx-fix-bug`.

## Read-only режим

Команда всегда read-only.

Разрешено:

* читать repository;
* читать OpenSpec artifacts;
* читать diff;
* искать runtime entrypoints;
* искать write, mutation, transition и data boundaries;
* искать tests;
* проверять реальные model, DTO, enum и state shapes;
* анализировать test seams и mocking boundaries;
* подготавливать packets и handoff commands.

Запрещено:

* менять файлы;
* stage, commit или push;
* выполнять destructive Git commands;
* менять OpenSpec;
* менять production code;
* менять tests;
* запускать implementation commands с `GO`;
* создавать patches.

## Входные параметры

Извлеки из `$ARGUMENTS`:

* `change`: OpenSpec change ID.
* `case`: durable bug CASE_ID, if present.
* `finding` / `source_finding`: durable FINDING_ID or packet path.
* `desc`: пользовательское описание ожидаемого поведения.
* `bug`: конкретный bug report, Bugbot finding, CI finding или manual finding.
* `classification`: ранее полученная классификация, если она явно передана.
* `verdict`: ранее полученный literal verdict, если он явно передан.
* `base`: branch или commit для сравнения.
* `head`: branch или commit для анализа.
* `scope`: paths или modules, ограничивающие анализ.
* `target`: `bug-hunt`, `fix-bug` или `both`.

## Source resolution (mandatory)

Следуй `.cursor/commands/opsx-source-resolution.md`.
Также следуй `.cursor/commands/opsx-execution-preflight.md`: не запускай unconditional `git status`/`git branch` до чтения exact change/finding; git только если REQUIRED_FOR base/head/dirty claim.

* `change=<id>` → читай только `openspec/changes/<id>/...` exact paths; не делай inventory всего `openspec/` без `EVIDENCE_GAP`.
* `case`/`finding` → сначала `.opsx/runs/bug-cases/<CASE_ID>/findings/<FINDING_ID>.md`.
* `scope=` ограничивает любой последующий code search.
* Budget: ≤ 3 targeted searches на незакрытый evidence target после direct reads.
* В финальном output включи `SOURCE_RESOLUTION` и при необходимости `EXECUTION_PREFLIGHT`.

Не используй distant chat history как единственное evidence для:

* `verdict`;
* `classification`;
* `runtime_path`;
* confirmed production reachability;
* `pre_fix_ref`;
* достаточности test coverage;
* реальной формы production model или DTO.

Такие факты должны быть:

* переданы в `$ARGUMENTS`;
* найдены в явном source artifact;
* или подтверждены прямым repository evidence.

## Минимальные входные данные

Достаточно одного из следующих вариантов.

### Вариант A: OpenSpec change

```text
change=<change-id>
```

Прочитай:

* `openspec/changes/<change-id>/proposal.md`;
* `openspec/changes/<change-id>/design.md`, если существует;
* `openspec/changes/<change-id>/tasks.md`, если существует;
* `openspec/changes/<change-id>/specs/**`, если существуют;
* `openspec/changes/<change-id>/decisions/**`, если существуют.

Не запускай `find openspec` / repo-wide inventory, когда `change-id` уже известен.

### Вариант B: описание пользователя

```text
desc="<что должно быть верно>"
```

Используй описание как черновик.

Не считай его готовым invariant.

Разверни его до проверяемого behavioral contract.

### Вариант C: bug report

```text
bug="<текст Bugbot, CI или manual finding>"
```

Извлеки:

* literal claim;
* protected state или entity;
* forbidden observable behavior;
* предполагаемый causal boundary;
* предполагаемый write, mutation или transition boundary;
* candidate invariant.

Bug report является гипотезой, пока отдельное evidence не подтверждает его.

### Вариант D: diff range

```text
base=<branch-or-commit> head=<branch-or-commit>
```

Если нет `change`, `desc` или `bug`, один diff range недостаточен.

В этом случае:

* предложи 2–5 candidate invariants;
* верни `status=needs_input` или `status=ambiguous`;
* не выдавай готовый root-aware bug-hunt handoff.

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
- scope, если требуется ограничение
- verdict/classification, если root bug уже подтверждался отдельно

Candidate invariants:
1. ...
2. ...
3. ...
```

Не передавай в `/opsx-bug-hunt` общий запрос вида:

```text
найди баги в diff
```

Недостаточное test evidence само по себе не должно менять прежний статус команды с `ready` на `blocked`, если invariant и обязательные handoff-поля уже готовы.

## Извлечение invariant из OpenSpec

Ищи:

* Requirements;
* Scenarios;
* Desired behavior;
* Acceptance criteria;
* Decisions;
* Forbidden behavior;
* lifecycle transitions;
* retry semantics;
* idempotency semantics;
* rollback и disable behavior;
* affected modules;
* task wording around tests and review;
* фразы `MUST`, `MUST NOT`, `SHALL`, `SHOULD NOT`.

При конфликте используй authority order проекта.

Не превращай proposed или draft decision в confirmed runtime fact без явной маркировки.

Если change содержит несколько независимых контрактов:

* перечисли candidate invariants;
* выбери primary invariant только когда цель пользователя ясна;
* не смешивай независимые contracts в один overly broad invariant.

## Как развивать invariant

Каждый готовый invariant должен содержать:

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
- transition boundaries:
- data boundaries:
- feature flags / modes / enums:
- related tests:
- weak tests to avoid:
- evidence needed:
- severity if violated:
```

## Критерии хорошего invariant

Хороший invariant:

* проверяет поведение, а не конкретный patch;
* содержит forbidden и allowed cases;
* называет protected state или entity;
* называет boundary, где нарушение должно быть остановлено;
* применим к runtime-reachable paths;
* может быть проверен regression test;
* может использоваться bug hunter для поиска разных causal paths;
* не зависит только от одной функции, если правило шире;
* не маскирует spec gap как code bug;
* позволяет отличить известный root bug от нового bypass.

Плохой invariant:

```text
Добавить filter_structural_act_candidates в delete_keywords_from_wl_by_mean_auto_ctr.
```

Хороший invariant:

```text
A/B Hold structural freeze: campaigns in PENDING_SETUP or ACTIVE must not reach any runtime-reachable structural mutation boundary for whitelist, blacklist, keyword structure, bid, setup or hold writes, while OFF campaigns must preserve allowed ACT behavior.
```

# Additive test coverage materialization

Эта секция расширяет существующий контракт команды и не изменяет его прежнюю семантику.

Команда по-прежнему формирует:

* `Invariant packet`;
* `Primary invariant`;
* `ROOT_FINDING_PACKET`;
* прежние handoff-блоки.

Дополнительно команда должна попытаться сформировать:

```text
TEST_COVERAGE_PACKET
```

`TEST_COVERAGE_PACKET` описывает, какие behavioral scenarios и runtime seams должны доказывать invariant тестами.

Он:

* не является test implementation plan;
* не создаёт тесты;
* не изменяет tests;
* не подтверждает, что существующие tests достаточны;
* не заменяет отдельный test audit;
* не меняет прежний verdict или handoff eligibility.

Если test evidence недостаточно, верни:

```text
TEST_COVERAGE_STATUS: provisional
```

или:

```text
TEST_COVERAGE_STATUS: not_materialized
```

и явно перечисли недостающие данные.

## Назначение TEST_COVERAGE_PACKET

Packet должен связать:

```text
requirement / scenario
→ invariant
→ production entrypoint or orchestration seam
→ protected boundary
→ required behavioral tests
→ weak-test risks
```

Он должен помогать предотвращать следующие test escapes:

* тест повторяет ошибочное предположение implementation;
* fixture создаёт поле или состояние, которого нет в реальной модели;
* causal boundary полностью замокана;
* тест покрывает только happy path;
* отсутствует next-tick, retry, residual или sibling-state case;
* source of truth заменён искусственным fixture value;
* handler или adapter wiring не проверяется на реальной форме входных данных;
* assertion проверяет implementation detail, но не observable behavior;
* похожее имя test ошибочно принимается за доказанное coverage;
* green unit tests ошибочно принимаются за доказательство production wiring.

## Поля TEST_COVERAGE_PACKET

```text
TEST_COVERAGE_PACKET:
- TEST_COVERAGE_STATUS:
- SOURCE_REQUIREMENTS:
- INVARIANT:
- PRODUCTION_ENTRYPOINTS:
- ORCHESTRATION_SEAMS:
- PROTECTED_BOUNDARIES:
- REQUIRED_BEHAVIORAL_SCENARIOS:
- REQUIRED_ALLOWED_SIBLING_SCENARIOS:
- REQUIRED_RESIDUAL_OR_REPEATED_INVOCATION_SCENARIOS:
- REQUIRED_FAILURE_OR_EMPTY_STATE_SCENARIOS:
- REALITY_CONSTRAINTS:
- MOCKING_CONSTRAINTS:
- MINIMUM_TEST_LEVEL:
- UNIT_SUFFICIENCY:
- EXISTING_TESTS_TO_INSPECT:
- COVERAGE_GAPS:
- WEAK_TEST_PATTERNS:
- EVIDENCE_STATUS:
- MISSING_EVIDENCE:
```

## TEST_COVERAGE_STATUS

Разрешённые значения:

```text
ready
provisional
not_materialized
not_applicable
```

### ready

Используй, когда:

* invariant materialized;
* production entrypoint или orchestration seam достаточно определён;
* protected boundary названа;
* required scenarios сформулированы behavioral terms;
* reality и mocking constraints определены.

### provisional

Используй, когда:

* packet пригоден как input для test planning или verify review;
* часть runtime seams или existing tests остаётся candidate или unconfirmed;
* uncertainty явно перечислена.

### not_materialized

Используй, когда:

* invariant готов;
* но данных недостаточно, чтобы назвать meaningful test seams или scenarios без угадывания.

### not_applicable

Используй, когда:

* пользователь явно запросил только conceptual invariant без repo, change или bug context;
* test mapping не имеет достаточного operational context.

## SOURCE_REQUIREMENTS

Укажи exact requirement, scenario, decision или пользовательское описание, из которого выведен test contract.

Не придумывай requirement ID.

Если source только `desc`, укажи:

```text
SOURCE_REQUIREMENTS:
- user_description_only
```

Если requirement является draft или proposed, сохрани этот статус.

## PRODUCTION_ENTRYPOINTS и ORCHESTRATION_SEAMS

Разделяй:

* production entrypoint — scheduler, worker, bot callback, API, CLI/admin или другой runtime source;
* orchestration seam — минимальная тестируемая manager/service/function boundary, через которую проходит реальное behavior;
* component seam — более узкий helper или adapter.

Не требуй full end-to-end test автоматически.

Предпочитай минимальную seam, которая сохраняет:

* causal path;
* реальную форму данных;
* protected boundary;
* observable behavior.

Если entrypoint не доказан, используй candidate-маркировку.

## REQUIRED_BEHAVIORAL_SCENARIOS

Сценарии должны быть сформулированы через:

```text
starting state or input
→ trigger
→ allowed observable result
→ forbidden observable result
```

Не формулируй scenario как название patch или конкретный internal helper call, если invariant шире.

Internal calls допустимы только как дополнительные boundary assertions, а не как единственное доказательство behavior.

## REQUIRED_ALLOWED_SIBLING_SCENARIOS

Для каждого forbidden case укажи соседний allowed case, если он существует.

Примеры:

* `complete` запрещает повторный external sync, а `pending/partial` разрешает retry;
* protected mode блокирует mutation, а `OFF` сохраняет разрешённое поведение;
* free path блокирует paid automation, а paid path остаётся разрешённым;
* missing source data fail-closes, а valid source data проходит.

Allowed sibling scenario должен проверять, что guardrail не стал слишком широким.

## REQUIRED_RESIDUAL_OR_REPEATED_INVOCATION_SCENARIOS

Обязательно рассмотри это поле для:

* lifecycle или state-machine invariant;
* retries;
* repeated scheduler ticks;
* idempotency;
* partial completion;
* durable status и незавершённого transition;
* stale state;
* interrupted activation или finalization;
* callback повторного нажатия;
* restart или crash window.

Если поле неприменимо, укажи:

```text
not_applicable: <reason>
```

## REQUIRED_FAILURE_OR_EMPTY_STATE_SCENARIOS

Проверь применимость:

* missing field или source;
* `NULL`;
* empty collection;
* stale data;
* exception или fallback;
* partial response;
* duplicate rows или events;
* wrong identity или type;
* unavailable dependency.

Не добавляй все случаи механически.

Выбирай только случаи, связанные с invariant и protected boundary.

Пустая или degenerate collection, которая всё ещё достигает terminal, success, transition или write boundary, не должна автоматически считаться safe no-op.

## REALITY_CONSTRAINTS

Опиши, какие факты test не имеет права выдумывать.

Примеры:

* использовать реальную форму production model или DTO;
* не добавлять synthetic attribute, которого нет в schema;
* получать identity из фактического owner object;
* использовать настоящий enum и допустимое state combination;
* различать live read model и durable field;
* сохранять production type: UUID, string, integer и другие semantics;
* строить residual state, реально возможный между двумя ticks;
* использовать реальную форму callback payload;
* не подменять source of truth удобным fixture value.

## MOCKING_CONSTRAINTS

Назови boundary, которую нельзя полностью замокать, если именно через неё проверяется invariant.

Разрешай mocks:

* за пределами causal path;
* на внешних destructive dependencies;
* когда observable contract и реальная input shape сохраняются.

Если causal boundary полностью замокана, отметь такой test как слабый.

Mock внешней API write может быть допустим, если тест реально проходит через production orchestration и проверяет отсутствие или наличие вызова на правильном state.

## MINIMUM_TEST_LEVEL

Используй одно или несколько значений:

```text
unit_component
orchestration_seam
runtime_entrypoint
boundary_adapter
integration
manual_only
unknown
```

Не повышай автоматически каждый invariant до integration или full E2E.

Выбирай минимальный уровень, который способен доказать:

* observable behavior;
* production wiring;
* causal path;
* protected boundary;
* required sibling behavior.

## UNIT_SUFFICIENCY

Верни одно из:

```text
sufficient
conditionally_sufficient
insufficient
unknown
```

Объясни условие.

Unit test недостаточен, если он:

* подменяет реальную model shape;
* полностью замыкает causal boundary mock-ом;
* не проверяет runtime wiring;
* не способен воспроизвести residual или repeated invocation;
* не проверяет source-of-truth boundary, являющуюся сутью invariant.

Unit test может быть достаточен на orchestration seam, если:

* seam является реальной production boundary;
* production state воспроизводится без synthetic fields;
* external destructive dependencies замоканы за causal boundary;
* observable allowed и forbidden results проверяются.

## Existing tests

Команда может искать и перечислять существующие tests.

Наличие похожего имени test не доказывает coverage.

Для каждого важного existing test укажи, если evidence доступно:

* какую state/input форму он строит;
* какие boundaries mock-ает;
* какой observable result проверяет;
* какой required scenario остаётся непокрытым.

Не превращай эту секцию в полный test audit, если пользователь не запросил его отдельно.

## Coverage gaps

Не объявляй gap только потому, что не найден test с ожидаемым названием.

Coverage gap должен быть связан с отсутствием evidence для конкретного required behavioral scenario.

Допустимые формулировки:

```text
confirmed gap
candidate gap
unknown due to incomplete test inspection
```

## Relation to existing handoffs

Добавление `TEST_COVERAGE_PACKET` не изменяет eligibility существующих handoff:

* `/opsx-bug-hunt` продолжает получать invariant и `ROOT_FINDING_PACKET`;
* `/opsx-fix-bug` продолжает получать bug, invariant и boundary без `GO`;
* отсутствие `TEST_COVERAGE_STATUS=ready` не запрещает прежний handoff, если его собственные условия выполнены.

`TEST_COVERAGE_PACKET` может быть передан downstream как дополнительный context, но существующие handoff formats не должны становиться несовместимыми.

# Reachability hints

Если invariant связан с:

* background jobs;
* campaign state;
* WB writes;
* Redis, PostgreSQL или ClickHouse;
* Telegram callbacks;
* paid/free boundary;
* scheduler retries;
* lifecycle transitions;

добавь отдельную секцию:

```text
Reachability hints:
- expected runtime entrypoints:
- scheduler/job/bot/API source:
- manager methods to inspect:
- service/helper paths to inspect:
- tests/inventory to inspect:
- paths probably dead or tests-only:
- evidence warnings:
```

Не размещай `TEST_COVERAGE_PACKET` внутри `Reachability hints`.

Не утверждай reachability без evidence.

Для handoff указывай:

* proven runtime paths как `proven`;
* candidate runtime paths как `candidate`;
* missing evidence как `missing`.

# Root finding materialization

Если на входе есть конкретный `bug`, команда должна попытаться сформировать отдельный:

```text
ROOT_FINDING_PACKET
```

Invariant и root finding — разные сущности.

`Invariant packet` описывает общее правило.

`ROOT_FINDING_PACKET` описывает конкретный уже известный или предполагаемый способ нарушения этого правила.

## Обязательные поля ROOT_FINDING_PACKET

```text
ROOT_FINDING_PACKET:
- ROOT_FINDING_ID:
- TITLE:
- LITERAL_CLAIM:
- CONFIRMED_VERDICT:
- CLASSIFICATION:
- RUNTIME_PATH:
- CAUSAL_BOUNDARY:
- WRITE_BOUNDARY:
- INVARIANT:
- PRE_FIX_REF:
```

## Дополнительные поля

```text
- OWNER_MODULE:
- REPORTED_SEVERITY:
- ACCEPTED_SEVERITY:
- REGRESSION_SCENARIO:
- KNOWN_FIX_BOUNDARY:
- ROOT_FIX_STATUS:
- EVIDENCE_STATUS:
- MISSING_EVIDENCE:
```

## Правила ROOT_FINDING_ID

Если пользователь явно передал ID, сохрани его.

Если ID отсутствует, присвой:

```text
ROOT-001
```

Не используй случайный ID.

Не создавай новый ID при повторном запуске для того же явно переданного root case.

Если команда не может определить, является ли это продолжением существующего root case, используй:

```text
ROOT_FINDING_ID: ROOT-001
ID_STATUS: provisional
```

## Правила CONFIRMED_VERDICT

Разрешённые значения:

```text
fix_now
false_positive
needs_entrypoint_map
needs_openspec_update
plan_only
unconfirmed
unknown
```

Используй подтверждённое значение только если:

* оно явно передано пользователем;
* оно содержится в явном output `/opsx-fix-bug`;
* или прямое repository evidence позволяет воспроизвести тот же verdict без изменения scope.

Если есть только сырой Bugbot finding:

```text
CONFIRMED_VERDICT: unconfirmed
```

Не повышай его до `fix_now`.

## Правила CLASSIFICATION

Сохраняй ранее полученный classification vocabulary.

Примеры:

```text
implementation_bug
spec_bug
implementation_bug_with_spec_gap
false_positive
unknown
unclassified
```

Если `/opsx-classify-bug` ещё не запускался и classification не передан:

```text
CLASSIFICATION: unclassified
```

Не угадывай classification из одного Bugbot claim.

## Правила RUNTIME_PATH

Используй точный chain, если он подтверждён:

```text
entrypoint
→ manager
→ service
→ causal boundary
→ write boundary
```

Если путь только предполагаемый:

```text
RUNTIME_PATH:
candidate: ...
evidence_status: unconfirmed
```

Не смешивай proven и candidate path без маркировки.

## Правила CAUSAL_BOUNDARY

`CAUSAL_BOUNDARY` должен описывать ошибочный механизм, а не только имя файла:

* неправильный gate;
* отсутствующий filter;
* early return;
* неверная state transition;
* неверная retry condition;
* bypass adapter;
* stale-state interpretation;
* callback routing;
* missing idempotency check.

Если механизм не подтверждён:

```text
CAUSAL_BOUNDARY: unknown
```

и перечисли required evidence.

## Правила WRITE_BOUNDARY

Назови фактическую observable boundary:

* external API write;
* PostgreSQL write;
* Redis mutation;
* ClickHouse insert;
* Telegram send или edit;
* lifecycle transition;
* scheduler enqueue;
* billing operation.

Если boundary только предполагается, явно пометь это.

## Правила PRE_FIX_REF

`PRE_FIX_REF` должен быть:

* branch;
* commit SHA;
* worktree ref;
* stash-aware clean snapshot description;
* или `unknown`.

Не выдумывай commit SHA.

Если fix находится в stash, но точный stash ref не передан:

```text
PRE_FIX_REF:
current clean HEAD before root fix stash restoration

PRE_FIX_REF_STATUS:
needs_exact_git_ref
```

`base/head` не доказывают автоматически, что `head` является pre-fix snapshot.

## Root finding completeness

Установи:

```text
ROOT_PACKET_STATUS:
- ready
- provisional
- incomplete
- not_applicable
```

`ready`:

* все обязательные поля надёжно заполнены.

`provisional`:

* packet пригоден для read-only hunt;
* uncertain evidence явно маркирована.

`incomplete`:

* bug-hunt не сможет надёжно сопоставить известный root.

`not_applicable`:

* конкретного bug report нет.

# Handoff target

Определи `target`:

* `target=bug-hunt` — нужен поиск других bypasses того же invariant.
* `target=fix-bug` — есть конкретный bug report для adjudication или fix planning.
* `target=both` — требуются оба handoff.

Если `target` не указан:

* при конкретном unconfirmed bug report используй `fix-bug`;
* при confirmed root bug и запросе на соседние нарушения используй `bug-hunt`;
* при change или diff без конкретного bug report используй обычный invariant-based bug-hunt, но не выдавай root-aware handoff без root packet;
* при явном запросе «и hunt, и fix» используй `both`.

# Root-aware bug-hunt handoff eligibility

Готовый root-aware `/opsx-bug-hunt` handoff разрешён, когда:

```text
ROOT_PACKET_STATUS=ready
```

или:

```text
ROOT_PACKET_STATUS=provisional
```

при условии, что uncertain поля явно маркированы.

Если:

```text
ROOT_PACKET_STATUS=incomplete
```

не выдавай готовую root-aware command.

Верни:

```text
Recommended next step:
- сначала /opsx-fix-bug без GO или targeted evidence extraction;
- затем повторить /opsx-invariant.
```

# Handoff в /opsx-bug-hunt

Root-aware handoff должен содержать:

* `base`;
* `head`;
* `invariant`;
* полный `root_finding`;
* `scope`;
* `deep`, если justified;
* expected boundary types;
* stop condition.

Формат:

```text
/opsx-bug-hunt
base=<base>
head=<head>
invariant="<primary invariant statement>"
root_finding="
ROOT_FINDING_PACKET:
  ROOT_FINDING_ID: ...
  TITLE: ...
  LITERAL_CLAIM: ...
  CONFIRMED_VERDICT: ...
  CLASSIFICATION: ...
  RUNTIME_PATH: ...
  CAUSAL_BOUNDARY: ...
  WRITE_BOUNDARY: ...
  INVARIANT: ...
  PRE_FIX_REF: ...
"
scope="<scope>"
deep
expected_boundaries="<boundaries>"
stop="known root reconfirmed or not reproduced | no new invariant bypass found | new child finding | needs_entrypoint_map | snapshot uncertainty"
```

Копируй packet без смыслового изменения.

Не сокращай root packet до title.

Не передавай только invariant вместо root packet.

`TEST_COVERAGE_PACKET` может быть приложен как дополнительный context, но его отсутствие или provisional status не блокируют этот handoff.

# Handoff в /opsx-fix-bug

Handoff должен содержать:

* bug report;
* named invariant;
* known или expected write boundary;
* scope;
* forbidden files/actions, если известны;
* indication, подтверждён finding или остаётся гипотезой;
* требование проверить reachability;
* `ROOT_FINDING_ID`, если материализован.

Не добавляй `GO`.

Формат:

```text
/opsx-fix-bug
root_finding_id="<id>"
bug="<bug report>"
invariant="<primary invariant statement>"
scope="<scope>"
write_boundary="<known or expected boundary>"
evidence_status="<confirmed | unconfirmed | partial>"
```

# Специальное правило: A/B Hold

Для:

* `card-ab-hold`;
* `PENDING_SETUP`;
* `ACTIVE`;
* `setup`;
* `hold`;
* `freeze`;
* `structural`;
* `whitelist`;
* `blacklist`;
* `bid`;
* `keyword`;
* `ACT`;

обязательно проверь наличие:

* protected states;
* allowed state `OFF`, если применимо;
* runtime tick или scheduler;
* candidate/filter boundary;
* handler/write boundary;
* blocked behavior scenario;
* allowed sibling behavior scenario;
* residual или repeated tick scenario, если применимо;
* warning, что sibling pattern не доказывает reachability текущего path.

# Специальное правило: paid/free boundary

Раздели:

* free-visible UI;
* paid automation;
* allowed manual или self-service behavior;
* forbidden paid-core execution;
* Telegram callback boundary;
* service call boundary;
* DB, billing или subscription gate;
* tests для free и paid paths.

# Специальное правило: campaign state

Раздели:

* source state;
* target state;
* trigger или event;
* allowed transitions;
* forbidden transitions;
* idempotency;
* stale stats behavior;
* retries и repeated ticks;
* write boundaries;
* terminal state behavior;
* residual state behavior.

Обязательно рассмотри repeated invocation и crash/restart window для `TEST_COVERAGE_PACKET`.

# Output contract

Выдай результат точно в следующей структуре:

````text
Статус:
- ready / needs_input / ambiguous / blocked

Источник invariant:
- change:
- desc:
- bug:
- classification input:
- verdict input:
- base/head:
- scope:
- target:

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
- transition boundaries:
- data boundaries:
- feature flags / modes / enums:
- related tests:
- weak tests to avoid:
- evidence needed:
- severity if violated:

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
  - transition:
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

ROOT_FINDING_PACKET:
- ROOT_FINDING_ID:
- ID_STATUS:
- TITLE:
- LITERAL_CLAIM:
- CONFIRMED_VERDICT:
- CLASSIFICATION:
- RUNTIME_PATH:
- CAUSAL_BOUNDARY:
- WRITE_BOUNDARY:
- INVARIANT:
- PRE_FIX_REF:
- PRE_FIX_REF_STATUS:
- OWNER_MODULE:
- REPORTED_SEVERITY:
- ACCEPTED_SEVERITY:
- REGRESSION_SCENARIO:
- KNOWN_FIX_BOUNDARY:
- ROOT_FIX_STATUS:
- EVIDENCE_STATUS:
- MISSING_EVIDENCE:
- ROOT_PACKET_STATUS:

TEST_COVERAGE_PACKET:
- TEST_COVERAGE_STATUS:
- SOURCE_REQUIREMENTS:
- INVARIANT:
- PRODUCTION_ENTRYPOINTS:
- ORCHESTRATION_SEAMS:
- PROTECTED_BOUNDARIES:
- REQUIRED_BEHAVIORAL_SCENARIOS:
- REQUIRED_ALLOWED_SIBLING_SCENARIOS:
- REQUIRED_RESIDUAL_OR_REPEATED_INVOCATION_SCENARIOS:
- REQUIRED_FAILURE_OR_EMPTY_STATE_SCENARIOS:
- REALITY_CONSTRAINTS:
- MOCKING_CONSTRAINTS:
- MINIMUM_TEST_LEVEL:
- UNIT_SUFFICIENCY:
- EXISTING_TESTS_TO_INSPECT:
- COVERAGE_GAPS:
- WEAK_TEST_PATTERNS:
- EVIDENCE_STATUS:
- MISSING_EVIDENCE:

Reachability hints:
- expected runtime entrypoints:
- scheduler/job/bot/API source:
- manager methods to inspect:
- service/helper paths to inspect:
- tests/inventory to inspect:
- paths probably dead or tests-only:
- evidence warnings:

Handoff to /opsx-bug-hunt:
```text
<ready command, blocked explanation, or not_applicable>
````

Handoff to /opsx-fix-bug:

```text
<ready command, template, or not_applicable>
```

Stop conditions:

* ...

Recommended next step:

1. ...
2. ...

````

# Bug-team handback (when case= present)

Authority: `.cursor/pipeline/contracts/bug-episode/CLOSE_POLICY.md`.

Invariant is a **fork**, not a human menu to run hunt/close alone by default.
When `case=<CASE_ID>` is known (or ROOT packet ties to a durable case), the
**Recommended next step** MUST lead with pasteable team handback (no silent
return):

```text
/opsx-bug-team case=<CASE_ID> mode=resume-family-fanout
```

ALSO_OK (solo walk / advisory, not a violation): `/opsx-bug-hunt …` only if
Owner explicitly wants solo hunt; `/opsx-fix-bug …` without GO if still
adjudicating. Prefer team handback over asking the human to choose among
hunt / close / learn.

Если конкретного bug report нет, верни:

```text
ROOT_FINDING_PACKET:
- ROOT_PACKET_STATUS: not_applicable
````

Не заполняй root fields выдуманными значениями.

Если test mapping неприменим или не может быть надёжно материализован, верни:

```text
TEST_COVERAGE_PACKET:
- TEST_COVERAGE_STATUS: not_materialized
- MISSING_EVIDENCE:
  - ...
```

Это не должно удалять или менять остальные output sections.

# Специальное правило: готовый bug-hunt handoff

Если `target` включает `bug-hunt`, проверь:

* invariant materialized;
* root packet materialized;
* root ID stable;
* literal claim preserved;
* verdict evidence status explicit;
* classification explicit;
* runtime path explicit или marked candidate;
* causal boundary explicit или marked unknown;
* write boundary explicit;
* pre-fix ref explicit или marked unknown;
* root packet copied into handoff.

Если обязательное поле отсутствует без явной маркировки:

```text
ROOT_PACKET_STATUS: incomplete
```

и готовый root-aware handoff запрещён.

# Специальное правило: test coverage compatibility

Перед формированием `TEST_COVERAGE_PACKET`:

* не изменяй invariant ради удобства тестирования;
* не меняй `ROOT_FINDING_PACKET`;
* не меняй прежний `Статус`, если invariant contract уже готов;
* не блокируй bug-hunt или fix-bug handoff только из-за неполного test mapping;
* не создавай test files;
* не выдавай test implementation plan;
* не объявляй unit test достаточным без проверки causal path и real data shape;
* не требуй integration или E2E без boundary-based причины;
* не считай green tests доказательством production wiring или полного spec conformity.

# Review checklist

Перед финалом проверь:

* invariant не является patch instruction;
* protected и allowed cases присутствуют;
* forbidden behavior наблюдаемо;
* boundary названа;
* base/head не выдуманы;
* scope не расширен без причины;
* raw bug report не объявлен confirmed без evidence;
* verdict не выдуман;
* classification не выдуман;
* root packet отделён от invariant packet;
* test coverage packet отделён от root и reachability packets;
* конкретные данные текущего бага не захардкожены;
* root packet передан в `/opsx-bug-hunt`;
* `/opsx-fix-bug` не получает `GO`;
* stash не изменяется;
* implementation не запускается;
* при недостатке invariant evidence команда останавливается;
* `TEST_COVERAGE_PACKET` добавлен только как additive output;
* прежние verdict, required inputs и handoff eligibility не изменены;
* неполный test mapping не блокирует прежний ready status;
* test scenarios сформулированы behavioral terms;
* reality constraints запрещают synthetic model fields и invented states;
* causal boundary не скрыта полным mock, если она проверяется;
* residual и repeated invocation рассмотрены для lifecycle и retry invariant;
* minimum test level выбран boundary-based;
* нет blanket E2E requirement;
* наличие похожего test name не объявлено доказанным coverage.


## Downstream hunt bounds (light)

When handing off to `/opsx-bug-hunt`, note episode bounds:

```text
MAX_HUNT_PASSES=3
MAX_DEPTH_FROM_ROOT=3
MAX_ACTIVE_BRANCHES=3
PASS_3=MANDATORY_STOP
NEW_INVARIANT_FROM_BRANCH=FORBIDDEN
```

Do not invent production GO. RED/GREEN path remains
`/opsx-test` → Owner GO → `/opsx-fix-bug GO` after companions activate.

