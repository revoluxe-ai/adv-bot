---
description: "Единая read-only точка статических проверок: MODE=FULL|FAST; parallel thin agents; сводный отчёт."
argument-hint: "[FAST|FULL]"
---

# /opsx-static-check

Единая точка статических проверок.

Оркестратор читает registry, запускает thin agents параллельно (fan-out), собирает packets (fan-in), синтезирует пересечения и печатает STATUS + PROBLEMS + один NEXT_ACTION.

SoT инфраструктуры: `.cursor/static-check/`.
Методология расширения: skill `opsx-static-check-infra`.

## Язык

Пояснения — на русском. Токены STATUS/MODE/CHECK_ID/пути — на английском.

## User input

```text
$ARGUMENTS
```

- пусто / `FULL` → `MODE=FULL`
- `FAST` → `MODE=FAST`
- иное → `STATUS=BLOCKED`, не запускать agents

## Purpose / boundaries

Read-only quality gate. Не заменяет `/opsx-verify`, `/opsx-fix-types`, `/opsx-test-triage`, targeted gates в `/opsx-apply`.

Hard rules:

- не менять файлы / не автофиксить;
- не объявлять archive `GO`/`NO_GO`;
- не дублировать tool details в этом файле — они в check packs;
- durable artifacts по умолчанию не создавать.

Shared contracts: `.cursor/commands/opsx-source-resolution.md`, `.cursor/commands/opsx-execution-preflight.md`.

## Steps

### 1. Load registry

Read `.cursor/static-check/registry.yaml` and `.cursor/static-check/contracts/synthesis.md`.

Announce:

```text
STATIC CHECK
MODE: FULL|FAST
Parallel plan: <waves from registry>
Checks: [ ] ...
```

### 2. Preflight

Repo root (`pyproject.toml`), `poetry` available, registry + agent files + packs exist.
Fail → `STATUS=BLOCKED` + Problem/Cause/Action + NEXT ACTION.

### 3. Fan-out (from registry waves)

For each check in the current wave, launch its **named project agent** from registry (`agent:` field) with `run_in_background: true` in **one parent message** for parallel wave members.

Task prompt MUST include:

```text
REPO_ROOT: <abs path>
MODE: FAST|FULL
CHECK_ID: <id>
Load packs listed in your agent file; return worker-packet only.
```

Progress as workers finish:

```text
WORKER READY: <check_id> → <STATUS> (findings=<n>)
```

Wave B (FULL `pytest-full`) starts only after `pytest-unit` completes (registry `after`).

Fallback: if Task/custom agents unavailable, say so and run packs sequential in-orchestrator with the same packet/synthesis contracts.

### 4. Fan-in + synthesize

Follow `.cursor/static-check/contracts/synthesis.md`.
Update checkboxes from packets.

### 5. Final report

```text
STATUS: PASS | FAIL | BLOCKED
MODE: FULL | FAST
CHECKS:
- <id>: PASS|FAIL|SKIPPED|BLOCKED|ERROR (command: ...)
SUMMARY:
- passed/failed checks, findings total, problem groups, truncated, omitted_groups
PROBLEMS:
### P1. ...
NEXT ACTION:
<one step>
```

Error UX: Problem / Cause / Action (never bare FAILED).

## Human checklist

- Registry-driven waves?
- Thin agents only (details in packs)?
- Intersections + budget?
- One NEXT_ACTION?
