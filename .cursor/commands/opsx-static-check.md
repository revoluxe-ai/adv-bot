---
description: "Единая read-only точка статических проверок: MODE=FULL|FAST; parallel Task workers; сводный отчёт."
argument-hint: "[FAST|FULL] [PREFLIGHT]"
---

# /opsx-static-check

Единая точка статических проверок.

Оркестратор читает registry, запускает Task workers параллельно (fan-out), собирает packets (fan-in), синтезирует пересечения и печатает STATUS + PROBLEMS + один NEXT_ACTION.

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
- **Completion gate:** run считается незавершённым, пока **оркестратор** не
  напечатал блок Final report (`STATUS` + `CHECKS` + `NEXT ACTION`) в **своём**
  ответе пользователю. Не финальный ответ:
  - «жду packets» / progress / `WORKER READY` alone;
  - system notification о завершении Task/subagent;
  - сырой worker packet / `RAW_TAIL` субагента (в т.ч. в Agent Team UI).
  Notification «pytest-* FAIL» **≠** Final report. После закрытия последней
  wave оркестратор **в том же ходе** (сразу после записи последнего packet)
  обязан сделать fan-in → synthesis → Final report — нельзя «просто остановиться».

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

### 3. Fan-out (from registry waves)

**Primary launch (mandatory):** Task tool with `subagent_type` = registry
`task_type` (short checks: `shell`; long suite waves `pytest-unit` /
`pytest-integration` / `pytest-destructive`: `generalPurpose` — shell Task
often Agent-Loops / silent-stalls before pytest starts).

- Read prompt template from `.cursor/static-check/base/worker-prompt.md`.
- Fill REPO_ROOT / MODE / CHECK_ID; load packs via that template.
- Invoke tools only via `bash .cursor/static-check/bin/run.sh -- …` (see `base/shell.md`).
- Do **not** invent `bash -lc 'source ...; cmd'`.
- Do **not** attempt custom project agent names (`opsx-sc-*` or any non-Task-enum id) — they are invalid for Task and must not be tried first.

If registry `task_type` is unavailable in the live Task enum → launch with
`generalPurpose` and the **same** prompt. Never invent undeclared tool wrappers.

**Launch-infra retry (exactly one Task retry per CHECK_ID):** treat as
launch-infra failure (not a pytest FAIL) and retry once via Task
`generalPurpose` with the same prompt (see `base/worker-prompt.md`) when ANY of:

- first Task finishes with no parseable worker packet;
- Agent Looping / repeating-pattern abort, or Task error without packet body;
- **silent stall** (pre-completion): CHECK_ID still in-flight with no
  parseable packet, owner reports hang/завис/стоп-воркера (or orchestrator
  probes after that signal), **and** evidence shows no matching
  `pytest`/`run.sh` for that check and/or Task transcript is only the initial
  prompt (no command output). Interrupt/abandon the open Task if still open,
  emit `WORKER RETRY`, then the one GP Task retry.

Use the retry packet if valid. Never more than one Task retry.

**Orchestrator-direct fallback (exactly one, after Task budget exhausted):**
if the one Task launch-infra retry is exhausted **and** the suite/check never
started (no parseable packet; no matching `pytest`/`run.sh` / command
output) → orchestrator runs **once** via its own Shell tool:
`bash .cursor/static-check/bin/run.sh -- <canonical command from instructions>`,
synthesizes a worker packet from exit code + tail, continues cascade.
Emit `WORKER DIRECT: <check_id> → orchestrator-shell`. This is **not** a
second Task retry and not a product FAIL path. If orchestrator-direct also
fails to start/finish → `STATUS=ERROR` for that check.

**Not** launch-infra / not orchestrator-direct (do not retry for these):

- matching `pytest`/`run.sh` is alive (e.g. PG/`DROP SCHEMA` lock hang) →
  env / concurrent-suite issue;
- owner `STOP_RUN` / abort of the entire `/opsx-static-check` → no retry;
  Final report with ERROR/SKIPPED as appropriate.

Task prompt MUST match `base/worker-prompt.md` (required body).

Progress:

```text
WORKER READY: <check_id> → <STATUS> (findings=<n>)
WORKER RETRY: <check_id> → generalPurpose (launch-infra)
WORKER DIRECT: <check_id> → orchestrator-shell
```

Pytest cascade (registry waves; hard stop on FAIL|BLOCKED|ERROR):

1. Wave A parallel: `pyright-strict`, `mypy`, `pytest-targeted`
2. Wave U `pytest-unit` — only if `pytest-targeted` STATUS=PASS
3. Wave I `pytest-integration` — only if `pytest-unit` STATUS=PASS
4. Wave D `pytest-destructive` — MODE=FULL only; only if
   `pytest-integration` STATUS=PASS (set ALLOW_* per pack). Never in FAST.

If a pytest gate fails → mark later pytest checks `SKIPPED` and continue to
synthesis (typing packets from Wave A still fan-in). Do **not** `--deselect`
dirty paths from suite waves. Do **not** launch retired `pytest-full` / bare
`poetry run pytest`.

### 4. Fan-in + synthesize

Follow `.cursor/static-check/contracts/synthesis.md` (SoT: STATIC/TESTS
buckets, intersection dedupe, actionable group fields, ≤ half-chat PROBLEMS
budget, TRUNCATED/OMITTED_GROUPS).
Update checkboxes from packets.
Do not edit repo files while synthesizing.
Do not paste worker RAW_TAIL or full FINDINGS into the Final report.

When the **last open check** of the run completes (final scheduled pytest
wave packet, or earlier when later waves are SKIPPED): **immediately**
synthesize and go to §5 — do not end the turn with only `WORKER READY`.

Mass `severity` / setup ERROR with the same root cause → one PROBLEMS group
with `count`, not a dump of every node id (see synthesis.md).

### 5. Final report

**Mandatory artifact of every completed `/opsx-static-check` run** (PASS, FAIL,
or BLOCKED). Print the full template below even when Team/UI already showed a
red subagent.

```text
STATUS: PASS | FAIL | BLOCKED
MODE: FULL | FAST
PREFLIGHT: off|on|skipped|failed
CHECKS:
- <id>: PASS|FAIL|SKIPPED|BLOCKED|ERROR (command: ...)
SUMMARY:
- passed/failed/skipped checks
- static_findings / test_findings / findings_total
- problem_groups / truncated / omitted_groups
PROBLEMS:
### STATIC
#### P1. <short title>
- path: <filepath:line>   # or <filepath> if line unknown
- count: <n>
- top: <≤2 codes>
- fix_target: <one line — file:line/symbol>
- fix_cmd: /opsx-fix-types
- seen_in: [...]
### TESTS
#### P2. <short title>
- node: <pytest node id>
- count: <n>
- top: <≤2 assert summaries>
- fix_target: <one line — test/fixture>
- fix_cmd: /opsx-test-triage
- seen_in: [...]
TRUNCATED: yes|no
OMITTED_GROUPS: <n>
NEXT ACTION:
<one step for the human; never "I will patch run.sh now">
```

Error UX: Problem / Cause / Action (never bare FAILED).
Budgets, dedupe, `fix_cmd` mapping, and single NEXT_ACTION rank: only in
`contracts/synthesis.md` — do not weaken them here.

## Human checklist

- PREFLIGHT off unless explicitly requested?
- No self-repair of command/infra during this run?
- Fan-out via registry `task_type` (shell short / GP suite waves) — no custom agent names?
- Launch-infra: one Task GP retry on empty packet / Agent Looping / silent stall;
  then orchestrator-direct once if suite never started?
- Registry-driven waves?
- Final report printed by orchestrator (not only worker notification)?
- One NEXT_ACTION?
