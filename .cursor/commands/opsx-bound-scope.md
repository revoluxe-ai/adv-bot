---
name: /opsx-bound-scope
id: opsx-bound-scope
category: Workflow
description: "Урезать раздутый OpenSpec change: сейчас vs потом; потом — в WORKLOG; KEEP — handoff в /opsx-update"
---

# /opsx-bound-scope

Простыми словами: change раздулся — ставим границу «делаем сейчас», остальное
не выкидываем, а складываем в `DOTO/WORKLOG.md` «на потом». Правки ТЗ в файлах
change делает уже `/opsx-update` по handoff.

Это локальная WB Sky OpenSpec-команда (не upstream OpenSpec).

**Язык для человека:** русский, коротко, без жаргона.  
**Машинные токены** (`PRINTOUT_KEEP`, `UPDATE_HANDOFF`, статусы) — оставлять
как есть для handoff; рядом всегда давать человеческое пояснение.

## Зачем

1. Жёстко решить, что остаётся в **текущем** change.
2. Не потерять отложенные идеи — записать их в WORKLOG.
3. Дать `/opsx-update` понятный пакет: что вырезать из ТЗ.

## Когда использовать

- ТЗ/tasks/specs раздулись («нафантазировали»).
- Нужен кусок «можно довести и сдать», остальное — позже.
- После `/opsx-explore` с блоком `NOW_LATER`, и ты согласен с «сейчас / потом»
  (explore только предлагает; паркует эта команда).

## Когда не использовать

- Просто поправить противоречия в ТЗ, без «унести в worklog» → `/opsx-update`
- Просто подумать / почитать WORKLOG → `/opsx-explore`
- Резать git/PR → `/opsx-split-for-pr`
- Совсем другая задумка продукта → `/opsx-new`
- Учёба по багу → `/opsx-learn-from-bug`
- Только обсудить сейчас/потом в чате, без записи → оставайся в explore

## Как запускать

```text
/opsx-bound-scope change=<CHANGE_ID>
/opsx-bound-scope:GO change=<CHANGE_ID>
```

Опционально подсказка границы:

```text
/opsx-bound-scope change=<CHANGE_ID> keep=<одной фразой: что оставляем сейчас>
```

Нет `change=` — спроси через `openspec list --json`, как в `/opsx-update`.
Не угадывай.

---

## Режимы (человечески)

### Без GO — только план (ничего не пишем)

Показать две понятные распечатки и **остановиться**.

1. **«Оставляем в change сейчас»** (`PRINTOUT_KEEP`)
2. **«Уносим в WORKLOG на потом»** (`PRINTOUT_WORKLOG`)

В конце — один простой вопрос про GO (см. ниже). Файлы не трогать.

### С GO — зафиксировать «на потом» + handoff

Только если человек явно сказал `GO` / запустил `:GO` **по этому плану**.
«Ок», «понятно», обсуждение правок плана ≠ GO.

После GO:

1. Дописать в `DOTO/WORKLOG.md` ровно то, что было во второй распечатке.
2. Выдать `UPDATE_HANDOFF` для `/opsx-update` (сузить ТЗ до «сейчас»).
3. Сами файлы change **не** редактировать (это update).
4. Код продукта **не** трогать.
5. Уже написанный код под «потом» **не** откатывать.

---

## Human-native GO (обязательно в конце плана)

После двух распечаток спросить **по-русски**, одним блоком:

```text
Коротко:
- В change оставляем: <N> пунктов (см. распечатку 1).
- В WORKLOG уносим: <M> пунктов (см. распечатку 2).
- Код и файлы ТЗ пока не меняю.

Если граница ок — напиши:
  GO

или запусти:
  /opsx-bound-scope:GO change=<CHANGE_ID>

Если что-то не так — напиши, что перенести из «сейчас» в «потом»
(или наоборот). Пока не будет GO, в WORKLOG ничего не пишу.
```

Не требовать помнить внутренние имена токенов.  
Не сыпать таблицами authority в лицо — их держать ниже для агента.

---

## Кто за что отвечает (кратко)

| Что | Кто |
|---|---|
| Предложить сейчас/потом в размышлении | `/opsx-explore` (`NOW_LATER`) |
| Показать план + по GO записать «потом» в WORKLOG | эта команда |
| Вырезать «потом» из файлов ТЗ | `/opsx-update` по handoff |
| Вернуть идею из WORKLOG обратно в change | `/opsx-update` + явное `REENTER_CONFIRMED` |
| Резать PR по git | `/opsx-split-for-pr` |

Цепочка:

```text
explore (NOW_LATER, по желанию)
  → bound-scope (две распечатки, ждём GO)
  → bound-scope:GO (WORKLOG + handoff)
  → update (сужает ТЗ; помнит отложенное)
  → позже вернуть идею: update + REENTER_CONFIRMED
```

---

## Preflight

Следовать `.cursor/commands/opsx-source-resolution.md` и
`.cursor/commands/opsx-execution-preflight.md`.

```text
OPERATION_REASON: resolve named change + existing planning artifacts
REQUIRED_FOR: KEEP/DEFER units and UPDATE_HANDOFF paths
SKIP_IF: change= missing (prompt first)
TIME_BUDGET: status/list 15s; targeted reads ≤120 lines first pass
FAILURE_BEHAVIOR: BLOCKED_NEEDS_OWNER or EVIDENCE_GAP / NO_GO
```

Architecture Decision Lookup — как у `/opsx-update`, если разрез трогает
ownership / layering / write-path / invariant. Дыры → `NO_GO`, не выдумывать KEEP.

---

## Шаги — план

1. Взять `change=` или спросить.
2. `openspec status --change "<name>" --json` — только `existingOutputPaths`.
3. Прочитать нужные proposal/design/tasks/specs (+ decisions по ADL).
3b. Если был `NOW_LATER` / подсказка «сейчас X, потом Y» — взять как старт,
    сверить с артефактами, показать расхождения простым языком.
4. Разметить пункты:

```text
KEEP_IN_CHANGE          → сейчас в change
DEFER_TO_WORKLOG        → в WORKLOG
IMPLEMENTED_BUT_DEFERRED → в ТЗ хотим «потом», но в коде уже есть
```

`IMPLEMENTED_BUT_DEFERRED`: не предлагать откат кода. До GO спросить:
оставить в «сейчас» или унести в WORKLOG с пометкой «уже частично в коде».

5. Неясный пункт — **один** вопрос человеку, не угадывать MVP.
6. Две распечатки + человеческий итог + блок GO. Стоп.

## Шаги — GO

1. Убедиться, что GO относится к последнему принятому плану.
2. Нерешённый `IMPLEMENTED_BUT_DEFERRED` → стоп
   (`BLOCKED_NEEDS_OWNER`), WORKLOG и handoff не писать.
3. Append в WORKLOG ровно из распечатки 2 (не переписывать чужой inbox).
4. Выдать `UPDATE_HANDOFF`.
5. Сказать по-русски: следующий шаг — `/opsx-update` с этим handoff
   (не запускать update сам, пока человек явно не попросил).

---

## Распечатка 1 — что оставляем сейчас

Сначала человеческий заголовок, потом машинный блок:

```text
=== 1. Оставляем в change сейчас ===

Простыми словами:
Мы сужаем текущую работу до: <одна фраза MVP>.
Вот что остаётся owed в этом change:

- <пункт> — зачем сейчас
…

Что уходит «на потом» — в распечатке 2 (в DoD этого change больше не должно висеть).

PRINTOUT_KEEP:
CHANGE_ID: <id>
MVP_BOUNDARY: <one sentence>
KEEP_UNITS:
- <title> — <artifact path> — <why keep>
OUT_OF_SCOPE_AFTER_BOUND:
- <title> — deferred (see PRINTOUT_WORKLOG)
ARTIFACT_TARGETS:
- path: <existingOutputPath>
  keep_edits: <что update должен вырезать/сузить>
STATUS: PLAN_READY | BOUND_APPLIED
```

## Распечатка 2 — что уносим в WORKLOG

```text
=== 2. Уносим в WORKLOG на потом ===

Простыми словами:
Эти идеи не пропадают. После GO я допишу их в DOTO/WORKLOG.md.
Потом можно вернуть в change только через /opsx-update + REENTER_CONFIRMED.

PRINTOUT_WORKLOG:
TARGET: DOTO/WORKLOG.md
ENTRIES:
- [ ] [deferred-from:<CHANGE_ID>] <короткий заголовок>
  source: openspec/changes/<CHANGE_ID>/<artifact>
  reason: out_of_current_mvp | oversized | owner_park
  notes: <1–3 строки из старого ТЗ>
```

На GO можно обернуть секцией:

```text
## Deferred from change <CHANGE_ID> (<YYYY-MM-DD>)
```

WORKLOG = сырые заметки, не второй tasks.md.

---

## UPDATE_HANDOFF (после GO)

Машинный блок для `/opsx-update` + одна русская строка сверху:

```text
Для человека: дальше запусти /opsx-update — он вырежет из ТЗ всё «на потом».
Отложенное из WORKLOG сам не вернёт, пока не скажешь REENTER_CONFIRMED.

UPDATE_HANDOFF:
SOURCE_COMMAND: /opsx-bound-scope
CHANGE_ID: <id>
STATUS: READY_FOR_UPDATE
WORKLOG_APPENDED: yes | no
WORKLOG_PATH: DOTO/WORKLOG.md
KEEP_MVP_BOUNDARY: <one sentence>
APPLY_KEEP_UNITS:
- ...
REMOVE_OR_NARROW_FROM_ARTIFACTS:
- path: <existingOutputPath>
  action: remove | narrow | mark_out_of_scope
  units: [...]
  instructions: <concrete edit guidance>
DO_NOT:
- recreate deferred units as owed tasks
- edit production code in this update
- create new change artifacts (continue frontier unchanged)
- silently ignore DEFERRED_PARKS_FOR_CHANGE (update must still print them)
NEXT_COMMAND: /opsx-update change=<CHANGE_ID>
NOTE_FOR_UPDATE: After this handoff, open WORKLOG parks for this CHANGE_ID remain
  out of scope until owner replies REENTER_CONFIRMED on a later /opsx-update.
```

---

## Статусы

```text
PLAN_READY
BOUND_APPLIED
BLOCKED_NEEDS_OWNER
NO_GO
PARTIAL_BLOCKED
```

Теги пунктов: `KEEP_IN_CHANGE` | `DEFER_TO_WORKLOG` | `IMPLEMENTED_BUT_DEFERRED`

## Ошибки

- Неясно сейчас/потом → стоп, один вопрос.
- ADL / EVIDENCE_GAP → `NO_GO`, WORKLOG не трогать.
- Сбой mid-GO → `PARTIAL_BLOCKED`, не врать что handoff готов.
- Не выдумывать «потом» из воздуха.
- Не удалять код.
- Не обходить verify / archive / sync.

---

## Итог человеку (каждый запуск)

Писать по-русски, поля можно дублировать токенами:

```text
Что сделал:
Зачем:
Где мы сейчас:
Нужно твоё решение:
Что дальше:
Пока не делай:
STATUS:
CHANGE_ID:
KEEP_COUNT:
DEFER_COUNT:
IMPLEMENTED_BUT_DEFERRED_COUNT:
WORKLOG_WRITTEN: yes | no
UPDATE_HANDOFF_EMITTED: yes | no
```

### После плана

```text
Нужно твоё решение: да — граница ок?
Что дальше: напиши GO  (или /opsx-bound-scope:GO change=<CHANGE_ID>)
Пока не делай: не править ТЗ руками «наугад»; не apply; не archive
WORKLOG_WRITTEN: no
UPDATE_HANDOFF_EMITTED: no
```

### После GO

```text
Нужно твоё решение: нет (если не заблокированы)
Что дальше: /opsx-update change=<CHANGE_ID> — вставь/используй UPDATE_HANDOFF
Пока не делай: считать WORKLOG задачами текущего change; шипить до update;
  откатывать код «на потом»
WORKLOG_WRITTEN: yes (если ок)
UPDATE_HANDOFF_EMITTED: yes (если ок)
```

---

## Запрещено

- Пропускать две распечатки в плане.
- Писать WORKLOG без GO.
- Самим править артефакты change (это `/opsx-update`).
- Путать с `/opsx-split-for-pr`.
- Класть «на потом» в `.cursor/worklogs/` вместо `DOTO/WORKLOG.md`.
- Автоматически плодить новый OpenSpec change на каждую отложенную строку.
- Говорить, что парковка = автоматический возврат в scope позже.
- Учить update игнорировать `DEFERRED_PARKS_FOR_CHANGE`.
- Заваливать человека английским process-жагоном без русской расшифровки.
