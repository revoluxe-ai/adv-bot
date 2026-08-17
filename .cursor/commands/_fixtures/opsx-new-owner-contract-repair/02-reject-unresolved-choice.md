# Fixture 02 — T6 reject unresolved semantic choice

## Given

```text
Valid-looking OWNER_REVIEW_HANDOFF shell, but some R-* has:
  REQUIRED_SEMANTICS that asks writer to choose A vs B
  OR OWNER_INPUT_REQUIRED: YES
  OR ambiguous unresolved fork
```

## Expected

```text
PAUSE
UNRESOLVED_SEMANTIC_CHOICE
(or INVALID_REPAIR_HANDOFF naming the R-*)

FILES_CHANGED: none
must NOT pick A or B
must NOT write owner-contract.md
must NOT create schema artifacts
```
