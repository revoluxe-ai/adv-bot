"""Unit: calibration views cache helper и AND-gate plan/fact × views."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.calibration_views_cache import (
    ChangePlanFactViews,
    resolve_complex_adv_total_views,
)
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager.full_wb_adv_stat import (
    SmallFullAdvStat,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolve_complex_adv_total_views_sums_all_adv_ids() -> None:
    complex_adv = MagicMock()
    complex_adv.all_adv_ids = {100, 200}

    captured: dict[str, object] = {}

    async def _fake_get_stats(
        adv_ids: list[int], start: datetime, end: datetime
    ) -> SmallFullAdvStat:
        captured["adv_ids"] = adv_ids
        captured["start"] = start
        captured["end"] = end
        return SmallFullAdvStat(
            views=1500,
            clicks=0,
            spend=0.0,
            added_to_cart=0,
            orders=0,
            sum_price=0.0,
        )

    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.calibration_views_cache.full_wb_adv_stat.get_stats_by_last_days",
        new=AsyncMock(side_effect=_fake_get_stats),
    ):
        views = await resolve_complex_adv_total_views(complex_adv, max_last_period=2)

    assert views == 1500
    assert set(captured["adv_ids"]) == {100, 200}  # type: ignore[arg-type]
    start = captured["start"]
    end = captured["end"]
    assert isinstance(start, datetime)
    assert isinstance(end, datetime)
    assert (end - start).days == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolve_complex_adv_total_views_empty_adv_ids() -> None:
    complex_adv = MagicMock()
    complex_adv.all_adv_ids = set()

    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.calibration_views_cache.full_wb_adv_stat.get_stats_by_last_days",
        new=AsyncMock(),
    ) as ch_mock:
        views = await resolve_complex_adv_total_views(complex_adv)

    assert views == 0
    ch_mock.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_change_plan_fact_views_roundtrip() -> None:
    adv = MagicMock()
    adv.adv_id = 42
    cache = ChangePlanFactViews(adv)
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value="999")
    mock_client.set = AsyncMock()

    with patch.object(type(cache), "_client", new_callable=PropertyMock) as client_prop:
        client_prop.return_value = mock_client
        assert await cache.get_cached_views() == 999
        await cache.set_views(1234)
        mock_client.set.assert_awaited_once_with(cache._key, "1234")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_change_plan_fact_views_missing_key() -> None:
    adv = MagicMock()
    adv.adv_id = 43
    cache = ChangePlanFactViews(adv)
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=None)

    with patch.object(type(cache), "_client", new_callable=PropertyMock) as client_prop:
        client_prop.return_value = mock_client
        assert await cache.get_cached_views() is None
