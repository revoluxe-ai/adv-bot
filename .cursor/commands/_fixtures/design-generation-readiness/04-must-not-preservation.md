# T4 — MUST NOT modality preserved in design

## Given

Authoritative upstream:

```text
if another blocker remains
→ Auto MUST NOT force-start
```

## When

Generator writes clear-our-block / resume behavior in design.

## Expected

```text
design preserves: MUST NOT force-start
  (or equivalent prohibition)
DESIGN_STATUS: READY
```

## Forbidden

```text
MAY force-start when convenient
SHOULD NOT force-start (weakening)
MUST NOT → SHOULD NOT
```
