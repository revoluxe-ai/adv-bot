# Fixture 12 — T6 writer regression after repair

## Given

```text
Prior OWNER_REVIEW_HANDOFF:
  REPAIRS_REQUIRED: R-001 applied successfully
  DO_NOT_CHANGE:
    - clear-our-block-only semantics
    - Best plan only (confirmed)

After /opsx-new:
  R-001 fixed
  BUT DO_NOT_CHANGE item altered (e.g. Best plan only removed or
  clear-our-block-only rewritten to unconditional Auto start)
```

## Expected

```text
REVIEW_STATE: READY_FOR_REPAIR | NEEDS_OWNER
must NOT be PASS

new finding for the DO_NOT_CHANGE regression
bounded repair cycle → new OWNER_REVIEW_HANDOFF if semantics known
  (OWNER_INPUT_REQUIRED: NO + REPAIR_REQUIRED: YES)
or NEEDS_OWNER only if regression introduced a new real product fork

MODE: READ_ONLY
FILES_CHANGED: none
```

## Why

Re-review must detect writer regressions on confirmed semantics and start a
new bounded cycle — not dump recovery onto Owner.
