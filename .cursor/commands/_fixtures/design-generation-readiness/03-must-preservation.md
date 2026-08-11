# T3 — MUST modality preserved in design

## Given

Authoritative upstream (owner-contract / spec):

```text
if our block cleared AND no other blockers
→ Auto MUST start
```

## When

Generator writes the corresponding design decision / lifecycle step.

## Expected

```text
design text contains: Auto MUST start
  (or equivalent MUST start wording)
DESIGN_STATUS: READY
NORMATIVE_CONFLICTS: none
```

## Forbidden

```text
Activity-control MAY start Auto …
Auto SHOULD start
MUST → MAY weakening
```
