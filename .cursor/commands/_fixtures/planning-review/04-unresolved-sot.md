# Fixture T4 — unresolved SoT

## Given (design.md)

```text
DESIGN_STATUS: READY
DURABLE_SOT_RESOLVED: yes

Body:
"PG or Redis — choose during apply"
```

## Expected

```text
STATUS: REPAIR_REQUIRED | BLOCKED
TYPE: DESIGN_READINESS_GAP
  (and/or AUTHORITY_OR_SOT_GAP)
APPLY_PLANNING_GATE: FAIL
Never: PASS
FILES_CHANGED: none
```

Prefer `REPAIR_REQUIRED` when repository evidence already selects one SoT
for update repair; `BLOCKED` / `NEEDS_OWNER` only if product choice truly
unresolved.
