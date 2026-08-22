# Fixture 04 — T8 DO_NOT_CHANGE preservation

## Given

```text
Valid REPAIR handoff with:
  REPAIRS_REQUIRED: R-001 touches section A (e.g. acceptance stale auto-restart)
  DO_NOT_CHANGE: includes confirmed semantics in other sections
    (e.g. Best plan only; clear block ≠ forced Auto start; per-tick recheck)
```

## Expected

```text
R-001 applied (REQUIRED_SEMANTICS present in owner-contract.md)
every DO_NOT_CHANGE item still true after write
no unrelated section rewritten for polish
OTHER_FILES_CHANGED: none
NEW_PRODUCT_DECISIONS_INTRODUCED: none
```
