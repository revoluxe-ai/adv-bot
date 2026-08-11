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
REVIEW_STATE: READY_FOR_REPAIR | NEEDS_OWNER

# Prefer READY_FOR_REPAIR when reviewer instructs removal of unproven bullet
# (Owner already confirmed module ON only — do NOT re-ask module ON).
# NEEDS_OWNER only if reviewer treats PLAN_DISTANCE as a live product fork
# still needing an explicit A/B choice.

OWNER_INPUT_REQUIRED: NO   # for module ON (already confirmed)
# For PLAN_DISTANCE bullet:
#   OWNER_INPUT_REQUIRED: YES  only if asking whether to adopt it
#   OR REPAIR_REQUIRED: YES to drop unproven bullet without re-asking

must NOT be PASS
must NOT treat PLAN_DISTANCE as confirmed OWNER_DECISION
```

## Finding focus

`PLAN_DISTANCE only` has no separate durable Owner confirmation.
Owner confirmed **module ON** only. Neighboring “Ок?” / bundled agent proposal
must not launder the second bullet into `OWNER_DECISION`.
