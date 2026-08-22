# T6 — scenario invented semantics

## Given

- Derived Lifecycle + Owner Contract do not authorize behavior X
- Spec contains a Scenario that introduces behavior X

## When

`/opsx-spec-scenario-coverage mode=plan|audit`

## Expected

```text
GAP / FAIL class: SEMANTIC_DRIFT
not PASS
REPAIR_TARGET: spec (or planning coherence via /opsx-update)
```

## Forbidden

- Treating invented Spec behavior as covered lifecycle
- Asking Owner to “confirm” the invented Scenario as if it were Owner intent
