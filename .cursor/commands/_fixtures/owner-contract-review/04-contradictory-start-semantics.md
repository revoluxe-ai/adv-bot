# Fixture 04 — contradictory start semantics

## Given (owner-contract.md excerpts)

```markdown
## Как поймём, что получилось

- После сброса паузы retest always starts Auto.

## Что должно остаться неизменным

- Бюджет, расписание, баланс могут запрещать start Авто.
```

## Expected

```text
INTERNAL_CONSISTENCY: FAIL
ACCEPTANCE_COHERENCE: FAIL   # optional co-fail; consistency is primary
VERDICT: FAIL
```

## Why

Acceptance asserts unconditional Auto start; keep/invariants assert higher-
priority blocks may prevent start. Reviewer must report the conflict and must
**not** choose which wording is correct.
