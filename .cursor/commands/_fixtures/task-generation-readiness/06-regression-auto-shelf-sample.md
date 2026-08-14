# T7 — regression sample: auto-shelf-exhausted-pause-retest

## Purpose

Generator fixture only. Uses planning artifacts under:

```text
openspec/changes/auto-shelf-exhausted-pause-retest/
```

as evidence of prior bad `tasks.md` shapes. **Do not** rewrite that Change's
product artifacts inside `/opsx-meta-fix-command-defects` APPLY for task
generation.

## Upstream fixture requirement (semantic)

```text
our block clear + no remaining blocker → Auto MUST start
remaining blocker exists → Auto MUST NOT force-start Auto
epoch → only after actual Auto start
```

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

3. Modality weakening / conditional collapse:

```text
Auto MAY start
```

or:

```text
только наш блок → Auto MAY start + new epoch
```

when upstream requires conditional `Auto MUST start` (and paired
`MUST NOT` when other blockers remain) plus epoch only after actual start.

## Expected dry-run against sample

```text
New generator MUST NOT emit the bad shapes above.
If design still leaves PG|Redis open → BLOCKED (no tasks write).
If SoT resolved → READY only when:
  NORMATIVE_MODALITY_PRESERVED: yes
  CONDITIONAL_BRANCHES_PRESERVED: yes
  both clear/start branches explicit (MUST start / MUST NOT force-start)
  epoch coupled to actual Auto start
  evidence roles intact
continue ≡ ff for same upstream.
```

## Expected regenerated fragment (semantic shape)

```text
TARGET_REGRESSION — clear/start/epoch

- calendar due / reset button / fit-on-tick
  MUST clear only shelf-exhausted block.

- if another blocker remains after clear:
  Auto MUST NOT be force-started;
  new epoch MUST NOT begin.

- if no other blocker remains after clear:
  Auto MUST start;
  new epoch MUST begin only after actual Auto start.

- no-fit tick:
  shelf-exhausted block MUST remain active.
```

Wording need not be literal; semantic equivalence is required.
