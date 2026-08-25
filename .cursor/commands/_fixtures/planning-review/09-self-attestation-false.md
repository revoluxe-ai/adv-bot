# Fixture T9 — self-attestation false

## Given

```text
NORMATIVE_MODALITY_PRESERVED: yes
DESIGN_STATUS: READY
TASKS_STATUS: READY
```

Body proves upstream `MUST start` weakened to `MAY start` in design
(and/or tasks).

## Expected

```text
STATUS: REPAIR_REQUIRED
TYPE: NORMATIVE_DRIFT
APPLY_PLANNING_GATE: FAIL
```

MUST NOT return PASS because markers say yes/READY.
`FILES_CHANGED: none`
