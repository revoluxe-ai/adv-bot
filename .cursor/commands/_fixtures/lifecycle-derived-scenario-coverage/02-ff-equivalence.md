# T2 — ff equivalence

## Given

Same reviewed Owner Contract + same repository state as a sequential
`/opsx-new` → `/opsx-continue`* path that produced a Derived Lifecycle.

## When

Artifacts are built via `/opsx-ff` instead.

## Expected

```text
LIFECYCLE_STATUS: DERIVED
lifecycle/design/spec semantically equivalent to sequential continue path
advancement mode differs only; semantic rules identical
no CONFIRM_LIFECYCLE on unambiguous derivation
```
