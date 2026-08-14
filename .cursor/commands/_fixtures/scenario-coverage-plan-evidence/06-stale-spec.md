# T6 — stale spec

## Given

Plan generated against spec B. Covered delta `spec.md` later becomes B2.

## When

Consumer freshness check.

## Expected

```text
STALE
same consumer refusal as T5
NEXT: /opsx-spec-scenario-coverage mode=plan
```
