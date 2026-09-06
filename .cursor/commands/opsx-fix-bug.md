---
description: "Разобрать и, только если безопасно, исправить баг-репорт через reachability, invariant, write-boundary и regression-test gates."
argument-hint: "[case=<CASE_ID>] [intake=<INTAKE_ID>] [finding=<FINDING_ID>] [claim_token=<TOKEN>] [GO] [bug report / Bugbot verdict / CI failure / manual finding]"
---

# /opsx-fix-bug

Используй эту команду для разбора и исправления конкретного баг-репорта от Bugbot, Cursor, Codex, CI, ручного ревью, логов или наблюдения пользователя.

Баг-репорт — это гипотеза, а не инструкция к фиксу.

Перед любыми изменениями production-кода или tests команда обязана проверить достижимость runtime-пути, владельца инварианта, write-boundary impact и качество regression-теста.

Перед глубоким анализом сырой bug signal обязан быть на диске в durable case map: либо через переданные `case`/`intake`, либо через same-chat resume из prior `COMMAND_RECEIPT`, либо (только first-run без resume) через `/opsx-materialize-bug-queue mode=intake`. Follow-up `GO` без IDs не создаёт новый case.

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
claim_token=
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

## Claim ownership gate (mandatory)

Ownership, закреплённый `/opsx-claim-next-bug`, обязан проверяться здесь.
Парсинг `claim_token=` **недостаточен**: токен сравнивается с durable `CLAIM_TOKEN`.

### Когда gate обязателен

Если передан `finding=<FINDING_ID>` (включая resume, где `FINDING_ID`
взят из same-chat prior `COMMAND_RECEIPT`):

1. Прочитай exact path
   `.opsx/runs/bug-cases/<CASE_ID>/findings/<FINDING_ID>.md`
   (при необходимости сверка строки в `LEDGER.md` того же case).
2. **Duplicate-root refuse (before claim-first):** если выполняется любое из:
   - `FINDING_ID` с префиксом `DUP-*`;
   - durable `RELATION_TO_ROOT` / class = `duplicate_root`;
   - `STATUS: duplicate_root_observation`;
   — hard stop `blocked_finding_status_not_actionable` до forensics /
   `mode=update` / `GO`, **даже если** ошибочно
   `STATUS: available` ∧ `CHAT_REQUIRED: true`.
   Не направляй на `/opsx-claim-next-bug`. Pasteable next: `none`.
   Не invent `CLAIM_TOKEN`. Это зеркало claim-next ineligible для
   same-causal-path duplicates (не claim-first петля).
3. **Claim-first (queue):** если `CHAT_REQUIRED: true` **и**
   `STATUS: available` **и** п.2 не сработал — hard stop
   `blocked_needs_claim_first`
   до forensics / `mode=update` / `GO`. Не invent и не пиши
   `CLAIM_TOKEN` из `/opsx-fix-bug`. Pasteable next **только**:
   `/opsx-claim-next-bug case=<CASE_ID> chat_label="<label>"`
   (без «retry с `claim_token=`» — токена ещё нет).
   Не применяй этот blocker к другим non-claimed статусам
   (`blocked`, `backlog`, `absorbed_*`, `closed_*`, `promoted_*`,
   `duplicate_root_observation`, intermediate post-claim, …) — для них п.4
   (`blocked_finding_status_not_actionable`), не claim-first петля.
4. **Status refusal (non-actionable):** если `STATUS` ∈
   `{backlog, blocked, absorbed_by_parent_fix, closed_false_positive,
   closed_fixed, promoted_to_root_case, duplicate_ancestor,
   duplicate_root_observation,
   adjudicating, ready_for_fix, implementing, verification}` или иное
   `absorbed_*` — hard stop `blocked_finding_status_not_actionable`
   до forensics / `mode=update` / `GO`, **независимо** от
   `CHAT_REQUIRED` (в т.ч. при `CHAT_REQUIRED: true` — без
   fall-through; при `CHAT_REQUIRED: false` — **не** п.6 optional).
   Не направляй на `/opsx-claim-next-bug` (ineligible).
   Pasteable next: `none` (или читать
   `.opsx/runs/bug-cases/<CASE_ID>/` INDEX / ledger; не claim).
   Aligns with claim-next ineligible / materialize terminal writes
   (`promoted_to_root_case`, `duplicate_ancestor`,
   `duplicate_root_observation`, closed FP, …).
5. Если у finding `STATUS: claimed` — token gate **всегда** обязателен
   (пустой durable `CLAIM_TOKEN` **не** ослабляет ownership):
   - если durable `CLAIM_TOKEN` пуст / absent → hard stop
     `blocked_claimed_without_durable_token` (corrupt claim state);
     не invent token; не продолжай adjudication / `mode=update` / `GO`;
   - иначе (durable `CLAIM_TOKEN` непустой) предоставленный token
     обязан быть ровно одним из:
     - `claim_token=<TOKEN>` в текущем вводе пользователя;
     - non-empty `CLAIM_TOKEN` в same-chat prior `COMMAND_RECEIPT`
       (тот же finding/case), когда текущий ввод — resume того же
       сигнала и ввод не содержит другого `claim_token=`;
   - приоритет: если во вводе есть `claim_token=`, используй его;
     иначе — `CLAIM_TOKEN` из prior receipt;
   - `<TOKEN>` обязан **точно** совпасть с durable `CLAIM_TOKEN`
     finding/ledger (без нормализации, без «похоже», без угадывания);
   - только после match продолжай adjudication / `mode=update` / `GO`;
   - после успешного match echo matched token в исходящий
     `COMMAND_RECEIPT.CLAIM_TOKEN` (см. schema ниже).
6. Если `STATUS` **не** `claimed`, **не** из п.4
   (backlog / blocked / absorbed_* / closed_* / promoted /
   duplicate_ancestor / duplicate_root_observation / adjudicating /
   ready_for_fix / implementing / verification), **не** класс п.2
   (`DUP-*` / `duplicate_root`), **и** (`CHAT_REQUIRED` =
   `false` / отсутствует) — `claim_token` опционален (legacy raw
   report / known-root / unclaimed non-queue finding); исходящий
   receipt `CLAIM_TOKEN` оставляй пустым. `STATUS: claimed` + пустой
   durable token **никогда** не попадает сюда (см. п.5 /
   `blocked_claimed_without_durable_token`). Статусы п.4 и класс п.2
   **никогда** не попадают сюда (см. `blocked_finding_status_not_actionable`).

### Blockers (hard stop)

| Условие | Blocker |
|---|---|
| `finding=` + (`FINDING_ID` `DUP-*` / relation\|class `duplicate_root` / `STATUS: duplicate_root_observation`) — любой `STATUS`/`CHAT_REQUIRED`, в т.ч. wrongly `available`+`true` | `blocked_finding_status_not_actionable` |
| `finding=` + `CHAT_REQUIRED: true` + `STATUS: available` (ещё не claimed) **и** не класс п.2 | `blocked_needs_claim_first` |
| `finding=` + `STATUS` ∈ {`backlog`, `blocked`, `absorbed_by_parent_fix`} / `absorbed_*` / `closed_false_positive` / `closed_fixed` / `promoted_to_root_case` / `duplicate_ancestor` / `duplicate_root_observation` / `adjudicating` / `ready_for_fix` / `implementing` / `verification` (любой `CHAT_REQUIRED`) | `blocked_finding_status_not_actionable` |
| `finding=` claimed + durable `CLAIM_TOKEN` пуст / absent | `blocked_claimed_without_durable_token` |
| `finding=` claimed + non-empty durable `CLAIM_TOKEN`, но нет `claim_token=` во вводе **и** нет usable non-empty `CLAIM_TOKEN` в same-chat prior `COMMAND_RECEIPT` | `blocked_missing_claim_token` |
| предоставленный token (ввод или prior receipt) не равен durable `CLAIM_TOKEN` | `blocked_claim_token_mismatch` |
| передан `claim_token=` во вводе, но нет `finding=` (и resume не восстановил `FINDING_ID`) | `blocked_claim_token_without_finding` |
| `finding=` claimed, а предоставленный token от другого finding/case | `blocked_claim_token_mismatch` |

При любом blocker из таблицы:

* не начинай forensics / adjudication по чужому claim / pre-claim queue finding;
* не делай `mode=update` по этому finding;
* не применяй production/`GO` edits;
* верни `Вердикт: blocked`, `RESULT: blocked` в `COMMAND_RECEIPT`,
  укажи `FINDING_ID` и ожидаемый owner path;
* pasteable next:
  - `blocked_needs_claim_first` → **только**
    `/opsx-claim-next-bug case=<CASE_ID> chat_label="<label>"`
    (не предлагай retry `/opsx-fix-bug` с `claim_token=`);
  - `blocked_needs_classify_first` → **только**
    `/opsx-classify-bug case=<CASE_ID> finding=<FINDING_ID>`;
  - `blocked_finding_status_not_actionable` → **`none`**
    (не `/opsx-claim-next-bug` — статус/класс ineligible; опционально
    указать path case INDEX/ledger);
  - `blocked_claimed_without_durable_token` → **только** materialize
    repair (не `/opsx-claim-next-bug` — claim-next не mint/repair empty
    durable token на already-claimed):
    `/opsx-materialize-bug-queue mode=update case=<CASE_ID> finding=<FINDING_ID> repair=mint_missing_claim_token`
    (если `OWNER_CHAT` задан); иначе
    `/opsx-materialize-bug-queue mode=update case=<CASE_ID> finding=<FINDING_ID> repair=release_corrupt_claim`
    затем `/opsx-claim-next-bug …`. Не invent `CLAIM_TOKEN` в fix-bug;
    не предлагай retry с угаданным token;
  - token blockers (`blocked_missing_claim_token` /
    `blocked_claim_token_mismatch` / `blocked_claim_token_without_finding`) →
    `/opsx-claim-next-bug case=<CASE_ID> chat_label="<label>"`
    либо повтор `/opsx-fix-bug` с корректным `claim_token=` из claim packet.

### Запреты

* Не принимать adjudication/update по `finding=` со статусом
  `available` и `CHAT_REQUIRED: true` без предварительного
  `/opsx-claim-next-bug` (обход claim-first запрещён), **кроме**
  класса п.2 (`DUP-*` / `duplicate_root` / `duplicate_root_observation`) —
  для него только `blocked_finding_status_not_actionable`, не claim-next.
* Не принимать adjudication/update по `finding=` со статусом
  `backlog` / `blocked` / `absorbed_*` / `closed_false_positive` /
  `closed_fixed` / `promoted_to_root_case` / `duplicate_ancestor` /
  `duplicate_root_observation` /
  `adjudicating` / `ready_for_fix` / `implementing` / `verification`
  (в т.ч. при `CHAT_REQUIRED: true` **или** false) — только
  `blocked_finding_status_not_actionable`, без fall-through и без п.6.
* Не принимать adjudication/update по `FINDING_ID` `DUP-*` или
  relation/class `duplicate_root` (любой STATUS) — только
  `blocked_finding_status_not_actionable`.
* Не принимать adjudication/update по `finding=` со статусом `claimed`,
  обходя token (в том числе «я тот же чат» **без** `CLAIM_TOKEN` в
  prior receipt, «токен потерян», «достаточно case+finding»).
* Не подставлять / invent / писать `CLAIM_TOKEN` из `OWNER_CHAT`,
  timestamp, filename или из `/opsx-fix-bug`. Same-chat prior
  `COMMAND_RECEIPT.CLAIM_TOKEN` допустим только как echo ранее matched
  token, не как источник угадывания.
* Не считать handoff `/opsx-claim-next-bug` выполненным ownership proof
  без повторной сверки durable token в этом запуске.
* Не применять `blocked_needs_claim_first` к non-available статусам
  (`blocked`, `backlog`, `absorbed_*`, `closed_*`, `promoted_*`,
  `duplicate_root_observation`, …) и к классу п.2 —
  claim-next их не возьмёт; для них — `blocked_finding_status_not_actionable`.



## Route reconciliation gate

Authority: ORCHESTRATION_MVP section 0.5-0.7 + ROUTE_TRACE.md.

Before adjudication that assumes an implementation route, and always before
production GO:

1. Read EXPECTED_EXECUTION_ROUTE / ACTUAL_EXECUTION_ROUTE /
   ROUTE_RECONCILIATION from LEDGER ## ROUTE_STATE (or last ROUTE-TRACE).
2. On this command start as executor, set
   ACTUAL_EXECUTION_ROUTE=/opsx-fix-bug and compute MATCH or MISMATCH.
3. If MISMATCH -> hard stop blocked_route_mismatch
   (BLOCKED_ROUTE_MISMATCH); no production GO; pasteable next: Owner
   route decision / evidence correction -- not silent continue.
4. If EXPECTED is /opsx-apply -> do not execute fix-bug as production
   executor; route to apply (or Owner correction).
5. Append ROUTE-TRACE with full v2 identity fields + reconciliation.
6. Episode close forbidden while RECONCILIATION is PENDING or MISMATCH.

## Classify-first gate (mandatory)

Authority: `.cursor/pipeline/ORCHESTRATION_MVP.md` §0.1.

After Claim ownership gate passes (or when claim is not required), and before
forensics / `mode=update` / production `GO` that selects an implementation
route:

1. Read `LEDGER.md` → `## ROUTE_STATE` → `CURRENT_CLASSIFICATION`.
2. If absent/empty for this finding/case → hard stop
   `blocked_needs_classify_first`.
3. Pasteable next **only**:

```text
/opsx-classify-bug case=<CASE_ID> finding=<FINDING_ID>
```

4. If `CURRENT_CLASSIFICATION` is `SPEC_BUG` | `SPEC_GAP` and
   `TASK_DELTA` not yet recorded → do not adjudicate as pure implementation;
   pasteable next `/opsx-update <change-id> …` (or continue update) unless
   Owner already completed update and TASK_DELTA says `/opsx-fix-bug`.
5. If `FALSE_POSITIVE` | `OUT_OF_SCOPE` → do not open production path;
   align with classification terminal.

Exceptions (classify not required):

* Claim ownership blockers already returned (claim-first / status / token);
* Duplicate-root / non-actionable status refusal;
* Type-check routing to `/opsx-fix-types`.

Append one ROUTE-TRACE event for each `/opsx-fix-bug` hop (adjudication
and/or GO apply). Update `## ROUTE_STATE` `LAST_COMMAND` / `NEXT_ACTION`.

## Разрешение на запись

### Orchestration companion markers

```text
IMPLEMENTATION_STATUS: LIVE_ACTIVATED
VALIDATION_STATUS: INDEPENDENT_TEST_PASS
RUNTIME_ENFORCEMENT: ACTIVE
LIVE_COMMAND_BEHAVIOR_CHANGED: YES
GO_ACTIVATE: ISSUED
GREEN_WRITER: /opsx-test verify mode
```

Claim ownership gates (`CHAT_REQUIRED`, `CLAIM_TOKEN`, claim-first,
duplicate / absorbed rules) are **unchanged**.

### Production code (Owner GO)

Можно изменять **production code** только если ввод пользователя содержит точный отдельный токен:

```text
GO
```

и итоговый вердикт стал `fix_now`, **и** выполнен RED-before-GO gate ниже.

### Tests — removed from production GO

`GO` **does not** authorize test edits.

* RED authoring / test changes: only `/opsx-test` (bug-regression mode).
* GREEN evidence: only `/opsx-test verify mode`.
* After Owner production GO, `/opsx-fix-bug` may re-run the same pytest
  `TEST_ID` as an **extra check only** — no test mutate, no GREEN write,
  no self-approval of `NON_WEAKEN_DELTA` (Owner only).

### RED-before-GO gate (production)

Production GO is allowed only when all hold:

```text
BUG_CONFIRMED
AND FIX_NOW
AND (
  RED_CONFIRMED
  OR RED_NOT_APPLICABLE_APPROVED
)
```

Durable proof:

* `RED_EVIDENCE_PATH` with `STATUS: RED_CONFIRMED`, or
* Owner-recorded `RED_NOT_APPLICABLE_APPROVED` with exception packet
  (ORCHESTRATION §1.5).

`RED_NOT_APPLICABLE_APPROVED` alone does **not** allow GO without
`BUG_CONFIRMED` and `FIX_NOW`.

If `GO` is present but RED gate fails → hard stop
`blocked_needs_red_before_go` (no production edits). Incomplete exception
packet → `blocked_red_not_applicable_incomplete`.

### Process artifacts без GO

Если `GO` отсутствует, всё равно разрешены записи только process artifacts внутри:

```text
.opsx/runs/bug-cases/**
```

Разрешённые process-writes без `GO`:

* создать raw intake через shared contract `/opsx-materialize-bug-queue mode=intake` **только** после Resume gate, когда prior same-chat receipt отсутствует (истинный first-run);
* обновить case/intake/finding/ledger/INDEX через `/opsx-materialize-bug-queue mode=update`;
* сохранить `SOURCE_INTAKE_ID` и recovery fields.

Запрещено без `GO`:

* изменять production code;
* изменять tests;
* изменять любые другие repo paths вне `.opsx/runs/bug-cases/**`;
* делать stage, commit, push;
* запускать разрушительные команды.

Пользователь не обязан помнить или вручную запускать отдельную materialization-команду перед `/opsx-fix-bug`.

Даже если `GO` есть, не редактируй production-код, пока итоговый вердикт не стал `fix_now` **и** RED-before-GO gate не пройден.

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
.opsx/runs/bug-cases/**
```

Не создавай второй storage layout и не копируй логику записи файлов вне контракта `/opsx-materialize-bug-queue`.

## Source resolution (mandatory)

Следуй `.cursor/commands/opsx-source-resolution.md` до любого широкого repo exploration.
Также следуй `.cursor/commands/opsx-execution-preflight.md` для git/shell ops.

Если переданы `case` / `intake` / `finding` / exact path / receipt `OUTPUT_PATH`:

1. сначала прочитай canonical/exact path;
2. если передан `finding=` — немедленно выполни **Claim ownership gate**
   (claim-first / `blocked_finding_status_not_actionable` /
   claimed-token cells; для `claimed`: пустой durable `CLAIM_TOKEN` →
   `blocked_claimed_without_durable_token`; иначе сверка предоставленного
   token из `claim_token=` или same-chat prior receipt `CLAIM_TOKEN` ↔
   durable `CLAIM_TOKEN`) до forensics и до любых writes;
3. не ищи эти artifacts через `rg` / `find` / glob / Task-explore по всему repo;
4. **не** запускай `git status` / `git branch` до чтения durable source и не делай их обязательными для read-only adjudication без GO;
5. forensics/`rg` разрешены только для **символов кода**, указанных packet'ом после успешного чтения durable source;
6. в output заполни `SOURCE_RESOLUTION` и `EXECUTION_PREFLIGHT`.

Canonical paths:

```text
.opsx/runs/bug-cases/<CASE_ID>/intakes/<INTAKE_ID>.md
.opsx/runs/bug-cases/<CASE_ID>/findings/<FINDING_ID>.md
.opsx/runs/bug-cases/<CASE_ID>/LEDGER.md
.opsx/runs/bug-cases/INDEX.md
```

Если durable source не найден после direct resolution — `blocked_needs_exact_source` / существующий blocker, а не бесконечный search и не hang на git.

### Если `case` и `intake` отсутствуют

Сначала **same-chat receipt resume** (human-first). Не создавай новый case, пока не исключено продолжение уже записанного сигнала.

#### Resume gate (обязателен до `mode=intake`)

1. Если в **этом же чате** уже есть завершённый `COMMAND_RECEIPT` от `/opsx-fix-bug` с непустыми `CASE_ID` и `INTAKE_ID` (и опционально `FINDING_ID` / `CLAIM_TOKEN`), и текущий ввод — продолжение того же сигнала (типично follow-up `GO`, повтор того же report, или «продолжи» без новых IDs):
   - **не** вызывай `/opsx-materialize-bug-queue mode=intake`;
   - продолжай с IDs из этого receipt как будто они были переданы во вводе;
   - при наличии `FINDING_ID` в receipt — применяй **Claim ownership gate**
     (claim-first при `available`+`CHAT_REQUIRED=true`;
     п.4 status refusal →
     `blocked_finding_status_not_actionable`; для `claimed` —
     пустой durable `CLAIM_TOKEN` → `blocked_claimed_without_durable_token`;
     иначе matching `claim_token=` из текущего ввода **или** non-empty
     `CLAIM_TOKEN` из того же prior receipt; см. gate выше).
2. Запрещено угадывать case по «похожему тексту» в `INDEX.md` или по другим чатам. Resume только из explicit IDs во вводе или из prior receipt **этого** чата.
3. Если resume невозможен (нет prior receipt / receipt без IDs):
   - при токене `GO` **и** пустом/отсутствующем новом raw bug payload (типичный follow-up только `GO`) → stop с blocker `blocked_needs_case_intake`;
     не создавай новый case; верни pasteable next из `.opsx/runs/bug-cases/INDEX.md` recovery row или попроси вставить `case=`/`intake=` из предыдущего receipt;
   - при токене `GO` **и** непустом новом raw bug payload без prior receipt (редкий one-shot) → first-run `mode=intake` ниже, затем forensics; это **не** путь для повторного GO по уже adjudicated сигналу;
   - без `GO` (истинный first-run) → создай новый intake через `mode=intake` ниже.

#### First-run (только без resume)

Выполни в одном запуске:

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

Intake обязан быть на диске до глубокого анализа. Не начинай широкий forensics, пока raw intake не записан (через resume existing paths или через first-run `mode=intake`).

### Если `case` и `intake` присутствуют

1. Если также передан `finding=` — сначала **Claim ownership gate**; при blocker остановись.
2. Прочитай durable intake из `.opsx/runs/bug-cases/<CASE_ID>/intakes/<INTAKE_ID>.md`.
3. Используй `RAW_REPORT` / symptom / context из intake как source of truth для сигнала.
4. Выполни read-only adjudication.
5. Выбери ровно один `PERSISTENCE_DECISION` и persist через `mode=update`.
6. Верни output contract и `COMMAND_RECEIPT`.

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

### Если передан `case` + `finding` без `intake`

Приоритетнее ветки «только `case` без `intake`». Типичный handoff от
`/opsx-claim-next-bug`, когда `intake=` опущено или пусто.

1. Выполни **Claim ownership gate** (включая claim-first для
   `available`+`CHAT_REQUIRED=true`; status refusal п.4 →
   `blocked_finding_status_not_actionable`; для `claimed` — всегда
   token gate, включая `blocked_claimed_without_durable_token` при
   пустом durable `CLAIM_TOKEN`). При любом gate blocker — остановись.
2. Прочитай finding packet
   `.opsx/runs/bug-cases/<CASE_ID>/findings/<FINDING_ID>.md`.
3. Разреши intake в этом порядке:
   - non-empty `SOURCE_INTAKE_ID` из finding packet/ledger → используй как
     `intake=` и продолжай как ветка `case` + `intake` + `finding`;
   - иначе non-empty `PRIMARY_INTAKE_ID` из `CASE.md` → то же;
   - иначе **finding-first legacy path**: выполни adjudication по finding
     packet (и `RAW_REPORT`/поля packet); **запрещено** вызывать
     `mode=intake` и создавать новый intake для этого claimed/existing
     finding.
4. Не падай в «только `case` без `intake`» пока есть `finding=`.

### Если передан только `case` или только `intake`

* только `case` без `intake` **и без** `finding=`: используй
  `PRIMARY_INTAKE_ID` из `CASE.md`, если он есть; иначе создай новый
  intake в этом case через `mode=intake`;
* `case` + `finding` без `intake` → см. секцию выше (не создавать
  spurious intake);
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

Тогда **без GO**:

- **не** предлагай `/opsx-fix-bug GO` как следующий шаг;
- pasteable next **must** be:

```text
/opsx-test case=<CASE_ID> finding=<FINDING_ID>
```

- regression test authoring / RED evidence belongs to `/opsx-test`;
- production patch waits for Owner GO after `RED_CONFIRMED`
  (or `RED_NOT_APPLICABLE_APPROVED`).

Тогда **с Owner GO** (после RED gate):

- патчь самую узкую правильную **production** границу;
- **не** редактируй tests;
- предпочитай shared guard/candidate filter вместо локального дублирования;
- optional: re-run same `TEST_ID` as check only;
- GREEN confirmation → `/opsx-test … verify` (this command is not GREEN writer);
- **Never** write `closed_fixed` from fix-bug;
- After production GO completes, receipt **PRIMARY** `NEXT_ACTION` =
  `/opsx-test case=<CASE_ID> finding=<FINDING_ID> verify`;
- **SECONDARY** pasteable handback (CLOSE_POLICY; no silent return):
  `HANDBACK_COMMAND` from LEDGER or
  `/opsx-bug-team case=<CASE_ID> mode=resume-family-fanout`;
- **ALSO_OK**: solo walk / OpenSpec coverage — not a violation.

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
- INDEX_PATH: .opsx/runs/bug-cases/INDEX.md
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
  CLAIM_TOKEN:
  RESULT:
  OUTPUT_PATH:
  NEXT_ACTION:
  ALSO_OK:
  HANDBACK_COMMAND:
  PERSISTENCE_DECISION:
  CANONICAL_INTAKE_ID:
  RELATED_FINDING_ID:

ROUTE_TRANSITION:
  (schema: .cursor/pipeline/contracts/bug-episode/ROUTE_TRANSITION.md)
  FROM_STATE:
  RESULT:
  TO_STATE:
  NEXT_COMMAND:
  NEXT_ARGS:
  PRECONDITIONS:
  REQUIRED_EVIDENCE:
  RECOVERY_CLASS:
  MISSION_COMPLETE: no
  FINDING_TERMINAL: no | yes
  FINDING_TERMINAL_KIND: none | …
```

## ROUTE_TRANSITION (mandatory for supervisor)

Authority: `.cursor/pipeline/contracts/bug-episode/ROUTE_TRANSITION.md`.
Narrative `Следующее действие` / prose stop conditions are UX only — they
MUST NOT invent a competing `NEXT_COMMAND` when structured fields exist.
`MISSION_COMPLETE` on this worker is always `no` (supervisor owns mission).

Canonical hop packets (emit the matching one):

```text
fix_now (без GO):
  TO_STATE: AWAITING_RED
  NEXT_COMMAND: /opsx-test
  NEXT_ARGS: case=… finding=…   # bug-regression / RED author
  PRECONDITIONS.GO_TOKEN: NOT_APPLICABLE
  PRECONDITIONS.RED_REQUIRED: yes
  REQUIRED_EVIDENCE: none yet (RED owned by /opsx-test)
  RECOVERY_CLASS: ADVANCE
  MISSION_COMPLETE: no
  FINDING_TERMINAL: no

GO applied (production patch done):
  TO_STATE: AWAITING_GREEN
  NEXT_COMMAND: /opsx-test
  NEXT_ARGS: case=… finding=… verify
  PRECONDITIONS.GREEN_REQUIRED: yes
  REQUIRED_EVIDENCE: writer execution evidence / diff refs
  RECOVERY_CLASS: ADVANCE
  MISSION_COMPLETE: no
  FINDING_TERMINAL: no

blocked_needs_red_before_go:
  RECOVERY_CLASS: BLOCKED
  NEXT_COMMAND: /opsx-test
  PRECONDITIONS.RED_REQUIRED: yes
  MISSION_COMPLETE: no
  FINDING_TERMINAL: no

claim / status / route_mismatch blockers:
  RECOVERY_CLASS: BLOCKED | PAUSED | NEEDS_OWNER
  MISSION_COMPLETE: no
  FINDING_TERMINAL: no
  NEXT_COMMAND: per existing pasteable next (claim-next / classify / none)

false_positive (finding terminal disposition):
  FINDING_TERMINAL: yes
  FINDING_TERMINAL_KIND: CLOSED_FALSE_POSITIVE
  RECOVERY_CLASS: TERMINAL
  MISSION_COMPLETE: no
  NEXT_COMMAND: CLOSED_NO_IMPLEMENTATION | materialize close path

plan_only | needs_entrypoint_map | needs_openspec_update:
  RECOVERY_CLASS: PAUSED | NEEDS_OWNER | ADVANCE
  MISSION_COMPLETE: no
  FINDING_TERMINAL: no
  NEXT_COMMAND: exact pasteable from existing contract (no invented route)
```

`RESULT` в receipt без `GO` обычно одно из: `adjudicated`, `false_positive`, `needs_entrypoint_map`, `plan_only`, `blocked`, `duplicate_intake`.

`CLAIM_TOKEN` в receipt:

* обязателен (non-empty echo matched token) после успешного Claim ownership
  gate для claimed finding;
* пуст / absent, если finding не claimed, gate не применялся, или
  gate blocked (`blocked_claimed_without_durable_token` /
  `blocked_missing_claim_token` / `blocked_claim_token_mismatch` / …);
  `STATUS: claimed` + пустой durable token **не** success path —
  только blocker, не optional ownership;
* same-chat Resume gate может использовать это поле как предоставленный
  token (exact match к durable), когда follow-up опускает `claim_token=`.

Для `PERSISTENCE_DECISION=duplicate_intake`:

* `FINDING_ID` в receipt = `RELATED_FINDING_ID` (canonical, unchanged);
* `CANONICAL_INTAKE_ID` обязателен;
* `OUTPUT_PATH` указывает на `results/<INTAKE_ID>-duplicate-check.md`.

Для `PERSISTENCE_DECISION=new_finding`:

* `FINDING_ID` = новый finding;
* `SOURCE_INTAKE_ID` finding = текущий `INTAKE_ID`;
* `CANONICAL_INTAKE_ID` / `RELATED_FINDING_ID` пусты.

`NEXT_ACTION` в receipt обязан соответствовать `FOLLOW_UP_SCOPE`, **кроме**
вердикта `fix_now` без GO — тогда pasteable next **обязан** быть:

```text
/opsx-test case=<CASE_ID> finding=<FINDING_ID>
```

(не `/opsx-fix-bug GO`).

Для других вердиктов:

- `none` → `none`;
- `invariant_candidate` → точный handoff в `/opsx-invariant`;
- `research_candidate_only` → точный read-only extraction handoff либо `none`.

`OUTPUT_PATH` указывает на finding packet или intake path, если finding ещё не создан.

Если вердикт `needs_entrypoint_map`, `Следующее действие` не должно быть `GO to apply`.

Оно должно быть read-only prompt/command для поиска entrypoints.

После потери чатов продолжение восстанавливается из `.opsx/runs/bug-cases/INDEX.md` по полям recovery row case.

## Поведение с GO

Когда `GO` есть:

1. если `case`/`intake` отсутствуют — сначала **Resume gate** (same-chat prior `COMMAND_RECEIPT`); при успешном resume продолжай forensics на этих IDs (включая `FINDING_ID` / `CLAIM_TOKEN` из receipt, если есть); **не** вызывай `mode=intake` и **не** создавай новый case. Если resume невозможен и ввод — follow-up только `GO` без raw payload → `blocked_needs_case_intake` (без production edits и без нового case). Если resume невозможен, но есть новый raw bug payload → допустим one-shot first-run `mode=intake`, затем forensics;
2. если передан или resumed `finding=` — **Claim ownership gate** до forensics и до любого production edit (п.2 DUP-/duplicate_root → `blocked_finding_status_not_actionable`; claim-first при `available`+`CHAT_REQUIRED=true` → `blocked_needs_claim_first`; п.4 statuses → `blocked_finding_status_not_actionable`; для `claimed` — всегда: пустой durable `CLAIM_TOKEN` → `blocked_claimed_without_durable_token`; иначе token из ввода или prior receipt `CLAIM_TOKEN`); mismatch/missing/corrupt-claim/needs_claim_first/status_not_actionable → `blocked`, без code changes;
3. выполни тот же forensics;
4. если вердикт не `fix_now`, не редактируй production code; process-artifacts updates через `mode=update` всё ещё допустимы;
5. если вердикт `fix_now`, сначала проверь RED-before-GO gate; при fail —
   `blocked_needs_red_before_go`, без production edits;
6. production-only patch; **test freeze** — не редактируй tests;
7. держи diff минимальным;
8. не патчь dead code без явного обоснования;
9. не трогай forbidden files/actions;
10. optional: re-run same `TEST_ID` as check only; GREEN →
    `/opsx-test case=… finding=… verify` as PRIMARY next (not close);
    emit pasteable bug-team handback as SECONDARY/ALSO_OK per CLOSE_POLICY;
11. отчитайся по changed files, optional pytest check, durable ids;
12. заверши `COMMAND_RECEIPT` с `CASE_ID` / `INTAKE_ID` / `FINDING_ID` /
    `CLAIM_TOKEN` (echo matched token после успешного claim gate; иначе
    пусто) / `PERSISTENCE_DECISION` / `RED_EVIDENCE_PATH` /
    `HANDBACK_COMMAND` / `ALSO_OK` when case-tied.

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

Если Bugbot, `/opsx-project-bug-hunt`, `/opsx-bug-hunt` или другой hunter
пропустил или неправильно классифицировал проблему, выдай hunter update note:

```text
Hunter feedback:
- missed/misclassified condition:
- required new check:
- example false positive/false negative:
- suggested rule:
- suggested fixture/test:
- preferred_learning_target: .cursor/commands/opsx-project-bug-hunt.md
  (section: Project hunt checklist (learning target))
- pasteable_next: /opsx-learn-from-bug case=… finding=… target=.cursor/commands/opsx-project-bug-hunt.md
```

Текст значений должен быть на русском, кроме имён функций, файлов, тестов и технических токенов.

Цель — не дать тому же классу багов снова дойти до Bugbot: residual Bugbot
miss усиливает **project** hunter checklist, не создаёт второй free-form audit.

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

- если передан / resumed `finding=` с `FINDING_ID` `DUP-*`, relation/class
  `duplicate_root`, или `STATUS: duplicate_root_observation` — stop с
  `blocked_finding_status_not_actionable` до forensics (даже при wrongly
  `available`+`CHAT_REQUIRED=true`); pasteable next: `none` (не claim-next);
- если передан / resumed `finding=` с `CHAT_REQUIRED: true` и
  `STATUS: available` (и не класс п.2 DUP-/duplicate_root) — stop с
  `blocked_needs_claim_first` до forensics;
  pasteable next только `/opsx-claim-next-bug …` (не invent `CLAIM_TOKEN`);
- если claim gate pass (или claim не требуется), но в LEDGER
  `## ROUTE_STATE` отсутствует `CURRENT_CLASSIFICATION` — stop с
  `blocked_needs_classify_first` до forensics / `GO`;
  pasteable next только `/opsx-classify-bug case=… finding=…`;
- если передан / resumed `finding=` со `STATUS` ∈
  {`backlog`, `blocked`, `absorbed_*`, `closed_false_positive`,
  `closed_fixed`, `promoted_to_root_case`, `duplicate_ancestor`,
  `duplicate_root_observation`,
  `adjudicating`, `ready_for_fix`, `implementing`, `verification`} —
  stop с `blocked_finding_status_not_actionable` (любой `CHAT_REQUIRED`);
  pasteable next: `none` (не claim-next);
- если передан / resumed `finding=` со `STATUS: claimed` и durable
  `CLAIM_TOKEN` пуст / absent — stop с
  `blocked_claimed_without_durable_token` (не invent token; не optional
  ownership); pasteable next только materialize
  `repair=mint_missing_claim_token` или `repair=release_corrupt_claim`
  (не `/opsx-claim-next-bug` для durable-empty);
- если передан / resumed `finding=` со `STATUS: claimed` и non-empty durable
  `CLAIM_TOKEN` — предоставленный token (`claim_token=` во вводе **или**
  same-chat prior `COMMAND_RECEIPT.CLAIM_TOKEN`) сверен exact match, иначе
  stop с `blocked_missing_claim_token` / `blocked_claim_token_mismatch`;
  после успешного match исходящий receipt содержит `CLAIM_TOKEN`;
- raw intake записан до глубокого анализа, если case/intake не были переданы;
- выбран ровно один `PERSISTENCE_DECISION`: `new_finding` или `duplicate_intake`;
- при `new_finding` создан новый finding с `SOURCE_INTAKE_ID` = текущий intake;
- при `duplicate_intake` canonical finding не изменён; intake закрыт как `closed_duplicate`;
- не обновлён finding чужого intake без `relation=duplicate_intake`;
- finding persisted через `mode=update` согласно persistence decision;
- INDEX recovery row обновлён и содержит pasteable `NEXT_ACTION`;
- без `GO` изменены только paths под `.opsx/runs/bug-cases/**`;
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
- при omitted `case`/`intake` сначала выполнен Resume gate (same-chat prior `COMMAND_RECEIPT`); follow-up `GO` без IDs не создал новый case;
- при `case` + `finding` без `intake` intake разрешён из finding
  `SOURCE_INTAKE_ID` / `PRIMARY_INTAKE_ID`, иначе finding-first без
  `mode=intake` (не создан spurious intake);
- при follow-up `GO` без IDs, без usable prior receipt и без нового raw payload — `blocked_needs_case_intake`, без `mode=intake`;
- `COMMAND_RECEIPT` содержит `CASE_ID`, `INTAKE_ID`, `FINDING_ID`,
  `PERSISTENCE_DECISION`, и `CLAIM_TOKEN` (non-empty после успешного claim
  gate; иначе пусто).

## Acceptance scenario (durable intake)

Ожидаемый путь одной команды без `GO`:

```text
raw user bug report
→ /opsx-fix-bug <report>          # без GO, без case/intake
→ Resume gate: no prior receipt → first-run
→ mode=intake пишет intakes/<INTAKE_ID>.md до глубокого анализа
→ CASE_ID и INTAKE_ID созданы
→ read-only adjudication
→ PERSISTENCE_DECISION=new_finding
→ mode=update пишет новый finding с SOURCE_INTAKE_ID=<current intake>
→ INDEX.md recovery row обновлён
→ чаты потеряны
→ продолжение из .opsx/runs/bug-cases/INDEX.md через pasteable NEXT_ACTION
```

## Acceptance scenario (same-chat GO resume — no duplicate case)

```text
1. /opsx-fix-bug <report>          # без GO, без case/intake
   → first-run mode=intake
   → COMMAND_RECEIPT: CASE_ID=BUGCASE-X, INTAKE_ID=INTAKE-001, FINDING_ID=...
2. в том же чате: /opsx-fix-bug GO   # IDs из receipt опущены
   → Resume gate: reuse CASE_ID/INTAKE_ID из prior COMMAND_RECEIPT
   → НЕ вызывать mode=intake
   → НЕ создавать второй case / INTAKE-002 для того же сигнала
3. в новом чате: /opsx-fix-bug GO     # без case/intake, без prior receipt, без raw payload
   → blocked_needs_case_intake
   → pasteable next из INDEX.md или из старого receipt
4. запрещено: same-chat GO follow-up без IDs → mode=intake → второй BUGCASE для того же сигнала
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

## Acceptance scenario (claim ownership)

```text
0. /opsx-fix-bug case=BUGCASE-X finding=CHILD-002
   (STATUS=available, CHAT_REQUIRED=true; без claim)
   → blocked_needs_claim_first; no adjudication writes
   → next только /opsx-claim-next-bug case=BUGCASE-X chat_label="…"
   → НЕ blocked_missing_claim_token; НЕ invent CLAIM_TOKEN
0b. finding STATUS=blocked|backlog|absorbed_*|closed_false_positive|
   closed_fixed|promoted_to_root_case|duplicate_ancestor|
   duplicate_root_observation|
   adjudicating|ready_for_fix|implementing|verification
   (любой CHAT_REQUIRED, в т.ч. true **или** false)
   → blocked_finding_status_not_actionable; no adjudication writes
   → pasteable next: none (НЕ /opsx-claim-next-bug; НЕ claim-first петля;
     НЕ п.6 optional-token)
   → НЕ blocked_needs_claim_first; НЕ fall-through
0c. finding STATUS=promoted_to_root_case|duplicate_ancestor|
   duplicate_root_observation
   (materialize-written; CHAT_REQUIRED обычно false)
   → всё равно blocked_finding_status_not_actionable (не п.6)
0d. finding=DUP-* (или relation/class=duplicate_root), даже STATUS=available
   + CHAT_REQUIRED=true
   → blocked_finding_status_not_actionable; pasteable none
   → НЕ blocked_needs_claim_first; НЕ claim-first петля; НЕ п.6
1. /opsx-claim-next-bug case=BUGCASE-X chat_label="chat-a"
   → FINDING_ID=CHILD-002, CLAIM_TOKEN=CLAIM/BUGCASE-X/CHILD-002/<ts>
2. /opsx-fix-bug case=BUGCASE-X intake=... finding=CHILD-002
   (без claim_token и без prior receipt CLAIM_TOKEN)
   → blocked_missing_claim_token; no adjudication writes
3. /opsx-fix-bug ... finding=CHILD-002 claim_token=WRONG
   → blocked_claim_token_mismatch; no production/GO path
4. /opsx-fix-bug ... finding=CHILD-002 claim_token=CLAIM/BUGCASE-X/CHILD-002/<ts>
   → gate pass; read-only adjudication allowed
   → COMMAND_RECEIPT включает CLAIM_TOKEN=CLAIM/BUGCASE-X/CHILD-002/<ts>
5. в том же чате: /opsx-fix-bug GO
   (IDs и claim_token опущены)
   → Resume gate: reuse CASE_ID/INTAKE_ID/FINDING_ID/CLAIM_TOKEN из prior receipt
   → Claim ownership gate: token из receipt exact-match durable → gate pass
   → НЕ blocked_missing_claim_token
6. параллельный чат с тем же finding= без валидного token (и без
   same-chat prior receipt CLAIM_TOKEN) не обходит ownership
7. «я тот же чат» без CLAIM_TOKEN в prior receipt → blocked_missing_claim_token
8. finding STATUS=claimed, durable CLAIM_TOKEN пуст / absent
   → blocked_claimed_without_durable_token; no adjudication / update / GO
   → next только materialize repair:
     /opsx-materialize-bug-queue mode=update case=… finding=… repair=mint_missing_claim_token
     (OWNER_CHAT задан) или repair=release_corrupt_claim затем claim-next;
     НЕ /opsx-claim-next-bug как единственный next при durable-empty;
     НЕ invent CLAIM_TOKEN; НЕ optional ownership через «достаточно case+finding»
9. finding STATUS=claimed, durable CLAIM_TOKEN непустой, но в этом чате
   нет usable claim_token=/prior receipt CLAIM_TOKEN
   → blocked_missing_claim_token; next /opsx-claim-next-bug … (echo via
     owner_already_has_open_claim) или retry fix-bug с token из claim packet
```

## Route-trace event requirements (SCHEMA_VERSION 2)

Authority: `.cursor/pipeline/contracts/bug-episode/ROUTE_TRACE.md`.

On every significant hop that touches a durable case map, append **one**
JSONL event to:

```text
.opsx/runs/bug-cases/<CASE_ID>/results/ROUTE-TRACE.jsonl
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

