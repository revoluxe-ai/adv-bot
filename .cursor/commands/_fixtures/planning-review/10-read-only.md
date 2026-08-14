# Fixture T10 — READ_ONLY

## Given

Any of T1–T9 (PASS, REPAIR_REQUIRED, NEEDS_OWNER, or BLOCKED).

## Expected

```text
MODE: READ_ONLY
FILES_CHANGED: none
```

No planning artifact, contract, or fixture mutation by the reviewer.
Applies to all terminal statuses.
