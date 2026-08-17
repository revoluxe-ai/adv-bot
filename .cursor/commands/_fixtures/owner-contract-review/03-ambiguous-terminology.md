# Fixture 03 — ambiguous terminology («полки»)

## Given (owner-contract.md uses «полки» for two entities)

```markdown
## Что хотим получить

Когда в полках больше нечего тестировать — Авто на паузе.
Управление полками при этом не выключается.

## Что должно остаться неизменным

- Полки не выключаются из‑за паузы.
- Пауза Search из‑за пустых ключей — отдельно; полки этот change не трогает.
```

No durable disambiguation that distinguishes:

* WB Auto campaign / shelf placement («полки» as placement), vs
* bot module «Управление ставкой в полках».

## Expected

```text
TERMINOLOGY: FAIL | NEEDS_OWNER
VERDICT: NEEDS_OWNER | FAIL
```

## OWNER_QUESTION (example)

```text
Где «полки» = размещение Auto на WB, а где = модуль
«Управление ставкой в полках»? Нужны разные формулировки в контракте.
```
