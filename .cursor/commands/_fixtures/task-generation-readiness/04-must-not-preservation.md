# T2 — MUST NOT modality preserved

## Given

Upstream requirement:

```text
other blocker remains
→ Auto MUST NOT be force-started
```

## When

Generator decomposes that requirement into a task line, then runs
post-generation `NORMATIVE_PRESERVATION_CHECK`.

## Expected

```text
task text contains: MUST NOT
(e.g. Auto MUST NOT be force-started / MUST NOT forced start)
NORMATIVE_MODALITY_PRESERVED: yes
TASKS_STATUS: READY
```

## Forbidden

```text
SHOULD NOT force start
MAY NOT force start
MUST NOT → SHOULD NOT / MAY weakening
```
