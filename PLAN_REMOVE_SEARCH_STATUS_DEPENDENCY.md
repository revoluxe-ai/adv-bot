# Plan: Remove Search Status Dependency from Auto Adv Counts

## Overview
Remove test-only expectations that auto adv counts depend on Search campaign `active_status`. The implementation already counts all auto advs with `search_adv_id`, regardless of search status. Update tests and documentation to reflect this behavior.

## Steps

### 1. Update Billing Tests

**Files:**
- `tests/modules/billing/test_pricer_tariffs.py`
- `tests/integration/billing/test_pricer_tariff_integration.py`

**Actions:**
- Remove all `fetch_active_search_adv_ids` mocks (method is not used by `fetch_tariff_auto_advs`)
- Update test names to reflect actual behavior:
  - `test_context_counts_only_advs_with_started_search` → `test_context_counts_all_advs_with_search_adv_id`
  - `test_count_is_zero_when_search_campaign_not_started` → `test_count_includes_advs_even_when_search_campaign_not_started`
  - `test_mode_auto_when_auto_settings_configured_but_no_active_search` → `test_mode_auto_when_auto_settings_configured_but_no_search_adv_id`
- Update assertions:
  - `test_context_counts_all_advs_with_search_adv_id`: expect count=3 (all advs with `search_adv_id`, excluding `search_adv_id=None`)
  - `test_count_includes_advs_even_when_search_campaign_not_started`: expect count=1 (auto adv counted regardless of search status)
  - Other tests: remove `fetch_active_search_adv_ids` mocking blocks

### 2. Update Documentation

**File:** `app/modules/billing/pricer/pricer.py`

**Action:** Update `fetch_tariff_auto_advs` docstring to accurately reflect behavior:

```python
"""Возвращает auto-кампании, которые участвуют в тарификации.

Правило на текущий момент:
- AdvSetting.bot_active == True
- Имеет search_adv_id (связь с search-кампанией)

Примечание: Подсчитываются все auto-кампании с search_adv_id, независимо от статуса search-кампании.
"""
```

### 3. Verification Steps

Run the affected billing tests to verify changes:

```powershell
# Unit tests
pytest tests/modules/billing/test_pricer_tariffs.py -v

# Integration tests
pytest tests/integration/billing/test_pricer_tariff_integration.py -v
```

## Expected Behavior

**Before (test expectations):** Auto advs counted only if linked search campaign has `active_status == 'started'`

**After (actual implementation):** Auto advs counted if they have `bot_active=True` and `search_adv_id is not None`, regardless of search campaign status

## Files to Modify

1. `app/modules/billing/pricer/pricer.py` - Update docstring
2. `tests/modules/billing/test_pricer_tariffs.py` - Remove mocks, update assertions and names
3. `tests/integration/billing/test_pricer_tariff_integration.py` - Update assertions and names
