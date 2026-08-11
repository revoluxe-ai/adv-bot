# Fixture 09 — T3 / Finding A stale writer text, semantics known

## Given (durable Owner decision)

```text
OWNER_DECISION:
Снимается только shelf-exhausted block.
Auto реально стартует только если другие blockers (budget/schedule/balance/…)
разрешают.
```

## And (owner-contract.md acceptance)

```markdown
## Как поймём, что получилось

- Через заданное число суток Авто снова включается
```

## Expected

```text
ACCEPTANCE_COHERENCE: FAIL   # or STALE_ASSUMPTIONS / INTERNAL_CONSISTENCY
REVIEW_STATE: READY_FOR_REPAIR
OWNER_INPUT_REQUIRED: NO
REPAIR_REQUIRED: YES
REPAIR_SEMANTICS: after N days only our block is cleared; Auto starts only if
                  other blockers allow — do not promise unconditional restart

must NOT ask Owner to reconfirm clear-our-block-only
must NOT be NEEDS_OWNER for this finding alone
OWNER_REVIEW_HANDOFF present when no other NEEDS_* remain
REPAIR_COMMAND: /opsx-new
MODE: READ_ONLY
FILES_CHANGED: none
```

## Why

Correct semantics already proven; contract wording is a writer defect.
