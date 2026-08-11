# Fixture 02 — agent proposal promoted to Owner decision

## Given (durable dialogue extract available to reviewer)

```text
Agent:
"Предлагаю PLAN_DISTANCE only.
Модуль должен быть ON. Ок?"

Owner:
"Да, функционал только если модуль ON."
```

## And (owner-contract.md excerpt)

```markdown
## Решения Owner

- Функционал только если модуль ON
- PLAN_DISTANCE only
```

## Expected

```text
OWNER_DECISION_PROVENANCE: FAIL
# or NEEDS_OWNER if reviewer treats missing confirmation as Owner question
# (must NOT be PASS)

VERDICT: FAIL | NEEDS_OWNER
```

## Finding focus

`PLAN_DISTANCE only` has no separate durable Owner confirmation.
Owner confirmed **module ON** only. Neighboring “Ок?” / bundled agent proposal
must not launder the second bullet into `OWNER_DECISION`.
