# T2 — resolvable technical choice recorded in design

## Given

Repository evidence exposes an existing persistence pattern that satisfies
upstream durable-state semantics (e.g. adjacent activity-reason / shelf
state store). WHAT/SCOPE/ACCEPTANCE unchanged.

## When

Design generator resolves the technical fork.

## Expected

```text
DESIGN_STATUS: READY
design records:
- chosen SoT (store class)
- owner component
- write / read boundary
- recovery / how state is read after restart
- rationale / trade-off
DESIGN_READINESS
DURABLE_SOT_RESOLVED: yes
STATE_OWNERSHIP_RESOLVED: yes
WRITE_AUTHORITY_RESOLVED: yes
RECOVERY_SEMANTICS_RESOLVED: yes
IMPLEMENTATION_CRITICAL_OPEN_QUESTIONS: none
```

No Owner question for the pure technical choice.

## Forbidden

```text
Owner: confirm PG or Redis?
выбрать в apply
SoT TBD
```
