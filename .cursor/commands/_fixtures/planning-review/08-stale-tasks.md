# Fixture T8 — stale tasks

## Given

Design was repaired after tasks generation:

* design now: Auto **MUST** start under clear+no-blockers
* tasks still: Auto **MAY** start (generated from prior design)

Optional: design content hash / version note newer than tasks provenance.

## Expected

```text
STATUS: REPAIR_REQUIRED
TYPE: STALE_DERIVED_ARTIFACT
  (and/or NORMATIVE_DRIFT / TASK_DECOMPOSITION_GAP)
FIRST_BAD_ARTIFACT: tasks.md
AFFECTED_DOWNSTREAM: (tasks and any derived checklists)
OWNER_INPUT_REQUIRED: NO
FILES_CHANGED: none
```

Do not treat file existence as freshness.
