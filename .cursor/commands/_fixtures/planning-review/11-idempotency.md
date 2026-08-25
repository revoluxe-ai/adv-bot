# Fixture T11 — idempotency

## Given

Unchanged planning package reviewed twice (same change tree, no edits).

## Expected

Second run:

```text
same STATUS
same BLOCKING finding TYPEs
same FIRST_BAD_ARTIFACT
same APPLY_PLANNING_GATE
```

Ignore irrelevant timestamps / finding list order / chat fluff.
`FILES_CHANGED: none` both times.
