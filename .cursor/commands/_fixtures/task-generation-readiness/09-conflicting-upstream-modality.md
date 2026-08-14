# T5 — conflicting upstream modality

## Given

Authoritative upstream sources disagree on the same observable:

```text
design: Auto MUST start
spec: Auto MAY start
```

## When

Generator runs `TASK_GENERATION_READINESS` before write.

## Expected

```text
UPSTREAM_NORMATIVE_CONFLICTS: present
TASKS_STATUS: BLOCKED
REASON: UPSTREAM_NORMATIVE_CONFLICT
CONFLICT: design MUST vs spec MAY
FILES_CHANGED: none
```

## Forbidden

```text
model-selected compromise (e.g. soft MAY / SHOULD)
TASKS_STATUS: READY with either wording silently chosen
```
