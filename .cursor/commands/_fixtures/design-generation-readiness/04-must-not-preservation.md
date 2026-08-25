# T4 — MUST NOT modality preserved in design

## Given

Authoritative upstream:

```text
if another blocker remains
→ Auto MUST NOT force-start
```

## When

Generator writes clear-our-block / resume behavior in design, then runs
post-generation `NORMATIVE_PRESERVATION_CHECK`.

## Expected

```text
design preserves: MUST NOT force-start
  (or equivalent prohibition)
NORMATIVE_MODALITY_PRESERVED: yes
DESIGN_STATUS: READY
```

## Forbidden

```text
MAY force-start when convenient
SHOULD NOT force-start (weakening)
MUST NOT → SHOULD NOT
```
