---
description: "Разобрать сырой вывод Pyright/Mypy и, только с GO, внести минимальные production typing fixes в подтверждённом scope."
argument-hint: "[tool=pyright|pyright-strict|mypy] [command=<exact>] [scope=<path>] [baseline=<ref>] [GO] <raw typecheck output | path=...>"
---

# /opsx-fix-types

Используй эту команду для разбора и исправления ошибок статической типизации из сырого вывода `pyright`, `pyright-strict` или `mypy`.

Это отдельная ветка процесса, не общий bug lifecycle и не замена `/opsx-test` / `/opsx-fix-bug`.

```text
raw pyright/mypy output
→ /opsx-fix-types без GO
→ read-only triage и план исправления
→ /opsx-fix-types GO
→ production typing fixes
→ повторный type check
→ результат и один NEXT_ACTION
```

## Язык ответа

Пояснения пользователю — на русском.

Технические токены, enum-значения, поля output contract, команды и пути — на английском как в контракте ниже.

## User input

```text
$ARGUMENTS
```

Извлеки при наличии:

```text
tool=pyright|pyright-strict|mypy
command=<exact original command>
scope=<optional path/change/case>
baseline=<optional commit/ref>
path=<exact path to saved typecheck output>
GO
```

Оставшийся текст считай raw type-check output, если `path=` не задан.

Если `tool` или исходная команда однозначно видны из output (например `pyright-strict`, `poetry run pyright`, `mypy ...`), не требуй повторного ввода.

Если `path=` задан — прочитай этот exact path напрямую (см. source-resolution). Не ищи файл по репозиторию.

## Shared contracts (mandatory)

Следуй:

- `.cursor/commands/opsx-source-resolution.md`
- `.cursor/commands/opsx-execution-preflight.md`

Не копируй эти контракты сюда. Не создавай второй lifecycle authority.

Для git/diff/baseline ops применяй purpose-driven preflight:

```text
OPERATION_REASON: classify diagnostic vs current diff / baseline
REQUIRED_FOR: disposition caused_by_current_diff | pre_existing_* when baseline/diff available
SKIP_IF: no baseline and disposition can stay cannot_determine without blocking triage
TIME_BUDGET: branch 5s / status 10s / diff 15s
FAILURE_BEHAVIOR: mark cannot_determine for relation; continue triage; do not hang
```

Type-check re-run после `GO` — обязателен; это не optional preflight.

## Boundary

Эта команда владеет только type-check diagnostics (Pyright / Mypy).

Не владеет:

- поведенческими багами → `/opsx-fix-bug`;
- написанием/правкой тестов как основной целью → `/opsx-test`;
- triage падений pytest → `/opsx-test-triage`;
- общим lint (Ruff, Bandit и т.п.) без отдельного owner decision.

Не создавай bug-case map, OpenSpec change или новый global verdict taxonomy ради typing.

## Write permission

### Без GO

Только read-only triage.

Запрещено изменять:

- `app/**`
- `tests/**`
- `openspec/**`
- любые production/config/CI paths

Process notes под `.tmp/` не обязательны; по умолчанию не создавай durable case map.

### С GO

`GO` разрешает изменения только если итоговый `VERDICT=fix_now` (или группа с `disposition` / plan помечена к применению и in-scope).

Разрешено только:

- минимальные production typing fixes;
- удаление ненужных casts;
- уточнение annotations;
- typed helper / DTO / narrowing;
- корректировка generic / `default_factory` typing;
- узкие правки, необходимые для прохождения подтверждённых in-scope diagnostics.

Запрещено даже с `GO`:

- массовый refactor;
- поведенческие изменения без отдельного bug finding;
- suppressions без явного обоснования;
- `# type: ignore` как default;
- снижение strictness;
- изменение конфигурации Pyright/Mypy для сокрытия ошибок;
- исправление out-of-scope debt;
- stage / commit / push / deploy / migrations / secrets / infra.

Если `GO` есть, но `VERDICT` ≠ `fix_now` → `CHANGES_ALLOWED: none`, код не трогай.

## Без GO — обязательные шаги

1. Определи `TOOL` и `ORIGINAL_COMMAND`.
2. Распарси diagnostics из raw output или файла.
3. Дедуплицируй повторяющиеся/искажённые terminal lines (`duplicate_diagnostic`).
4. Проверь exact source paths (`missing_source_path` если путь не существует).
5. Сгруппируй по файлам и root cause.
6. Соотнеси с текущим diff / `baseline`, когда доступны.
7. Раздели:
   - current in-scope errors;
   - pre-existing in-scope debt;
   - pre-existing out-of-scope debt;
   - unresolved diagnostics.
8. Для каждой группы предложи минимальный production typing fix.
9. Реши `GO_ELIGIBLE` и `VERDICT`.
10. Ничего не меняй в коде.

## Verdicts

Локальные verdicts (не новая global taxonomy):

```text
fix_now
plan_only
false_positive
blocked
```

Правила выбора:

| VERDICT | Когда |
|---|---|
| `fix_now` | Есть подтверждённые in-scope diagnostics с безопасным минимальным typing fix; после `GO` можно править. |
| `plan_only` | Нужен план / уточнение scope, но авто-fix сейчас небезопасен или неоднозначен. |
| `false_positive` | Diagnostic не отражает реальную typing проблему (например, stale output, уже исправлено, tool noise) — с evidence. |
| `blocked` | Нельзя продолжать: missing path, missing source extraction, нет raw output, неоднозначный tool/command и нельзя вывести. |

### Diagnostic dispositions

```text
caused_by_current_diff
pre_existing_in_scope
pre_existing_out_of_scope
cannot_determine
duplicate_diagnostic
missing_source_path
```

`in_scope=true` только для diagnostics, которые входят в заявленный `scope` / затронутые текущей работой файлы / явно подтверждённый typing scope пользователя.

`blocks_current_work=true` только если diagnostic мешает текущему type-check gate для in-scope files.

## GO semantics

После triage с `VERDICT=fix_now` пользователь запускает ту же команду с `GO` и тем же `tool` / `command` / `scope` / diagnostics context.

При `GO`:

1. Повторно подтверди in-scope groups (не расширяй scope молча).
2. Внеси только разрешённые typing fixes.
3. Повтори исходную точную type-check command (`ORIGINAL_COMMAND`).
4. При необходимости — narrow check только по затронутым путям.
5. Заполни `TYPECHECK_RESULT`.
6. Не объявляй успех (`remaining_in_scope` cleared), если исходная команда всё ещё красная из-за in-scope errors.

Если после typing fix обнаружен реальный behavioral defect:

```text
NEXT_ACTION.command: /opsx-fix-bug
```

без `GO`, с кратким symptom — не чини поведение внутри `/opsx-fix-types`.

## Verification

Обязательно после `GO`-правок:

1. Exact replay `ORIGINAL_COMMAND`.
2. Optional narrow check по changed paths.
3. Покажи:
   - сколько diagnostics было;
   - сколько исправлено;
   - сколько осталось;
   - появились ли новые diagnostics.
4. `remaining_in_scope > 0` ⇒ не terminal success для текущего scope.

## Routing

```text
raw Pyright/Mypy output
→ /opsx-fix-types без GO
```

```text
VERDICT=fix_now
→ /opsx-fix-types GO с тем же tool/command/scope
```

```text
VERDICT=blocked
→ точный missing path / baseline / source extraction (NEXT_ACTION называет недостающее)
```

```text
after GO, all in-scope diagnostics cleared
→ NEXT_ACTION: none
→ terminal_for_current_scope=true
```

```text
after GO, behavioral defect discovered
→ /opsx-fix-bug без GO
```

```text
only out-of-scope debt remains
→ terminal_for_current_scope=true
→ optional backlog отдельно от NEXT_ACTION
→ NEXT_ACTION: none
```

Ровно одна `NEXT_ACTION.command` (exact pasteable command или `none`).

## Integration (callers)

Короткие route-ссылки живут в:

- `.cursor/commands/opsx-test.md`
- `.cursor/commands/opsx-test-triage.md`
- `.cursor/commands/opsx-fix-bug.md`

При входном Pyright/Mypy / type-check diagnostic packet эти команды **не** разбирают typing сами — возвращают:

```text
NEXT_ACTION: /opsx-fix-types
```

`/opsx-fix-bug` остаётся владельцем behavioral production bugs; пакетные type diagnostics может передать сюда.

## Output contract

Каждый terminal output обязан содержать:

```text
VERDICT:
TOOL:
ORIGINAL_COMMAND:
RAW_DIAGNOSTIC_COUNT:
UNIQUE_DIAGNOSTIC_COUNT:

DIAGNOSTIC_GROUPS:
- group_id:
- files:
- root_cause:
- disposition:
- in_scope:
- blocks_current_work:
- proposed_fix:
- evidence:

GO_ELIGIBLE:
CHANGES_ALLOWED:
CHANGES_FORBIDDEN:

TYPECHECK_RESULT:
- command:
- before:
- after:
- remaining_in_scope:
- remaining_out_of_scope:

ROUTE_STATE:
- scope: type_check_run
- terminal_for_current_scope: true | false

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

NEXT_ACTION:
- command: <exact command or none>
- reason:
- expected_result:
- return_fields:

DO_NOT_RUN:
```

Без `GO` поля `TYPECHECK_RESULT.after` / исправленные counts могут быть `n/a` / `not_run`.

Фрагменты `SOURCE_RESOLUTION` и `EXECUTION_PREFLIGHT` — из shared contracts (ссылка, не копия полного текста). При raw paste без `path=` допустимо `mode: referenced_source`, `primary_path: inline_raw_output`.

`DO_NOT_RUN` перечисляет запрещённые следующие шаги (массовый refactor, suppressions, правка out-of-scope, `/opsx-test` для typing, и т.п.).

Опционально, только когда out-of-scope debt остался при зелёном current scope:

```text
OPTIONAL_BACKLOG:
- summary:
- files:
```

`OPTIONAL_BACKLOG` никогда не заменяет `NEXT_ACTION` (для terminal scope `NEXT_ACTION.command` = `none`).

## Acceptance anchors (contract check)

Команда должна корректно вести себя минимум на:

1. один Pyright error в изменённом файле → `caused_by_current_diff`, `fix_now`, `GO_ELIGIBLE=true`;
2. смешанный output: current diff + старый debt → раздельные groups / dispositions;
3. повторяющиеся/искажённые terminal lines → `duplicate_diagnostic`, unique count < raw count;
4. missing file path → `missing_source_path`, часто `blocked` или group out of apply;
5. unnecessary cast → минимальный fix = remove cast;
6. `list[Unknown]` в Pydantic models → уточнение annotation / `default_factory` typing;
7. ошибка исчезла после GO → `remaining_in_scope=0`, `NEXT_ACTION: none`;
8. out-of-scope debt остался, текущий scope зелёный → `terminal_for_current_scope=true`, backlog ≠ NEXT_ACTION;
9. после typing fix найден behavioral defect → `NEXT_ACTION: /opsx-fix-bug` без GO;
10. пользователь вставил Mypy output без `tool=` → tool выводится из output, повторный ввод не требуется.

## Guardrails

- Не исправляй typing без `GO` + `fix_now`.
- Не превращай команду в общий linter.
- Не дублируй полный lifecycle `/opsx-fix-bug`.
- Не меняй семантику `/opsx-test`.
- Не объявляй `fixed`, пока in-scope diagnostics остаются на exact original command.
- Одна `NEXT_ACTION.command` на ответ.
