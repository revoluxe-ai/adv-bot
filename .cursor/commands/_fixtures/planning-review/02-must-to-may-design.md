# Fixture T2 — MUST → MAY in design

## Given (authoritative upstream)

```text
owner-contract / lifecycle:
clear our block + no remaining blockers
→ Auto MUST start
```

## And (design.md)

```text
Decision: Activity-control MAY start Auto if no other blockers.
DESIGN_STATUS: READY
NORMATIVE_MODALITY_PRESERVED: yes
```

## And (tasks.md)

```text
Auto MAY start when only our block cleared.
TASKS_STATUS: READY
```

## Expected

```text
STATUS: REPAIR_REQUIRED
TYPE: NORMATIVE_DRIFT
FIRST_BAD_ARTIFACT: design.md
AFFECTED_DOWNSTREAM: tasks.md
OWNER_INPUT_REQUIRED: NO
APPLY_PLANNING_GATE: FAIL
FILES_CHANGED: none
```

Handoff MUST target `/opsx-update` with repair of design first, then
stale tasks — not tasks-only patch.
