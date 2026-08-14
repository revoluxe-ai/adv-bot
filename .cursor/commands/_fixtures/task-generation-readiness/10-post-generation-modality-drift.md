# T6 — post-generation modality drift catch

## Purpose

Key regression: preflight that only scans upstream MUST NOT miss drift
created by the generator itself.

## Given

Upstream (unambiguous):

```text
A → MUST B
UPSTREAM_NORMATIVE_CONFLICTS: none
```

Intentional bad draft task (simulating generator paraphrase):

```text
A → MAY B
```

## When

Post-generation `NORMATIVE_PRESERVATION_CHECK` runs on the draft.

## Expected

```text
NORMATIVE_MODALITY_PRESERVED: no
TASKS_STATUS: BLOCKED
REASON: NORMATIVE_MODALITY_DRIFT
DRIFT: MUST B → MAY B
FILES_CHANGED: none
```

## Forbidden

```text
UPSTREAM_NORMATIVE_CONFLICTS: none
TASKS_STATUS: READY
```

with the weakened draft written to `tasks.md`.
