# T3 — conditional branch preservation

## Given

Upstream requirement (two deterministic branches):

```text
no other blocker → Auto MUST start
other blocker remains → Auto MUST NOT be force-started
```

## When

Generator decomposes that requirement into task lines.

## Expected

Both branches present with preserved modality:

```text
… no other blockers … → Auto MUST start
… other blocker … → Auto MUST NOT be force-started
CONDITIONAL_BRANCHES_PRESERVED: yes
NORMATIVE_MODALITY_PRESERVED: yes
TASKS_STATUS: READY
```

## Forbidden

```text
Auto MAY start
```

used as a collapse of the two branches into optional start.

On collapse:

```text
CONDITIONAL_BRANCHES_PRESERVED: no
TASKS_STATUS: BLOCKED
REASON: CONDITIONAL_BRANCH_COLLAPSE
FILES_CHANGED: none
```
