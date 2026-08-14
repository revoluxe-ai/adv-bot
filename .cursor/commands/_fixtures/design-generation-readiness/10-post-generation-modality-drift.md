# T10 — post-generation modality drift catch (design)

## Purpose

Key regression: preflight that only scans upstream MUST NOT miss drift
created by the design generator itself.

## Given

Upstream (unambiguous):

```text
A → MUST B
NORMATIVE_CONFLICTS: none
```

Intentional bad draft design (simulating generator paraphrase):

```text
A → MAY B
```

## When

Post-generation `NORMATIVE_PRESERVATION_CHECK` runs on the draft.

## Expected

```text
NORMATIVE_MODALITY_PRESERVED: no
DESIGN_STATUS: BLOCKED
REASON: NORMATIVE_MODALITY_DRIFT
DRIFT: MUST B → MAY B
FILES_CHANGED: none | partial-draft-only-if-explicitly-kept-unready
```

## Forbidden

```text
NORMATIVE_CONFLICTS: none
DESIGN_STATUS: READY
```

with the weakened draft declared complete.
