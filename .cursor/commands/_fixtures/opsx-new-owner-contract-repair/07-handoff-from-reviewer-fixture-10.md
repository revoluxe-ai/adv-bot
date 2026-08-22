# Fixture 07 — T4↔T5 cross-contract: reviewer handoff is valid REPAIR input

## Given

```text
Output shape required by:
  .cursor/commands/_fixtures/owner-contract-review/10-ready-for-repair-handoff.md

Pasteable block:
  /opsx-new

  OWNER_REVIEW_HANDOFF
  CHANGE_ID: <change>
  TARGET_WRITER: /opsx-new
  MODE: REPAIR_EXISTING_OWNER_CONTRACT
  REVIEWED_ARTIFACT: ...
  OWNER_INTENT: ...
  CONFIRMED_OWNER_DECISIONS: ...
  REPAIRS_REQUIRED: ... (CURRENT_SEMANTICS / REQUIRED_SEMANTICS / EVIDENCE)
  DO_NOT_CHANGE: ...
  WRITE_BOUNDARY: owner-contract.md only
  FORBIDDEN: ...
  AFTER_REPAIR: /opsx-owner-contract-review change=<change>
```

## Expected

```text
/opsx-new accepts this block WITHOUT human rewriting / field renaming
enters REPAIR MODE
validates successfully when CHANGE_ID + owner-contract.md exist
and REPAIRS_REQUIRED are fully resolved

must NOT require Owner to adapt REVIEW_SOURCE / REPAIR_BOUNDARY /
  REPAIR_COMMAND / CURRENT_TEXT synonyms — those are forbidden aliases

Contract-level acceptance:
  output of owner-contract-review READY_FOR_REPAIR
  == valid input of opsx-new REPAIR MODE
```
