# T5 — continue / ff equivalence

## Given

Identical upstream artifacts for a Change (proposal, specs, design,
decisions, owner-contract as applicable).

## When

`tasks.md` is generated once via `/opsx-continue` and once via `/opsx-ff`
(or dry-run against the same readiness contract).

## Expected

```text
semantically equivalent tasks
same TASK_GENERATION_READINESS outcome
same BLOCKED reasons / same READY task obligations
advancement mode differs only
```

## Forbidden

```text
continue-only vs ff-only divergent task rules
different modality or evidence-role treatment per command
```
