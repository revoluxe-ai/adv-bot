# Plan: Remove Active-Search Filter from `pricer.calculate_tariff_context`

## Overview
Remove the requirement that search campaigns must have `active_status == 'started'` for auto campaigns to be counted in tariff calculations. Currently, `fetch_tariff_auto_advs` should count all `bot_active=True` auto campaigns that have a `search_adv_id`, regardless of the search campaign's active status.

## Current State Analysis

### Implementation (`app/modules/billing/pricer/pricer.py`)

**Current `fetch_tariff_auto_advs` behavior (lines 145-165):**
- Returns all `auto_advs` if they have `search_adv_ids`
- Does NOT actually filter by `active_status == 'started'` despite the docstring mentioning it
- The method `fetch_active_search_adv_ids` exists but is NOT called in `fetch_tariff_auto_advs`

**Current `calculate_tariff_context` flow:**
1. Fetches `bot_active=True` advs via `fetch_bot_active_advs`
2. Calls `fetch_tariff_auto_advs` which currently returns all advs with `search_adv_id`
3. Counts the returned advs

### Test Expectations

**Tests that expect active-search filtering:**
1. `test_context_counts_only_advs_with_started_search` - expects only 2 out of 4 advs counted
2. `test_count_is_zero_when_search_campaign_not_started` - expects count=0 when search is paused
3. `test_mode_auto_when_auto_settings_configured_but_no_active_search` - expects count=0 when no active search

**Tests that mock `fetch_active_search_adv_ids`:**
- Multiple tests patch this method, suggesting filtering was intended

## Code Changes Required

### 1. Update `fetch_tariff_auto_advs` Method

**File:** `app/modules/billing/pricer/pricer.py`

**Current implementation (lines 145-165):**
```python
@staticmethod
async def fetch_tariff_auto_advs(
    session: AsyncSession,
    shop_id: str,
    *,
    auto_advs: Sequence[AdvSetting] | None = None,
) -> Sequence[AdvSetting]:
    """Возвращает auto-кампании, которые участвуют в тарификации.

    Правило на текущий момент:
    - AdvSetting.bot_active == True
    - search-кампания (search_adv_id) имеет active_status == 'started'
    """
    if auto_advs is None:
        auto_advs = await Pricer.fetch_bot_active_advs(session, shop_id)
    if not auto_advs:
        return []

    search_adv_ids = [adv.search_adv_id for adv in auto_advs if adv.search_adv_id]
    if not search_adv_ids:
        return []
    return auto_advs
```

**New implementation:**
```python
@staticmethod
async def fetch_tariff_auto_advs(
    session: AsyncSession,
    shop_id: str,
    *,
    auto_advs: Sequence[AdvSetting] | None = None,
) -> Sequence[AdvSetting]:
    """Возвращает auto-кампании, которые участвуют в тарификации.

    Правило на текущий момент:
    - AdvSetting.bot_active == True
    - Имеет search_adv_id (связь с search-кампанией)
    """
    if auto_advs is None:
        auto_advs = await Pricer.fetch_bot_active_advs(session, shop_id)
    if not auto_advs:
        return []

    # Return all auto_advs that have a search_adv_id, regardless of search campaign status
    return [adv for adv in auto_advs if adv.search_adv_id is not None]
```

**Changes:**
- Remove check for `search_adv_ids` list emptiness
- Filter to only advs with `search_adv_id is not None`
- Update docstring to remove mention of `active_status == 'started'`

### 2. Remove or Deprecate `fetch_active_search_adv_ids` Method

**File:** `app/modules/billing/pricer/pricer.py`

**Decision:** Keep method for now (may be used elsewhere), but it's no longer called by `fetch_tariff_auto_advs`.

**Note:** Check if this method is used elsewhere before removing.

## Test Updates Required

### 1. `test_context_counts_only_advs_with_started_search`

**File:** `tests/modules/billing/test_pricer_tariffs.py`

**Current expectation:** Counts only 2 advs (those with started search campaigns)

**New expectation:** Counts all 4 advs (all have `search_adv_id`)

**Update:**
```python
@pytest.mark.asyncio
async def test_context_counts_all_advs_with_search_adv_id(
    self, monkeypatch: pytest.MonkeyPatch
):
    advs = [
        DummyAdv(search_adv_id=10, automatic_version=1, auto_update_white_list=True),
        DummyAdv(search_adv_id=11, automatic_version=1, auto_update_white_list=False),
        DummyAdv(search_adv_id=None, automatic_version=1, auto_update_white_list=True),  # No search_adv_id
        DummyAdv(search_adv_id=12, automatic_version=1, auto_update_white_list=True),
    ]

    async def _fake_fetch_bot_active_advs(
        session: Any, shop_id: str
    ) -> Sequence[DummyAdv]:
        return advs

    monkeypatch.setattr(
        Pricer, "fetch_bot_active_advs", staticmethod(_fake_fetch_bot_active_advs)
    )

    details = await Pricer().get_tariff_details(session=None, shop_id="s")  # type: ignore[arg-type]
    # Should count 3 advs (10, 11, 12) - all with search_adv_id, regardless of search status
    assert details.count == 3
```

**Changes:**
- Remove mocking of `fetch_active_search_adv_ids` (no longer needed)
- Update test name to reflect new behavior
- Update assertion to expect 3 instead of 2 (excluding the one with `search_adv_id=None`)

### 2. `test_count_is_zero_when_search_campaign_not_started`

**File:** `tests/integration/billing/test_pricer_tariff_integration.py`

**Current expectation:** `count == 0` when search campaign is paused

**New expectation:** `count == 1` (auto campaign should be counted regardless of search status)

**Update:**
```python
async def test_count_includes_advs_even_when_search_campaign_not_started(
    async_session: AsyncSession,
    wb_cabinet: WBCabinet,
):
    wb_cabinet_id = 1
    shop_id = "test_shop_id"

    search = AdvSetting(
        adv_id=90201,
        name="search_90201",
        wb_cabinet_id=wb_cabinet_id,
        active_status="paused",  # Paused search campaign
        bot_active=False,
    )
    auto = _make_auto_adv(
        adv_id=90202,
        wb_cabinet_id=wb_cabinet_id,
        search_adv_id=search.adv_id,
        automatic_version=1,
        wl=True,
        tp=True,
    )

    async_session.add_all([search, auto])
    await async_session.flush()

    details = await Pricer().get_tariff_details(async_session, shop_id)
    # Should count auto campaign even though search is paused
    assert details.count == 1
    assert details.total_per_month > 0.0
```

**Changes:**
- Update test name
- Change expected count from 0 to 1
- Update assertion to expect non-zero total

### 3. `test_mode_auto_when_auto_settings_configured_but_no_active_search`

**File:** `tests/modules/billing/test_pricer_tariffs.py`

**Current expectation:** `count == 0` when no active search campaigns

**New expectation:** `count == 0` only if `search_adv_id is None`, otherwise count regardless of search status

**Update:**
```python
@pytest.mark.asyncio
async def test_mode_auto_when_auto_settings_configured_but_no_search_adv_id(
    self, monkeypatch: pytest.MonkeyPatch
):
    advs = [
        DummyAdv(
            search_adv_id=None,  # No search_adv_id
            automatic_version=1,
            auto_update_white_list=True,
            auto_update_target_place=False,
        ),
    ]

    async def _fake_fetch_bot_active_advs(
        session: Any, shop_id: str
    ) -> Sequence[DummyAdv]:
        return advs

    monkeypatch.setattr(
        Pricer, "fetch_bot_active_advs", staticmethod(_fake_fetch_bot_active_advs)
    )

    details = await Pricer().get_tariff_details(session=None, shop_id="s")  # type: ignore[arg-type]
    assert details.mode == TariffMode.AUTO
    assert details.count == 0  # No search_adv_id means not counted
    assert details.total_per_month == 0.0
```

**Changes:**
- Update test name to clarify it's about missing `search_adv_id`, not active status
- Remove mocking of `fetch_active_search_adv_ids`
- Keep expectation of count=0 (because `search_adv_id is None`)

### 4. Other Tests That Mock `fetch_active_search_adv_ids`

**Files to update:**
- `test_context_no_bot_active_advs_means_zero_and_old`
- `test_mode_switches_to_auto_if_any_part_auto_enabled`
- `test_mode_stays_old_if_no_part_auto_enabled`
- `test_exponent_does_not_switch_to_auto_mode`

**Action:** Remove all `fetch_active_search_adv_ids` mocking from these tests since it's no longer used.

**Pattern to remove:**
```python
async def _fake_fetch_active_search_adv_ids(
    session: Any, search_adv_ids: Sequence[int]
) -> set[int]:
    return {10, 11}  # or whatever

if hasattr(Pricer, "fetch_active_search_adv_ids"):
    monkeypatch.setattr(...)
else:
    monkeypatch.setattr(...)
```

### 5. Integration Test: `test_auto_mode_applies_without_active_search_campaigns`

**File:** `tests/integration/billing/test_pricer_tariff_integration.py`

**Current:** Expects `count == 0` when `search_adv_id=None`

**New:** Keep expectation (correct behavior - no `search_adv_id` means not counted)

**Action:** Update test name for clarity:
```python
async def test_auto_mode_applies_without_search_adv_id(
    async_session: AsyncSession,
    wb_cabinet: WBCabinet,
):
    # ... existing test code unchanged ...
    assert details.count == 0  # Still 0 because search_adv_id is None
```

## Summary of Changes

### Code Files
1. **`app/modules/billing/pricer/pricer.py`**
   - Update `fetch_tariff_auto_advs` to filter only by `search_adv_id is not None`
   - Update docstring
   - Keep `fetch_active_search_adv_ids` (check if used elsewhere first)

### Test Files
1. **`tests/modules/billing/test_pricer_tariffs.py`**
   - Update `test_context_counts_only_advs_with_started_search` → `test_context_counts_all_advs_with_search_adv_id`
   - Update `test_mode_auto_when_auto_settings_configured_but_no_active_search` → `test_mode_auto_when_auto_settings_configured_but_no_search_adv_id`
   - Remove `fetch_active_search_adv_ids` mocking from all tests

2. **`tests/integration/billing/test_pricer_tariff_integration.py`**
   - Update `test_count_is_zero_when_search_campaign_not_started` → `test_count_includes_advs_even_when_search_campaign_not_started`
   - Update `test_auto_mode_applies_without_active_search_campaigns` → `test_auto_mode_applies_without_search_adv_id`

## Expected Impact

### Behavior Change
- **Before:** Auto campaigns were counted only if their linked search campaign had `active_status == 'started'`
- **After:** Auto campaigns are counted if they have `bot_active=True` and `search_adv_id is not None`, regardless of search campaign status

### Billing Impact
- **Potential increase in billing:** More campaigns may be counted, leading to higher charges for shops with paused search campaigns
- **Recommendation:** Verify business requirements before deploying

## Verification Steps

1. Run unit tests: `pytest tests/modules/billing/test_pricer_tariffs.py -v`
2. Run integration tests: `pytest tests/integration/billing/test_pricer_tariff_integration.py -v`
3. Check for other usages of `fetch_active_search_adv_ids`: `grep -r "fetch_active_search_adv_ids" app/`
4. Verify billing calculations in staging environment
