# T6 — implementation-critical Open Question fails readiness

## Given

Draft design leaves:

```text
## Open Questions
- PG vs Redis TBD
```

or equivalent SoT / ownership / write-authority question, while durable
state is required.

## When

`DESIGN_READINESS` is evaluated.

## Expected

```text
IMPLEMENTATION_CRITICAL_OPEN_QUESTIONS: <non-empty>
DESIGN_STATUS: BLOCKED
```

(or resolve the question into Decisions and clear Open Questions first).

## Forbidden

```text
DESIGN_STATUS: READY
with Open Questions holding PG|Redis / SoT / write authority
```
