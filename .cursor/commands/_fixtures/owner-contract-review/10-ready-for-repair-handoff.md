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

Human UX includes:
  "Скопируйте блок ниже в новый/Writer чат:"

Pasteable block starts with:
  /opsx-new

OWNER_REVIEW_HANDOFF present with literal fields:
  CHANGE_ID
  TARGET_WRITER: /opsx-new
  MODE: REPAIR_EXISTING_OWNER_CONTRACT
  REVIEWED_ARTIFACT
  OWNER_INTENT
  CONFIRMED_OWNER_DECISIONS   # full semantics, including cycle answers
  REPAIRS_REQUIRED            # R-00N with CURRENT_SEMANTICS / REQUIRED_SEMANTICS / EVIDENCE
  DO_NOT_CHANGE
  WRITE_BOUNDARY              # owner-contract.md only
  FORBIDDEN
  AFTER_REPAIR: /opsx-owner-contract-review change=<change>

must NOT use alternate field names:
  REPAIR_BOUNDARY / REPAIR_COMMAND / CURRENT_TEXT / REVIEW_SOURCE
must NOT tell Owner to manually edit owner-contract.md
must NOT say "Owner + owning writer"
must NOT require Owner to rewrite findings into a custom /opsx-new prompt

This handoff MUST be valid input for /opsx-new REPAIR MODE
  (see _fixtures/opsx-new-owner-contract-repair/07-handoff-from-reviewer-fixture-10.md)

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
