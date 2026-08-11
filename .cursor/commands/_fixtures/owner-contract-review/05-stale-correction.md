# Fixture 05 — stale assumption after Owner correction

## Given (earlier durable state)

```text
cost watchdog / mid-cycle cost pause: orthogonal / unchanged
```

## And (Owner correction — durable)

```text
OWNER_DECISION:
remove mid-cycle cost pause when shelf bid module is ON
```

## And (owner-contract.md still contains both)

```markdown
## Что должно остаться неизменным

- cost watchdog mid-cycle pause behavior unchanged

## Решения Owner

- Выпилить mid-cycle cost pause при включённом «Управление ставкой в полках»
```

## Expected

```text
STALE_ASSUMPTIONS: FAIL
REVIEW_STATE: READY_FOR_REPAIR
OWNER_INPUT_REQUIRED: NO
REPAIR_REQUIRED: YES
REPAIR_SEMANTICS: remove stale "mid-cycle pause unchanged" keep bullet;
                  keep Owner decision to remove mid-cycle pause when module ON
must NOT re-ask Owner to confirm the correction
must NOT be overall NEEDS_OWNER solely for this finding
```

## Why

Owner correction changed meaning, but the old assumption remains in another
section. Reviewer must flag stale residue; must not silently delete or rewrite;
must emit writer repair in OWNER_REVIEW_HANDOFF when other blockers are clear.
