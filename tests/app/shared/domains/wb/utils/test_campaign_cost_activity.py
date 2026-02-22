from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.shared.domains.wb.utils.auto_campaign_cost_activity import (
    get_auto_campaign_cost_activity_metrics,
    is_auto_campaign_active,
)


class _FakeAdvSetting:
    def __init__(
        self,
        adv_id: int,
        *,
        plan_for_sales_for_day: int | None,
        target_price_for_order: int | float | None,
        max_price_for_order: int | float | None,
    ) -> None:
        self.adv_id = adv_id
        self.plan_for_sales_for_day = plan_for_sales_for_day
        self.target_price_for_order = target_price_for_order
        self.max_price_for_order = max_price_for_order


@pytest.mark.asyncio
async def test_is_auto_campaign_active_returns_true_when_avg_cost_below_target() -> None:
    adv = _FakeAdvSetting(
        101,
        plan_for_sales_for_day=10,
        target_price_for_order=100,
        max_price_for_order=200,
    )
    reader = SimpleNamespace(
        get_latest_plan_fact=AsyncMock(
            return_value=SimpleNamespace(fact_predict_orders=12.0)
        )
    )

    with patch(
        "app.shared.domains.wb.utils.auto_campaign_cost_activity.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=90.0),
    ):
        result = await is_auto_campaign_active(adv, plan_fact_reader=reader)

    assert result is True


@pytest.mark.asyncio
async def test_is_auto_campaign_active_returns_false_when_avg_cost_above_target() -> None:
    adv = _FakeAdvSetting(
        102,
        plan_for_sales_for_day=10,
        target_price_for_order=100,
        max_price_for_order=200,
    )
    reader = SimpleNamespace(
        get_latest_plan_fact=AsyncMock(
            return_value=SimpleNamespace(fact_predict_orders=15.0)
        )
    )

    with patch(
        "app.shared.domains.wb.utils.auto_campaign_cost_activity.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=150.0),
    ):
        result = await is_auto_campaign_active(adv, plan_fact_reader=reader)

    assert result is False


@pytest.mark.asyncio
async def test_is_auto_campaign_active_returns_none_without_plan_fact_row() -> None:
    adv = _FakeAdvSetting(
        103,
        plan_for_sales_for_day=10,
        target_price_for_order=100,
        max_price_for_order=200,
    )
    reader = SimpleNamespace(get_latest_plan_fact=AsyncMock(return_value=None))

    with patch(
        "app.shared.domains.wb.utils.auto_campaign_cost_activity.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=80.0),
    ):
        result = await is_auto_campaign_active(adv, plan_fact_reader=reader)

    assert result is None


@pytest.mark.asyncio
async def test_get_auto_campaign_cost_activity_metrics_returns_none_when_avg_missing() -> None:
    adv = _FakeAdvSetting(
        104,
        plan_for_sales_for_day=10,
        target_price_for_order=120,
        max_price_for_order=220,
    )
    reader = SimpleNamespace(
        get_latest_plan_fact=AsyncMock(
            return_value=SimpleNamespace(fact_predict_orders=12.0)
        )
    )

    with patch(
        "app.shared.domains.wb.utils.auto_campaign_cost_activity.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=None),
    ):
        metrics = await get_auto_campaign_cost_activity_metrics(
            adv,
            plan_fact_reader=reader,
        )

    assert metrics.target_cost == 120.0
    assert metrics.avg_cost is None
    assert metrics.is_active is None
