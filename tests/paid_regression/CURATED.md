# Curated adjunct tests (paid safety)

Дополнительные существующие тесты, рекомендуемые перед free/paid изменениями:

```powershell
poetry run pytest tests/modules/billing -m unit -q
poetry run pytest tests/modules/balance_manager/test_handlers_comprehensive.py -m unit -q
poetry run pytest tests/modules/shop_menu/test_message_tariff.py -m unit -q
poetry run pytest tests/unit/client_bot/handlers/test_toggle_cabinet_active.py -m unit -q
poetry run pytest tests/modules/billing/test_pricer_tariffs.py -m unit -q
```

| Путь | Контракт |
|------|----------|
| `tests/modules/billing/` | charge, pricer, parallel billing |
| `tests/modules/balance_manager/test_handlers_comprehensive.py` | balance handlers |
| `tests/modules/shop_menu/test_message_tariff.py` | tariff display в shop menu |
| `tests/unit/client_bot/handlers/test_toggle_cabinet_active.py` | cabinet active toggle |
| `tests/modules/billing/test_pricer_tariffs.py` | tariff vs bot_active count |

Новые контракты — в `tests/paid_regression/` с маркером `@pytest.mark.paid_regression`.
