# T8 — continue / ff design equivalence

## Given

Identical upstream context (same owner-contract, specs, decisions,
repository evidence).

## When

`design.md` is generated via `/opsx-continue` **or** `/opsx-ff`.

## Expected

```text
semantically equivalent design
same DESIGN_READINESS outcome
  (including NORMATIVE_MODALITY_PRESERVED)
same SoT / ownership / write / recovery choices
same MUST / MUST NOT modality
```

Both commands cite `.cursor/pipeline/contracts/DESIGN_GENERATION.md` as
the single SoT. Advancement mode differs only.

## Forbidden

```text
continue-only vs ff-only divergent design rules
ff READY while continue would BLOCK (or reverse) on same input
post-generation check present in only one command
```
