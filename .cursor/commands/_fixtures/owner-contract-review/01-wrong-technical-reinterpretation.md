# Fixture 01 — wrong technical reinterpretation

## Given (durable OWNER_INTENT)

```text
OWNER_INTENT:
старый модуль управления ставкой
не конфликтует с новым
```

Product meaning (Owner language): old Auto bid-control module must not conflict
with the new shelf bid-control module.

## And (owner-contract.md excerpt)

```markdown
## Что хотим получить

legacy cost pause / cost watchdog должен сосуществовать
с shelf bid control
```

## Expected

```text
INTENT_PRESERVATION: FAIL
VERDICT: FAIL
```

## Why

Contract replaced Owner’s object of change (two bid-control modules) with a
technical cost-watchdog framing without durable Owner correction.
