# Fixture 04 — contradictory start semantics

## Given (owner-contract.md excerpts)

```markdown
## Как поймём, что получилось

- После сброса паузы retest always starts Auto.

## Что должно остаться неизменным

- Бюджет, расписание, баланс могут запрещать start Авто.
```

## And (when durable Owner decision already proves clear-our-block-only)

```text
OWNER_DECISION (durable):
Сброс паузы снимает только наш shelf-exhausted block.
Auto стартует только если другие blockers разрешают.
```

## Expected

```text
INTERNAL_CONSISTENCY: FAIL
ACCEPTANCE_COHERENCE: FAIL   # optional co-fail; consistency is primary

# Without durable proof which side is Owner meaning:
REVIEW_STATE: NEEDS_OWNER
OWNER_INPUT_REQUIRED: YES

# With durable proof (clear-our-block-only) as above:
REVIEW_STATE: READY_FOR_REPAIR
OWNER_INPUT_REQUIRED: NO
REPAIR_REQUIRED: YES
REPAIR_SEMANTICS: acceptance must not promise unconditional Auto start
```

## Why

Acceptance asserts unconditional Auto start; keep/invariants assert higher-
priority blocks may prevent start. Reviewer must report the conflict and must
**not** choose which wording is correct **unless** durable evidence already
proves Owner semantics — then route to writer repair, not an Owner quiz.
