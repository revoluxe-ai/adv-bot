# Fixture 05 — T11 idempotency

## Given

```text
Same valid OWNER_REVIEW_HANDOFF already applied successfully once.
owner-contract.md already matches all REQUIRED_SEMANTICS.
Owner re-pastes the identical handoff into /opsx-new.
```

## Expected

```text
MODE: REPAIR_EXISTING_OWNER_CONTRACT
no duplicate bullets / sections
no broadened edits beyond REPAIRS_REQUIRED
resulting contract semantically equivalent to post-first-repair
REPAIRS_APPLIED may list R-* as already satisfied
OR REPAIRS_NOT_APPLIED: none with explicit already-satisfied note
OTHER_FILES_CHANGED: none
must NOT recreate scaffold / schema artifacts
```
