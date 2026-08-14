# T4 — genuine semantic ambiguity

## Given

Owner Contract says “pause is reset” but does not define whether epoch
starts on reset (A) or on actual campaign start (B).

## When

`/opsx-continue` (design) or `/opsx-spec-scenario-coverage mode=plan`

## Expected

```text
STATUS: BLOCKED
REASON: UNRESOLVED_PRODUCT_SEMANTICS
UNRESOLVED_TRANSITION: clear_pause → epoch ?
NEXT_ACTION: /opsx-owner-contract-review change=<id>
```

## Forbidden

- Model inference choosing A or B
- `CONFIRM_LIFECYCLE` as substitute Owner authority
- Silent “sensible default”
