# Fixture T6 — scenario gap

## Given

Design lifecycle includes a material transition (e.g. conditional Auto start
after clear). Scenario coverage plan reports an unresolved gap for that
transition (or plan missing when required). Product behavior itself is
resolved.

## Expected

```text
STATUS: REPAIR_REQUIRED
TYPE: SPEC_COVERAGE_GAP
OWNER_INPUT_REQUIRED: NO
```

Not an Owner question unless product behavior is unresolved.
Not a demand that planning-review rebuild the scenario matrix itself —
point repair to update / scenario-plan writer path as appropriate.
`FILES_CHANGED: none`
