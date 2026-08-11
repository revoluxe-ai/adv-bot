# T10 — body/receipt integrity

## Given

`plan.md` modified without updating `plan.receipt.json` /
`PLAN_CONTENT_HASH`.

## When

Consumer integrity check.

## Expected

```text
EVIDENCE_INTEGRITY_FAIL
MUST NOT trust receipt pointing to changed content
```
