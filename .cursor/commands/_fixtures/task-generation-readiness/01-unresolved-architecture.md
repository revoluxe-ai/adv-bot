# T1 — unresolved architecture blocks tasks

## Given

Upstream `design.md` (or decision) leaves storage SoT open:

```text
pause-block / epoch / due SoT = PG | Redis
(not chosen)
```

No accepted decision names a single SoT.

## When

`/opsx-continue` or `/opsx-ff` is about to create `tasks.md`.

## Expected

```text
TASK_GENERATION_READINESS
UNRESOLVED_DESIGN_CHOICES: pause-block SoT = PG | Redis
TASKS_STATUS: BLOCKED
REASON: TECHNICAL_DESIGN_UNRESOLVED
FILES_CHANGED: none
FIX_ARTIFACT: design.md | decisions/.../decision.md
```

No Owner auto-ask (technical gap ≠ Owner semantic gap).

## Forbidden

```text
- [ ] Выбрать SoT … (PG и/или Redis …)
- [ ] Decide PG or Redis during implementation
```
