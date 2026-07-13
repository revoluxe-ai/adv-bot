# Bot-active ACT gates

Инварианты **free/paid границы**: при `bot_active=False` автоматика **не мутирует Wildberries**, даже если все auto-flags включены (leak detection).

## P0 категории (обязаны быть GREEN)

1. **Общая ставка search** — `update_common_bid_in_search_adv`
2. **Target place ключей** — `update_individual_keyword_target_places`, `adv_settings_auto_update`
3. **Whitelist** — `update_top_key_in_advs`, `white_list_tail_trimmer`
4. **Shelf bid** — `auto_shelf_bid_control`

Расширение P0: `update_cluster_bids`, `update_minus_phrases_in_advs`, `update_cpm_bid`.

## Команда

```powershell
poetry run pytest tests/bot_active_gates -m bot_active_gates -v
```

## RECORD-тесты и xfail

Тесты на **запись при inactive** помечены `@pytest.mark.xfail(reason="loader refactor pending")`:

- Сейчас `_get_active_advs()` фильтрует `bot_active=True` — кампания не попадает в pipeline.
- **Снять xfail** после follow-up change: расширить loader для RECORD, ACT gate через `bot_active`.

Критерий снятия xfail:

1. `_get_active_advs` (или аналог) возвращает все non-done РК кабинета.
2. ACT-корутины по-прежнему фильтруют `bot_active=True`.
3. `test_keyword_stamp_runs_when_inactive` и `test_common_sale_stat_runs_when_inactive` — GREEN без xfail.

## Матрица корутин

См. [RECORD_ACT_MATRIX.md](./RECORD_ACT_MATRIX.md).
