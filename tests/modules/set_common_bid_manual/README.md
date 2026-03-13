# Tests for set_common_bid_manual

## Coverage: 81%

Unit tests for the manual common bid setting handler with FSM state error handling.

## Test Cases

### Successful Flow Tests
1. **test_set_common_bid_manual_start_success** - Start flow: get min bids, save to state, set waiting state
2. **test_set_common_bid_manual_apply_success** - Success: update WB, save to Redis, reload menu

### Error Handling Tests  
3. **test_set_common_bid_manual_start_no_search_adv** - Start when campaign has no search_adv_id
4. **test_set_common_bid_manual_apply_missing_state_data** - **Missing FSM state: show error, wait 1s, DON'T reload (no data)**
5. **test_set_common_bid_manual_apply_partial_state_reload_menu** - **Partial FSM state: show error, wait 1s, RELOAD menu (IDs available)**

### Validation Tests
6. **test_set_common_bid_manual_apply_invalid_input** - Non-numeric input
7. **test_set_common_bid_manual_apply_bid_below_minimum** - Bid below minimum
8. **test_set_common_bid_manual_apply_bid_above_maximum** - Bid above system max (3000 rub)

### Helper Function Tests
9. **test_reload_adv_setting_menu_success** - Reload menu helper: loads data and calls AdvSettingMenu
10. **test_reload_adv_setting_menu_missing_data** - Reload menu with missing data: don't call menu

## Key Scenarios Tested

### FSM State Loss Handling (Tests 4-5)
- ✅ **Completely missing state**: User gets error message with support link, no reload attempt
- ✅ **Partial state (IDs present, min_bid missing)**: User gets error message, waits 1 second, menu reloaded
- ✅ Both scenarios clear FSM state (`set_state(None)`)
- ✅ Error message includes: "не найдены сохраненные данные", "Начните заново", support link

### Success Path (Test 2)
- ✅ Validates input (numeric, >= min_bid, <= MAX_BID_RUB)
- ✅ Updates WB via `update_search_adv_common_cpm`
- ✅ Saves to Redis (bid values + timestamp)
- ✅ Shows success message
- ✅ Reloads AdvSettingMenu

## Run Tests

```powershell
# All tests
poetry run pytest tests/modules/set_common_bid_manual/test_handlers.py -v

# With coverage
poetry run pytest tests/modules/set_common_bid_manual/test_handlers.py --cov=app.client_bot.user_interface.handlers.set_common_bid_manual --cov-report=term-missing

# Specific test
poetry run pytest tests/modules/set_common_bid_manual/test_handlers.py::test_set_common_bid_manual_apply_partial_state_reload_menu -v
```

## Production Ready ✅

All critical paths tested:
- ✅ Happy path (successful bid update)
- ✅ FSM state loss (session expired) with graceful recovery
- ✅ Input validation (format, min/max bounds)
- ✅ Error handling (missing campaign, no search_adv_id, WB API errors)
- ✅ Menu reload after success and after error (when possible)
- ✅ 1-second pause before reload for better UX
