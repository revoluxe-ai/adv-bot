# T1 — unresolved durable SoT blocks design

## Given

Change requires durable state. Generator cannot determine PG vs Redis
(or equivalent store) from repository evidence / decisions.

```text
durable pause-block / epoch / due SoT = PG | Redis
(evidence insufficient)
```

## When

`/opsx-continue` or `/opsx-ff` is about to complete `design.md`.

## Expected

```text
DESIGN_READINESS
DURABLE_SOT_RESOLVED: <not yes>
DESIGN_STATUS: BLOCKED
REASON: TECHNICAL_DESIGN_UNRESOLVED
UNRESOLVED: <exact SoT fork>
EVIDENCE_MISSING: <gap>
```

Design MUST NOT be reported complete. Downstream MUST NOT see false
«design complete».

## Forbidden

```text
DESIGN_STATUS: READY
Точная схема PG/Redis — apply-time
PG vs Redis — выбрать в apply
```
