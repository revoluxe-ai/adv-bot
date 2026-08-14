# T2 — legacy baseline vs target regression

## Given

Change intentionally removes existing behavior:

```text
CURRENT:
  A → pause

TARGET:
  A → MUST NOT pause
```

## When

Generator creates test-related tasks for `tasks.md`.

## Expected

```text
LEGACY_BASELINE task: proves CURRENT A → pause (pre-change)
TARGET_REGRESSION task: asserts A → MUST NOT pause
FINAL_ACCEPTANCE (optional): end-state target holds
TASKS_STATUS: READY
```

## Forbidden

```text
require CURRENT characterization assertion to remain green after change
OLD behavior MUST happen AND OLD behavior MUST NOT happen
```
