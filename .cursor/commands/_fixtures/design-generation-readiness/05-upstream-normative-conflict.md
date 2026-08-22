# T5 — upstream normative conflict blocks design

## Given

Two authoritative upstream artifacts conflict:

```text
SOURCE_A (owner-contract): Auto MUST start when our block clear
  AND no other blockers
SOURCE_B (decision): Activity-control MAY start Auto …
```

## When

Design generator would have to choose one modality.

## Expected

```text
DESIGN_STATUS: BLOCKED
REASON: UPSTREAM_NORMATIVE_CONFLICT
SOURCE_A: …
SOURCE_B: …
```

No silent compromise wording. No READY design that picks the convenient
modality.

## Forbidden

```text
DESIGN_STATUS: READY
with model-selected MAY (or SHOULD) compromise
```
