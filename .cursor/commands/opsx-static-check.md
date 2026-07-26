---
description: "Единая read-only точка статических проверок: MODE=FULL|FAST; parallel Task workers; сводный отчёт."
argument-hint: "[FAST|FULL] [PREFLIGHT]"
---

# /opsx-static-check

Единая точка статических проверок.

Оркестратор читает registry, запускает Task workers параллельно (fan-out), **ждёт все packets**, синтезирует пересечения и печатает STATUS + PROBLEMS + один NEXT_ACTION.

SoT инфраструктуры: `.cursor/static-check/`.
Методология расширения: skill `opsx-static-check-infra` (не во время обычного check-run).

## Язык

Пояснения — на русском. Токены STATUS/MODE/CHECK_ID/пути — на английском.

## User input

```text
$ARGUMENTS
```

Разбор токенов (порядок свободный):

| Token | Effect |
|-------|--------|
| (нет MODE) / `FULL` | `MODE=FULL` |
| `FAST` | `MODE=FAST` |
| `PREFLIGHT` | run optional env preflight before fan-out |
| иное неизвестное | `STATUS=BLOCKED`, не запускать agents |

Примеры:

- `/opsx-static-check` → FULL, **без** preflight
- `/opsx-static-check FAST` → FAST, без preflight
- `/opsx-static-check FULL PREFLIGHT` → FULL + preflight
- `/opsx-static-check PREFLIGHT FAST` → FAST + preflight

## Purpose / boundaries

Read-only quality gate. Не заменяет `/opsx-verify`, `/opsx-fix-types`, `/opsx-test-triage`, targeted gates в `/opsx-apply`.

### Hard rules (абсолютно)

- **READ_ONLY end-to-end:** не изменять никакие файлы репозитория.
- Запрещено «чинить» даже инфраструктуру check-команды: `.cursor/commands/opsx-static-check.md`, `.cursor/static-check/**`, skills/rules этой подсистемы, `bin/run.sh`, configs.
- Не автофиксить production/tests.
- Не объявлять archive `GO`/`NO_GO`.
- Не создавать durable artifacts по умолчанию.
- При BLOCKED/FAIL: только отчёт + NEXT ACTION для **человека** / другой команды. **Этот** run ничего не патчит.
- **Completion gate:** run незавершён, пока не напечатан Final report (`STATUS` + `CHECKS` + `NEXT ACTION`). «Жду packets» — не финальный ответ.

Shared contracts: `.cursor/commands/opsx-source-resolution.md`, `.cursor/commands/opsx-execution-preflight.md` (общий opsx preflight ≠ optional PREFLIGHT этой команды).

## Steps

### 1. Load registry

Read `.cursor/static-check/registry.yaml` and `.cursor/static-check/contracts/synthesis.md`.

Announce:

```text
STATIC CHECK
MODE: FULL|FAST
PREFLIGHT: off|on
Parallel plan: <waves from registry>
Checks: [ ] ...
```

### 2. Optional PREFLIGHT (default OFF)

**По умолчанию шаг пропускается** (`PREFLIGHT: off`).

Выполнять `.cursor/static-check/base/preflight.md` **только** если в `$ARGUMENTS` есть точный токен `PREFLIGHT`.

Если `PREFLIGHT` задан и probe fail → STOP:

- `STATUS=BLOCKED`
- Problem / Cause / Action
- **не** запускать workers
- **не** править файлы

Если `PREFLIGHT` не задан → сразу fan-out.

### 3. Fan-out + WAIT (from registry waves)

**Primary launch (mandatory):** Task tool with `subagent_type` = registry `task_type` (default `shell`).

- Read prompt template from `.cursor/static-check/base/worker-prompt.md`.
- Fill REPO_ROOT / MODE / CHECK_ID; load packs via that template.
- Invoke tools only via `bash .cursor/static-check/bin/run.sh -- …` (see `base/shell.md`).
- Do **not** invent `bash -lc 'source ...; cmd'`.
- Do **not** attempt custom project agent names (`opsx-sc-*` or any non-Task-enum id).

If registry `task_type` unavailable in live Task enum → one fallback to `generalPurpose` with the **same** prompt.

Task prompt MUST match `base/worker-prompt.md`.

#### Parallel launch

- Wave с `parallel: true`: в **одном** turn запустить **все** checks волны (`run_in_background: true`).
- Держать чеклист `[ ] check_id` до packet каждого worker.

#### WAIT contract (обязательно)

1. После fan-out **нельзя** печатать Final report и нельзя считать команду сделанной.
2. «Жду packets…» — только progress, **не** terminal answer.
3. End turn после launch — только чтобы получить Task completion notifications (пауза ожидания, не конец команды).
4. На **каждое** notification/packet:
   - `WORKER READY: <id> → <STATUS> (findings=<n>)`;
   - отметить checkbox;
   - волна неполная → продолжать ждать (не спрашивать пользователя);
   - волна полная → **сразу** в том же turn: Wave B (если надо) или fan-in + Final report.
5. Запрещено бросать chat после частичных READY и ждать пинка от пользователя.
6. Wave B не стартует, пока Wave A checklist не закрыт.

Progress:

```text
WORKER READY: <check_id> → <STATUS> (findings=<n>)
```

Wave B (`pytest-full`) только если `pytest-unit` STATUS=PASS. Иначе `pytest-full: SKIPPED` → synthesis.
Wave B тоже под WAIT: без packet/SKIPPED Final report не печатать.

### 4. Fan-in + synthesize

Follow `.cursor/static-check/contracts/synthesis.md`.
Update checkboxes from packets.
Do not edit repo files while synthesizing.

### 5. Final report

```text
STATUS: PASS | FAIL | BLOCKED
MODE: FULL | FAST
PREFLIGHT: off|on|skipped|failed
CHECKS:
- <id>: PASS|FAIL|SKIPPED|BLOCKED|ERROR (command: ...)
SUMMARY:
- passed/failed checks, findings total, problem groups, truncated, omitted_groups
PROBLEMS:
### P1. ...
NEXT ACTION:
<one step for the human; never "I will patch run.sh now">
```

Error UX: Problem / Cause / Action (never bare FAILED).

## Human checklist

- PREFLIGHT off unless explicitly requested?
- No self-repair of command/infra during this run?
- Fan-out via Task `shell` (registry `task_type`) — no custom agent names?
- Waited for **all** wave packets before Final report (no early chat stop)?
- Registry-driven waves?
- One NEXT_ACTION?
