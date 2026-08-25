# T5 — stale design

## Given

Plan generated against design A. `design.md` later becomes A2 (content hash
changes). Receipt still cites design A hash.

## When

Tasks or planning-review freshness check.

## Expected

```text
SCENARIO_PLAN_FRESHNESS: stale
REASON / TYPE: SCENARIO_PLAN_EVIDENCE_STALE | STALE_DERIVED_ARTIFACT
MUST NOT accept old plan as CURRENT
NEXT: /opsx-spec-scenario-coverage mode=plan
```
