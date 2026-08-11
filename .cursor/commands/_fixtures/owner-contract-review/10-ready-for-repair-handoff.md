# Fixture 10 — T4 all questions resolved, contract still wrong

## Given

```text
Durable OWNER_INTENT + OWNER_DECISIONS available.
All OWNER_INPUT_REQUIRED: YES findings answered in this review cycle
  (or no such findings).
owner-contract.md still contains ≥1 proven semantic defect
  (e.g. Fixture 09 stale acceptance + missing Best-plan-only bullet).
```

## Expected

```text
REVIEW_STATE: READY_FOR_REPAIR
VERDICT: READY_FOR_REPAIR

OWNER_REVIEW_HANDOFF present with:
  CHANGE_ID
  REVIEW_SOURCE
  CONFIRMED_OWNER_DECISIONS   # full semantics, including cycle answers
  REPAIRS_REQUIRED            # R-00N with REQUIRED_SEMANTICS
  DO_NOT_CHANGE
  REPAIR_BOUNDARY
  REPAIR_COMMAND: /opsx-new
  AFTER_REPAIR: /opsx-owner-contract-review change=<change>

must NOT tell Owner to manually edit owner-contract.md
must NOT say "Owner + owning writer"
MODE: READ_ONLY
FILES_CHANGED: none
```

## Optional Finding C (Best plan only)

If durable Owner confirmation for «Best plan only» exists but bullet is
missing under `## Решения Owner`:

```text
OWNER_INPUT_REQUIRED: NO
REPAIR_REQUIRED: YES
```

Do not re-ask Owner.
