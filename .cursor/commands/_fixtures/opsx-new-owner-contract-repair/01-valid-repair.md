# Fixture 01 — T5 valid REPAIR MODE

## Given

```text
Change CHANGE_ID exists.
openspec/changes/<CHANGE_ID>/owner-contract.md exists.
Input contains literal OWNER_REVIEW_HANDOFF with:
  TARGET_WRITER: /opsx-new
  MODE: REPAIR_EXISTING_OWNER_CONTRACT
  REPAIRS_REQUIRED: non-empty, fully resolved REQUIRED_SEMANTICS
  WRITE_BOUNDARY: owner-contract.md only
  FORBIDDEN: schema artifacts / reinterpret intent / new decisions
```

## Expected

```text
MODE: REPAIR_EXISTING_OWNER_CONTRACT
do NOT create new Change / recreate scaffold
do NOT create proposal/spec/design/tasks

FILES_CHANGED:
  openspec/changes/<CHANGE_ID>/owner-contract.md
OTHER_FILES_CHANGED: none

OWNER_CONTRACT_REPAIR_RESULT present with:
  REPAIRS_APPLIED listing each R-*
  REPAIRS_NOT_APPLIED: none
  NEW_PRODUCT_DECISIONS_INTRODUCED: none
  NEXT_ACTION: /opsx-owner-contract-review change=<CHANGE_ID>

must NOT emit independent review PASS from /opsx-new
```
