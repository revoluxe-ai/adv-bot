# Paid regression suite

Контрактные тесты: **платное поведение не сломано** (`AdvSetting.bot_active=True`).

## Когда запускать

- Перед merge любой ветки с free UI, shop-runner, billing или client_bot automation.
- После рефакторинга `_get_active_advs` / RECORD vs ACT.

## Команда

```powershell
poetry run pytest tests/paid_regression -m paid_regression -v
```

## Критерий «paid не сломан»

- Все тесты с маркером `paid_regression` — **GREEN**.
- Дополнительно (рекомендуется): curated adjunct из [CURATED.md](./CURATED.md).

## Pre-merge для free-веток

```powershell
poetry run pytest tests/paid_regression -m paid_regression -v
poetry run pytest tests/bot_active_gates -m bot_active_gates -v
```

Gate-тесты на RECORD с `xfail` допустимы; ACT gates (P0) — обязаны быть GREEN.

## Состав

| Область | Что проверяем |
|---------|----------------|
| Turn bot on/off | balance check, `bot_active` toggle |
| Inverse ACT gates | при active — write path вызывается |
| Pricer | tariff считает только bot-active кампании |

См. также [CURATED.md](./CURATED.md) — существующие тесты billing/balance.
