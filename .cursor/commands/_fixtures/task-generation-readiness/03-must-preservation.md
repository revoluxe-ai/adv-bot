# T3 — MUST modality preserved

## Given

Upstream spec requirement:

```text
if our block cleared AND no other blockers
→ Auto MUST start
```

## When

Generator decomposes that requirement into a task line.

## Expected

```text
task text contains: Auto MUST start
TASKS_STATUS: READY
```

## Forbidden

```text
Auto MAY start
Auto SHOULD start
MUST → MAY weakening
```
