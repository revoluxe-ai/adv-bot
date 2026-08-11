# Fixture T6 — scenario gap

## Given

Design lifecycle includes a material transition (e.g. conditional Auto start
after clear). Durable scenario coverage plan exists and is CURRENT, but
reports an unresolved coverage gap for that transition. Alternatively:
plan missing when required → prefer `SPEC_COVERAGE_EVIDENCE_MISSING`
(see fixtures 13–15). Product behavior itself is resolved.

## Expected

```text
STATUS: REPAIR_REQUIRED   # or BLOCKED for evidence-missing
TYPE: SPEC_COVERAGE_GAP | SPEC_COVERAGE_EVIDENCE_MISSING
OWNER_INPUT_REQUIRED: NO
```

Not an Owner question unless product behavior is unresolved.
Not a demand that planning-review rebuild the scenario matrix itself —
point repair to update / scenario-plan writer path as appropriate
(`NEXT: /opsx-spec-scenario-coverage mode=plan` when evidence missing/stale;
`/opsx-update` when plan shows SPEC gap).
`FILES_CHANGED: none`
