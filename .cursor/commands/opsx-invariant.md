---

description: "Сформировать именованный behavioral invariant и, при наличии конкретного bug report, материализовать ROOT_FINDING_PACKET для передачи в root-aware /opsx-bug-hunt или /opsx-fix-bug."
argument-hint: "change=<id> OR desc=<описание> OR bug=<bug-report> [classification=<value>] [verdict=<value>] [base=<branch>] [head=<branch>] [scope=<paths>] [target=bug-hunt|fix-bug|both]"
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# /opsx-invariant

Используй эту команду, когда перед `/opsx-bug-hunt` или `/opsx-fix-bug` нужен точный behavioral invariant.

Команда должна:

1. превратить размытое описание, OpenSpec change, diff или bug report в проверяемый invariant;
2. определить protected states, allowed behavior, forbidden behavior и runtime boundaries;
3. подготовить handoff для следующей команды;
4. при наличии конкретного bug report материализовать отдельный `ROOT_FINDING_PACKET`;
5. передать `ROOT_FINDING_PACKET` в root-aware `/opsx-bug-hunt`.

Команда не исправляет код.

Команда не подтверждает баг без evidence.

Команда не должна подменять:

* `/opsx-fix-bug`;
* `/opsx-classify-bug`;
* `/opsx-bug-hunt`;
* `/opsx-learn-from-bug`.

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
* «нужно надёжно отличить root bug от child findings».

## Важное разделение ролей

Эта команда НЕ должна:

* исправлять production code;
* исправлять tests;
* изменять OpenSpec artifacts;
* изменять Cursor commands;
* делать stage, commit или push;
* запускать deploy, restart или migrations;
* создавать Git branch или worktree;
* восстанавливать, применять, удалять или изменять Git stash;
* превращаться в общий diff review;
* подтверждать production reachability без evidence;
* объявлять сырой Bugbot finding подтверждённым багом;
* запускать bug hunt;
* запускать learning.

Эта команда должна:

1. собрать входные данные;
2. прочитать релевантные OpenSpec artifacts;
3. прочитать diff и runtime boundaries, если они доступны;
4. извлечь или предложить invariant;
5. уточнить недостающие границы;
6. развернуть invariant в проверяемый packet;
7. при наличии конкретного root bug сформировать `ROOT_FINDING_PACKET`;
8. выдать готовый handoff для `/opsx-bug-hunt` и/или `/opsx-fix-bug`.

## Read-only режим

Команда всегда read-only.

Разрешено:

* читать repository;
* читать OpenSpec artifacts;
* читать diff;
* искать runtime entrypoints;
* искать write, mutation, transition и data boundaries;
* искать tests;
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
* `desc`: пользовательское описание ожидаемого поведения.
* `bug`: конкретный bug report, Bugbot finding, CI finding или manual finding.
* `classification`: ранее полученная классификация, если она явно передана.
* `verdict`: ранее полученный literal verdict, если он явно передан.
* `base`: branch или commit для сравнения.
* `head`: branch или commit для анализа.
* `scope`: paths или modules, ограничивающие анализ.
* `target`: `bug-hunt`, `fix-bug` или `both`.

Не используй distant chat history как единственное evidence для:

* `verdict`;
* `classification`;
* `runtime_path`;
* `confirmed production reachability`;
* `pre_fix_ref`.

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

## Reachability hints

Если invariant связан с:

* background jobs;
* campaign state;
* WB writes;
* Redis, PostgreSQL или ClickHouse;
* Telegram callbacks;
* paid/free boundary;
* scheduler retries;
* lifecycle transitions;

добавь:

```text
Reachability hints:
- expected runtime entrypoints:
- scheduler/job/bot/API source:
- manager methods to inspect:
- service/helper paths to inspect:
- tests/inventory to inspect:
- paths probably dead or tests-only:
```

Не утверждай reachability без evidence.

Для handoff указывай:

* proven runtime paths как proven;
* candidate runtime paths как candidates;
* missing evidence как missing.

## Root finding materialization

Если на входе есть конкретный `bug`, команда должна попытаться сформировать отдельный:

```text
ROOT_FINDING_PACKET
```

Invariant и root finding — разные сущности.

`INVARIANT_PACKET` описывает общее правило.

`ROOT_FINDING_PACKET` описывает конкретный уже известный или предполагаемый способ нарушения этого правила.

### Обязательные поля ROOT_FINDING_PACKET

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

### Дополнительные поля

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

Используй `fix_now`, `false_positive`, `needs_entrypoint_map`, `needs_openspec_update` или `plan_only` только если:

* значение явно передано пользователем;
* оно содержится в явном output `/opsx-fix-bug`;
* или прямое repository evidence позволяет воспроизвести тот же verdict без изменения scope.

Если есть только сырой Bugbot finding:

```text
CONFIRMED_VERDICT: unconfirmed
```

Не повышай его до `fix_now`.

## Правила CLASSIFICATION

Разрешённые значения должны сохранять ранее полученный classification vocabulary.

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

Не смешивай proven и candidate path в одну строку без маркировки.

## Правила CAUSAL_BOUNDARY

`CAUSAL_BOUNDARY` должен описывать не просто файл, а ошибочный механизм:

* неправильный gate;
* отсутствующий filter;
* early return;
* неверная state transition;
* неверная retry condition;
* bypass adapter;
* stale-state interpretation;
* callback routing;
* missing idempotency check.

Пример:

```text
process_ab_epoch treats phase=WB_SYNC as in-flight while ignoring sync_status=complete.
```

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
* Telegram send/edit;
* lifecycle transition;
* scheduler enqueue;
* billing operation.

Если boundary только предполагается, пометь это.

## Правила PRE_FIX_REF

`PRE_FIX_REF` должен быть:

* branch;
* commit SHA;
* worktree ref;
* stash-aware clean snapshot description;
* или `unknown`.

Не выдумывай commit SHA.

Если fix уже находится в stash, но точный stash ref не передан:

```text
PRE_FIX_REF:
current clean HEAD before root fix stash restoration

PRE_FIX_REF_STATUS:
needs_exact_git_ref
```

Если `base/head` заданы, это не автоматически означает, что `head` является pre-fix snapshot.

## Root finding completeness

Установи:

```text
ROOT_PACKET_STATUS:
- ready
- provisional
- incomplete
- not_applicable
```

`ready` — все обязательные поля надёжно заполнены.

`provisional` — packet пригоден для read-only hunt, но часть evidence маркирована как unconfirmed.

`incomplete` — bug-hunt не сможет надёжно сопоставить известный root.

`not_applicable` — конкретного bug report нет, invariant создаётся только по change или desc.

## Handoff target

Определи `target`:

* `target=bug-hunt` — нужен поиск других bypasses того же invariant.
* `target=fix-bug` — есть конкретный bug report для adjudication или fix planning.
* `target=both` — требуются оба handoff.

Если `target` не указан:

* при конкретном unconfirmed bug report используй `fix-bug`;
* при confirmed root bug и запросе на поиск соседних нарушений используй `bug-hunt`;
* при change/diff без конкретного bug report используй `bug-hunt`, но без root-aware handoff;
* при явном запросе «и hunt, и fix» используй `both`.

## Root-aware bug-hunt handoff eligibility

Готовый root-aware `/opsx-bug-hunt` handoff разрешён только когда:

```text
ROOT_PACKET_STATUS=ready
```

или:

```text
ROOT_PACKET_STATUS=provisional
```

при условии, что все uncertain поля явно маркированы и command не выдаёт их как confirmed facts.

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

## Handoff в /opsx-bug-hunt

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

Не сокращай root packet до одного title.

Не передавай только invariant вместо root packet.

## Handoff в /opsx-fix-bug

Handoff должен содержать:

* bug report;
* named invariant;
* known или expected write boundary;
* scope;
* forbidden files/actions, если известны;
* указание, подтверждён finding или остаётся гипотезой;
* требование проверить reachability;
* `ROOT_FINDING_ID`, если он материализован.

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

## Специальное правило: если invariant про A/B Hold

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
* blocked behavior test;
* allowed behavior test;
* warning, что sibling pattern не доказывает reachability текущего path.

## Специальное правило: paid/free boundary

Раздели:

* free-visible UI;
* paid automation;
* allowed manual or self-service behavior;
* forbidden paid-core execution;
* Telegram callback boundary;
* service call boundary;
* DB, billing или subscription gate;
* tests для free и paid paths.

## Специальное правило: campaign state

Раздели:

* source state;
* target state;
* trigger/event;
* allowed transitions;
* forbidden transitions;
* idempotency;
* stale stats behavior;
* retries и repeated ticks;
* write boundaries;
* terminal state behavior;
* residual state behavior.

## Output contract

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

Если конкретного bug report нет, верни:

```text
ROOT_FINDING_PACKET:
- ROOT_PACKET_STATUS: not_applicable
````

Не заполняй root fields выдуманными значениями.

## Специальное правило: готовый bug-hunt handoff

Если `target` включает `bug-hunt`, команда должна проверить:

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

Если хотя бы одно обязательное поле отсутствует без явной маркировки:

```text
ROOT_PACKET_STATUS: incomplete
```

и готовый root-aware handoff запрещён.

## Review checklist

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
* конкретные данные текущего бага не захардкожены в command contract;
* root packet передан в `/opsx-bug-hunt`;
* `/opsx-fix-bug` не получает `GO`;
* stash не изменяется;
* implementation не запускается;
* при недостатке данных команда останавливается.
