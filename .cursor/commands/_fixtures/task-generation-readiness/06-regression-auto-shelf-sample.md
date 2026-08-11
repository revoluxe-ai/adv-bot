# T6 — regression sample: auto-shelf-exhausted-pause-retest

## Purpose

Generator fixture only. Uses planning artifacts under:

```text
openspec/changes/auto-shelf-exhausted-pause-retest/
```

as evidence of prior bad `tasks.md` shapes. **Do not** rewrite that Change's
product artifacts inside `/opsx-meta-fix-command-defects` APPLY for task
generation.

## Known bad shapes (must NOT be re-emitted by new generator)

From previously generated `tasks.md`:

1. Architecture-as-task:

```text
Выбрать SoT нашего pause-block / epoch / due (PG и/или Redis …)
```

Expected instead: if SoT still open in design →
`TASKS_STATUS: BLOCKED` / `TECHNICAL_DESIGN_UNRESOLVED`
(fix design/decision first).

2. Characterization mixed as final green after intentional kill of mid-cycle
   cost pause:

```text
Characterization … cost_rule_failed / pause_auto_campaign
```

paired without role split against target
`module ON → MUST NOT ordinary cost pause`.

Expected: `LEGACY_BASELINE` + `TARGET_REGRESSION` (no OLD MUST ∧ OLD MUST NOT).

3. Modality weakening:

```text
Auto MAY start
```

when upstream requires conditional `Auto MUST start`
(and paired `MUST NOT` when other blockers remain).

## Expected dry-run against sample

```text
New generator MUST NOT emit the three bad shapes above.
If design still leaves PG|Redis open → BLOCKED (no tasks write).
If SoT resolved → READY tasks with evidence roles + MUST/MUST NOT intact.
continue ≡ ff for same upstream.
```
