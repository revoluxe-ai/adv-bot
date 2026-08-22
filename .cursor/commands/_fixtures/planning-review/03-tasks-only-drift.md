# Fixture T3 — tasks-only drift

## Given

Design + spec:

```text
Auto MUST start when our block cleared and no other blockers remain.
```

Tasks:

```text
Auto MAY start when our block cleared…
TASKS_STATUS: READY
NORMATIVE_MODALITY_PRESERVED: yes
```

## Expected

```text
STATUS: REPAIR_REQUIRED
TYPE: NORMATIVE_DRIFT | TASK_DECOMPOSITION_GAP
FIRST_BAD_ARTIFACT: tasks.md
OWNER_INPUT_REQUIRED: NO
FILES_CHANGED: none
```

Do not blame design when design/spec already preserve MUST.
