---
description: "Audit committed or dirty-worktree production Python against pyrightconfig_strict.json include/exclude so changed code is actually covered by pyright-strict."
argument-hint: "base=<branch|ref> [head=<ref>|working] [GO]"
---

# /opsx-pyright-strict-coverage

Проверь, что весь **in-policy** production Python из `base...target` попал в
`pyrightconfig_strict.json` `include` и не вырезан `exclude`.

Цель: нельзя «пройти» `pyright-strict` / `/opsx-static-check`, если новый или
изменённый production-код просто отсутствует в allowlist.

## What this is

* Coverage audit: branch diff ⊆ strict-include (minus exclude).
* Рекомендуемый шаг **после** `/opsx-apply`, **до**
  `/opsx-external-call-coverage`, conditional `/opsx-performance-review`,
  `/opsx-static-check` и `/opsx-verify`,
  когда в сессии/diff есть production `.py`.
* Опционально `GO`: только **additive** записи в `include[]`.

## What this is NOT

* NOT запуск `pyright-strict` (→ `/opsx-static-check`).
* NOT разбор/фикс typing diagnostics (→ `/opsx-fix-types`).
* NOT archive / adequacy verdict (→ `/opsx-verify`).
* NOT ослабление `typeCheckingMode`, удаление `exclude`, suppressions.
* NOT external-call / integration coverage (→ `/opsx-external-call-coverage`).
* NOT performance review (→ `/opsx-performance-review`).
* NOT `/opsx-project-bug-hunt` и не product-bug triage.

## User input

```text
$ARGUMENTS
```

Токены (порядок свободный):

| Token | Effect |
|-------|--------|
| `base=<ref>` | обязательный comparison base (branch/tag/commit) |
| `head=<ref>` | optional immutable comparison target |
| `head=working` | explicit dirty-worktree target |
| `GO` | разрешить additive update `include[]` по `MISSING_FROM_INCLUDE` |
| иное неизвестное | `STATUS=BLOCKED`, не менять файлы |

Примеры:

- `/opsx-pyright-strict-coverage base=main`
- `/opsx-pyright-strict-coverage base=origin/main head=HEAD`
- `/opsx-pyright-strict-coverage base=origin/main head=working`
- `/opsx-pyright-strict-coverage base=main GO`

## Required input

Если `base=` отсутствует или ref не резолвится → `STATUS=BLOCKED`.

Спроси один раз:

```text
На какую base branch/ref сверять coverage?
Пример: /opsx-pyright-strict-coverage base=main
```

Не выдумывай base.

## Modes

### Default (no `GO`) — READ_ONLY

* Не менять репозиторий.
* Только отчёт + pasteable `NEXT_ACTION`.
* Если `head=` не задан, target по умолчанию — текущий `WORKTREE`, а не
  committed `HEAD`; staged, unstaged и релевантные untracked in-policy paths
  должны попасть в audit.

### `GO`

Только после полного READ_ONLY pass в том же чате (или явного replay списка
`MISSING_FROM_INCLUDE`):

* Добавить в `pyrightconfig_strict.json` → `include` **минимальные** пути
  из `SUGGESTED_INCLUDE_ENTRIES`.
* Не трогать `exclude`, `typeCheckingMode`, venv, pythonVersion.
* Не удалять существующие include-записи.
* После записи — повторный audit; затем рекомендовать `/opsx-static-check`.

Если `GO` есть, но `MISSING_FROM_INCLUDE` пуст → ничего не писать.

## Policy scope (in / out)

**In-policy** (должны быть covered):

* изменённые или добавленные `*.py` под `app/`;
* изменённые/добавленные top-level production scripts `*.py` в корне репо
  (например `updater.py`), если они есть в diff.

**Out-of-policy** (`OUT_OF_POLICY_SCOPE`, не требуют include):

* `tests/**`;
* `.cursor/**`, `openspec/**`, `docs/**`, `docks/**`, `k8s/**`;
* non-`.py` файлы;
* удалённые пути (delete) — include не нужен.

Rename/copy: проверяй **новый** путь (destination).

## Target resolution

1. Resolve `base` to an immutable commit.
2. Resolve target:
   - explicit `head=<ref>` → immutable ref target;
   - explicit `head=working` or omitted `head=` → current worktree target.
3. For the worktree target use the base-to-working diff, not
   `base...HEAD`; include staged and unstaged tracked changes, deletions, and
   relevant untracked in-policy files as added paths.
4. Report:

```text
AUDIT_TARGET: WORKTREE | REF
BASE_SHA: <sha>
TARGET_REF: WORKTREE | <sha>
WORKTREE_TRACKED_CHANGED: <n>
WORKTREE_UNTRACKED_IN_POLICY: <n>
WORKTREE_DELETED: <n>
```

5. A clean worktree target may be equivalent to `HEAD`, but the report must
   still state `AUDIT_TARGET: WORKTREE`. No commit is required for a
   read-only worktree re-audit.

## Matching rules

Нормализуй пути: relative to repo root, `/` separators, без ведущего `./`.

Путь `P` **covered** include-записью `I`, если:

1. `P == I`, или
2. `I` — directory-prefix: `P == I.rstrip('/')` или
   `P.startswith(I.rstrip('/') + '/')`.

Путь **HIT_EXCLUDE**, если аналогично матчится любой `exclude` entry
(даже при include match) → для coverage это **не** PASS по этому файлу;
disposition `HIT_EXCLUDE`.

`include` directory без trailing slash и с ним эквивалентны для prefix-match.

## Steps

1. Разобрать `base` / `head` / `GO` and resolve the target.
2. `git rev-parse` `base` and any explicit ref; при ошибке → `BLOCKED`.
3. Inventory the base-to-target changed paths, including relevant untracked
   worktree paths.
4. Прочитать `pyrightconfig_strict.json` (`include`, `exclude`).
5. Классифицировать каждый path:
   - skip non-in-policy;
   - skip deletes (`D`);
   - else evaluate COVERED / MISSING_FROM_INCLUDE / HIT_EXCLUDE.
6. Построить `SUGGESTED_INCLUDE_ENTRIES`:
   - предпочитай **file-level** path для одиночных файлов;
   - если в одном package-dir много новых файлов одного модуля — допускается
     одна directory entry (существующий стиль конфига);
   - не предлагай пути, уже covered;
   - не предлагай обход exclude через удаление exclude.
7. Без `GO`: только отчёт.
8. С `GO` и непустым `MISSING_FROM_INCLUDE`: additive write → re-audit.
9. Печать Final report (обязательный completion gate).

## Status

| STATUS | Когда |
|--------|--------|
| `PASS` | нет in-policy paths с `MISSING_FROM_INCLUDE` или `HIT_EXCLUDE` |
| `FAIL` | есть `MISSING_FROM_INCLUDE` и/или `HIT_EXCLUDE` |
| `BLOCKED` | нет/битый `base`, нет конфига, неизвестный token, git error |

`PASS` при нуле in-policy Python в diff — допустим (`nothing in policy scope`).

## Authority boundaries

* Не объявляй archive `GO` / `NO_GO`.
* Не подменяй `/opsx-static-check` и `/opsx-fix-types`.
* Не считай PASS coverage доказательством отсутствия typing errors.
* Recommendation после apply — soft; этот command не блокирует verify сам по себе.

## Final report (required)

```text
STATUS: PASS | FAIL | BLOCKED

BASE: <ref>
HEAD: <ref>
AUDIT_TARGET: WORKTREE | REF
BASE_SHA: <sha>
TARGET_REF: WORKTREE | <sha>
WORKTREE_TRACKED_CHANGED: <n>
WORKTREE_UNTRACKED_IN_POLICY: <n>
WORKTREE_DELETED: <n>
CONFIG: pyrightconfig_strict.json

IN_POLICY_CHANGED: <n>
COVERED: <n>
MISSING_FROM_INCLUDE: <n>
HIT_EXCLUDE: <n>
OUT_OF_POLICY_SCOPE: <n>

MISSING_FROM_INCLUDE:
- <path> ...

HIT_EXCLUDE:
- <path> (matched exclude: <entry>) ...

SUGGESTED_INCLUDE_ENTRIES:
- <path> ...

GO_APPLIED: false | true
INCLUDE_WRITTEN: none | <list>

WHAT_HAPPENED:
WHY:
CURRENT_STATE: coverage_pass | coverage_gaps | blocked_needs_base
OWNER_DECISION_REQUIRED: false | true (<what>)
NEXT_ACTION:
DO_NOT_DO_YET:
```

### NEXT_ACTION rules

* `BLOCKED` (no base) → pasteable ask for `base=`.
* `FAIL` без `GO` →  
  `/opsx-pyright-strict-coverage base=<BASE> GO`  
  **или** вручную добавить `SUGGESTED_INCLUDE_ENTRIES`, затем rerun без GO.
* `FAIL` с `HIT_EXCLUDE` only → owner must choose: move out of exclude
  (отдельное решение; **эта** команда с GO exclude не трогает) или
  вынести код из excluded path.
* `PASS` →  
  `/opsx-external-call-coverage base=<BASE>`
  затем conditional `/opsx-performance-review` (when trigger) →
  `/opsx-static-check` → `/opsx-verify <change-name>` если есть
  активный change.
* После успешного `GO` write → сначала rerun allowlist audit; при PASS →
  `/opsx-external-call-coverage base=<BASE>`; после external-call PASS →
  conditional performance-review → `/opsx-static-check`
  (новый include может вскрыть diagnostics → `/opsx-fix-types`).

### DO_NOT_DO_YET

* Не archive.
* Не считать `/opsx-static-check` PASS доказательством allowlist coverage,
  если этот audit не был PASS.
* Не ослаблять strictness / не `# type: ignore` ради закрытия gaps.

## Handoff

| From | To |
|------|-----|
| `/opsx-apply` (recommend) | this command with `base=` |
| this PASS | `/opsx-external-call-coverage` → conditional `/opsx-performance-review` → `/opsx-static-check` → `/opsx-verify` |
| this FAIL + diagnostics later | `/opsx-fix-types` after static-check |

## Regression checks (self)

- [ ] Без `base=` → `BLOCKED`, файлы не менялись
- [ ] Без `GO` → `pyrightconfig_strict.json` не менялся
- [ ] С `GO` → только additive `include[]`
- [ ] `tests/**` не попали в MISSING
- [ ] Не заявлен verify/archive verdict
- [ ] Final report напечатан
