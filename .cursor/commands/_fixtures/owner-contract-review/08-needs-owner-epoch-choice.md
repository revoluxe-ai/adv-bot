# Fixture 08 — T2 / Finding B real Owner epoch choice missing

## Given (durable statements — both present, fork unresolved)

```text
OWNER said (durable):
«пауза сбрасывается, начинается новый цикл»

OWNER_DECISION (durable):
clear our shelf-exhausted block only;
Auto starts only if no other blockers.
```

## And (owner-contract.md uses ambiguous «новый цикл» without choosing)

```markdown
## Решения Owner

- Кнопка «Сбросить паузу»: пауза сбрасывается, начинается новый цикл
- Снимается только наш block; другие blockers могут держать Auto остановленным
```

## Expected

```text
REVIEW_STATE: NEEDS_OWNER
OWNER_INPUT_REQUIRED: YES

OWNER_QUESTION: (example shape — exact wording may vary)

  Кнопка «Сбросить паузу»:

  A. снимает только shelf-exhausted block;
     новая эпоха начинается, когда Auto реально стартует;

  B. начинает новую эпоху сразу при нажатии,
     даже если другой blocker не даёт Auto стартовать.

must NOT pick A/B for Owner
must NOT be FAIL solely for the unresolved choice
must NOT ask unrelated speculative questions in the same turn if this is the
  only live fork
```

## After Owner answers A (same cycle)

```text
CONFIRMED_OWNER_DECISIONS includes full semantics of A (not "Owner chose A")
REVIEW_STATE: READY_FOR_REPAIR   # if contract text still wrong/ambiguous
# or PASS if contract already matches A exactly
```

## Why

Value of «new cycle» cannot be proven from the conflicting durable fragments —
true product authority gap.
