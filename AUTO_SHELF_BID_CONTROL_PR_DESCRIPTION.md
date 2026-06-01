# PR Description Notes: Auto Shelf Bid Control v1

## Conversion policy (обязательный блок)

### 1) Какие единицы принимает `WBApi.update_cpm`

`WBApi.update_cpm(adv_id, nmid, new_bid)` отправляет integer `bid` в payload:

```json
{
  "bids": [
    {
      "advert_id": "<adv_id>",
      "nm_bids": [{"nm": "<nmid>", "bid": "<new_bid>"}]
    }
  ]
}
```

### 2) Как `bid_minor` конвертируется в `api_bid`

В v1 применяется identity policy:

- `api_bid = bid_minor`

Скрытых преобразований между копейками и legacy CPM в setter нет.

### 3) Чем это подтверждено

- legacy-код:
  - `app/client_bot/user_interface/handlers/change_cpm.py`
  - `app/modules/shop_runner/bidder/bidder_func.py`
- unit-тесты:
  - `tests/unit/test_auto_shelf_bid_setter.py`
- dry-run верификация:
  - при `AUTO_SHELF_BID_CONTROL_DRY_RUN=true` реальные PATCH в WB не выполняются.

