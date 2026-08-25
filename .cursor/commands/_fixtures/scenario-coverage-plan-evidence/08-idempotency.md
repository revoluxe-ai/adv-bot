# T8 — idempotency

## Given

Unchanged authoritative inputs; prior CURRENT pair already matches.

## When

`mode=plan` run twice.

## Expected

```text
same semantic plan
same PLAN_EVIDENCE_ID / PLAN_CONTENT_HASH
MATERIALIZATION_STATUS: ALREADY_CURRENT (or equivalent)
no duplicate competing CURRENT evidence
```
