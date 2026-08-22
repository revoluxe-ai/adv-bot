# T4 — epoch coupling to actual Auto start

## Given

Upstream:

```text
new epoch MUST begin only after actual Auto start
```

Clear/start context (paired with conditional start rules):

```text
clear our block → evaluate remaining blockers
actual Auto start → new epoch may/must begin per upstream
Auto remains paused after clear → MUST NOT start new epoch
```

## When

Generator emits clear / start / epoch task lines.

## Expected

```text
paused after clear → MUST NOT begin new epoch
actual start → epoch begins (coupled)
NORMATIVE_MODALITY_PRESERVED: yes
CONDITIONAL_BRANCHES_PRESERVED: yes
TASKS_STATUS: READY
```

## Forbidden

```text
clear → new epoch
Auto MAY start + new epoch
```

as substitutes that drop the actual-start coupling.
