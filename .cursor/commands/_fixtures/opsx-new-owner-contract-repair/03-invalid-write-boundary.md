# Fixture 03 — T7 invalid write boundary

## Given

```text
OWNER_REVIEW_HANDOFF asks to edit any of:
  proposal.md / design.md / tasks.md / specs/** / decisions/**
  code / tests / evolution / explore artifacts
OR WRITE_BOUNDARY is not limited to owner-contract.md only
```

## Expected

```text
PAUSE
INVALID_REPAIR_BOUNDARY
(or DEPENDENCY_FOUND if repair truly requires another artifact)

FILES_CHANGED: none
OTHER_FILES_CHANGED: none
must NOT expand write scope
must NOT partially edit owner-contract.md and claim success
```
