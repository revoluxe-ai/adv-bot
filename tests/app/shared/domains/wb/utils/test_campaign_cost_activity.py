from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.common_slaves.wildberries.models.models import BidderCoroutineType
from app.shared.domains.wb.utils.auto_campaign_cost_activity import (
    get_auto_campaign_cost_activity_metrics,
    is_auto_campaign_active,
)


def _plan_fact_summary(
    *,
    fact_predict_orders: object,
    plan_fact_ch_ts_msk: str = "01.01.2025 00:00",
    fact_original_orders: float | None = None,
    fact_pay_for_order: object = None,
    fact_method: str | None = None,
) -> SimpleNamespace:
    """Минимальный снимок plan/fact для unit-тестов cost activity."""
    return SimpleNamespace(
        fact_predict_orders=fact_predict_orders,
        fact_original_orders=fact_original_orders,
        fact_pay_for_order=fact_pay_for_order,
        fact_method=fact_method,
        plan_fact_ch_ts_msk=plan_fact_ch_ts_msk,
    )


class _FakeAdvSetting:
    def __init__(
        self,
        adv_id: int,
        *,
        plan_for_sales_for_day: int | None,
        target_price_for_order: float | None,
        max_price_for_order: float | None,
        auto_shelf_bid_control_enabled: bool = False,
        bidder_coroutine_type: BidderCoroutineType = (
            BidderCoroutineType.OLD_UPDATE_CPM_BIDDER
        ),
    ) -> None:
        self.adv_id = adv_id
        self.plan_for_sales_for_day = plan_for_sales_for_day
        self.target_price_for_order = target_price_for_order
        self.max_price_for_order = max_price_for_order
        self.sales_predict_method = FactMethods.DIRECT_SALES
        self.auto_shelf_bid_control_enabled: bool = auto_shelf_bid_control_enabled
        self.bidder_coroutine_type = bidder_coroutine_type

@pytest.mark.asyncio
async def test_is_auto_campaign_active_returns_true_when_avg_cost_below_target() -> None:
    adv = _FakeAdvSetting(
        101,
        plan_for_sales_for_day=10,
        target_price_for_order=100,
        max_price_for_order=200,
        auto_shelf_bid_control_enabled=False
    )
    reader = SimpleNamespace(
        get_latest_plan_fact=AsyncMock(
            return_value=_plan_fact_summary(
                fact_predict_orders=12.0,
                plan_fact_ch_ts_msk="01.01.2025 00:00",
            )
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
            return_value=_plan_fact_summary(
                fact_predict_orders=15.0,
                fact_pay_for_order=150.0,
                plan_fact_ch_ts_msk="01.01.2025 00:00",
            )
        )
    )

    with patch(
        "app.shared.domains.wb.utils.auto_campaign_cost_activity.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=150.0),
    ):
        result = await is_auto_campaign_active(adv, plan_fact_reader=reader)

    assert result is False


@pytest.mark.asyncio
async def test_is_auto_campaign_active_returns_false_for_cluster_bidder_without_shelf_control() -> None:
    """Кластерный биддер без shelf-control: cost-rule по-прежнему применяется."""
    adv = _FakeAdvSetting(
        107,
        plan_for_sales_for_day=10,
        target_price_for_order=100,
        max_price_for_order=200,
        auto_shelf_bid_control_enabled=False,
        bidder_coroutine_type=BidderCoroutineType.UPDATE_CLUSTER_BIDS,
    )
    reader = SimpleNamespace(
        get_latest_plan_fact=AsyncMock(
            return_value=_plan_fact_summary(
                fact_predict_orders=5.0,
                fact_pay_for_order=680.0,
                plan_fact_ch_ts_msk="01.01.2025 00:00",
            )
        )
    )

    with patch(
        "app.shared.domains.wb.utils.auto_campaign_cost_activity.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=680.0),
    ):
        result = await is_auto_campaign_active(adv, plan_fact_reader=reader)

    assert result is False


@pytest.mark.asyncio
async def test_is_auto_campaign_active_returns_false_for_shelf_bid_control_when_both_cpo_bad() -> None:
    adv = _FakeAdvSetting(
        105,
        plan_for_sales_for_day=10,
        target_price_for_order=100,
        max_price_for_order=200,
        auto_shelf_bid_control_enabled=True,
    )
    reader = SimpleNamespace(
        get_latest_plan_fact=AsyncMock(
            return_value=_plan_fact_summary(
                fact_predict_orders=15.0,
                fact_pay_for_order=120.0,
                plan_fact_ch_ts_msk="01.01.2025 00:00",
            )
        )
    )

    with patch(
        "app.shared.domains.wb.utils.auto_campaign_cost_activity.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=150.0),
    ):
        result = await is_auto_campaign_active(adv, plan_fact_reader=reader)

    assert result is False


@pytest.mark.asyncio
async def test_get_auto_campaign_cost_activity_metrics_shelf_bid_control_is_uncertain_when_total_cpo_ok() -> None:
    adv = _FakeAdvSetting(
        106,
        plan_for_sales_for_day=10,
        target_price_for_order=100,
        max_price_for_order=200,
        auto_shelf_bid_control_enabled=True,
    )
    reader = SimpleNamespace(
        get_latest_plan_fact=AsyncMock(
            return_value=_plan_fact_summary(
                fact_predict_orders=15.0,
                fact_pay_for_order=100.0,
                plan_fact_ch_ts_msk="01.01.2025 00:00",
            )
        )
    )

    with patch(
        "app.shared.domains.wb.utils.auto_campaign_cost_activity.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=150.0),
    ):
        metrics = await get_auto_campaign_cost_activity_metrics(
            adv,
            plan_fact_reader=reader,
        )

    assert metrics.target_cost == 100.0
    assert metrics.avg_cost == 150.0
    assert metrics.fact_pay_for_order == 100.0
    assert metrics.is_active is None
    assert metrics.cost_threshold_kind == "target"


@pytest.mark.asyncio
async def test_is_auto_campaign_active_returns_none_for_shelf_bid_control_without_plan_fact() -> None:
    adv = _FakeAdvSetting(
        103,
        plan_for_sales_for_day=10,
        target_price_for_order=100,
        max_price_for_order=200,
        auto_shelf_bid_control_enabled=True
    )
    reader = SimpleNamespace(get_latest_plan_fact=AsyncMock(return_value=None))

    with patch(
        "app.shared.domains."
        "wb.utils.auto_campaign_cost_activity."
        "full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=80.0),
    ):
        result = await is_auto_campaign_active(adv, plan_fact_reader=reader)

    assert result is None


@pytest.mark.asyncio
async def test_is_auto_campaign_active_returns_true_for_shelf_bid_control_when_avg_cost_below_target_without_total_cpo() -> None:
    adv = _FakeAdvSetting(
        108,
        plan_for_sales_for_day=10,
        target_price_for_order=100,
        max_price_for_order=200,
        auto_shelf_bid_control_enabled=True,
    )
    reader = SimpleNamespace(
        get_latest_plan_fact=AsyncMock(
            return_value=_plan_fact_summary(
                fact_predict_orders=15.0,
                fact_pay_for_order=None,
            )
        )
    )

    with patch(
        "app.shared.domains.wb.utils.auto_campaign_cost_activity.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=90.0),
    ):
        result = await is_auto_campaign_active(adv, plan_fact_reader=reader)

    assert result is True


@pytest.mark.asyncio
@pytest.mark.parametrize("fact_pay_for_order", [None, "bad", float("nan")])
async def test_is_auto_campaign_active_returns_none_for_shelf_bid_control_when_total_cpo_missing_or_bad(
    fact_pay_for_order: object,
) -> None:
    adv = _FakeAdvSetting(
        109,
        plan_for_sales_for_day=10,
        target_price_for_order=100,
        max_price_for_order=200,
        auto_shelf_bid_control_enabled=True,
    )
    reader = SimpleNamespace(
        get_latest_plan_fact=AsyncMock(
            return_value=_plan_fact_summary(
                fact_predict_orders=15.0,
                fact_pay_for_order=fact_pay_for_order,
            )
        )
    )

    with patch(
        "app.shared.domains.wb.utils.auto_campaign_cost_activity.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=150.0),
    ):
        result = await is_auto_campaign_active(adv, plan_fact_reader=reader)

    assert result is None


@pytest.mark.asyncio
@pytest.mark.parametrize("fact_predict_orders", [None, "bad", float("nan")])
async def test_is_auto_campaign_active_returns_none_when_fact_predict_orders_missing_or_bad(
    fact_predict_orders: object,
) -> None:
    adv = _FakeAdvSetting(
        110,
        plan_for_sales_for_day=10,
        target_price_for_order=100,
        max_price_for_order=200,
        auto_shelf_bid_control_enabled=True,
    )
    reader = SimpleNamespace(
        get_latest_plan_fact=AsyncMock(
            return_value=_plan_fact_summary(
                fact_predict_orders=fact_predict_orders,
                fact_pay_for_order=120.0,
            )
        )
    )

    with patch(
        "app.shared.domains.wb.utils.auto_campaign_cost_activity.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=150.0),
    ):
        result = await is_auto_campaign_active(adv, plan_fact_reader=reader)

    assert result is None

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
            return_value=_plan_fact_summary(
                fact_predict_orders=12.0,
                plan_fact_ch_ts_msk="07.06.2025 08:09",
            )
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
    assert metrics.plan_fact_ch_ts_msk == "07.06.2025 08:09"
    assert metrics.cost_threshold_kind == "target"


@pytest.mark.asyncio
async def test_get_auto_campaign_cost_activity_metrics_threshold_kind_target() -> None:
    adv = _FakeAdvSetting(
        201,
        plan_for_sales_for_day=10,
        target_price_for_order=100,
        max_price_for_order=300,
    )
    reader = SimpleNamespace(
        get_latest_plan_fact=AsyncMock(
            return_value=_plan_fact_summary(fact_predict_orders=15.0)
        )
    )
    with patch(
        "app.shared.domains.wb.utils.auto_campaign_cost_activity.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=50.0),
    ):
        metrics = await get_auto_campaign_cost_activity_metrics(
            adv,
            plan_fact_reader=reader,
        )
    assert metrics.target_cost == 100.0
    assert metrics.cost_threshold_kind == "target"


@pytest.mark.asyncio
async def test_get_auto_campaign_cost_activity_metrics_threshold_kind_max() -> None:
    adv = _FakeAdvSetting(
        202,
        plan_for_sales_for_day=10,
        target_price_for_order=100,
        max_price_for_order=300,
    )
    reader = SimpleNamespace(
        get_latest_plan_fact=AsyncMock(
            return_value=_plan_fact_summary(fact_predict_orders=5.0)
        )
    )
    with patch(
        "app.shared.domains.wb.utils.auto_campaign_cost_activity.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=50.0),
    ):
        metrics = await get_auto_campaign_cost_activity_metrics(
            adv,
            plan_fact_reader=reader,
        )
    assert metrics.target_cost == 300.0
    assert metrics.cost_threshold_kind == "max"

@pytest.mark.asyncio
async def test_cost_activity_with_complex_adv_uses_auto_cpo_not_aggregate() -> None:
    """Auto cost-activity обязан подтверждаться Auto CPO при наличии ComplexAdv."""
    adv = _FakeAdvSetting(
        109,
        plan_for_sales_for_day=10,
        target_price_for_order=100,
        max_price_for_order=200,
    )
    reader = SimpleNamespace(
        get_latest_plan_fact=AsyncMock(
            return_value=_plan_fact_summary(
                fact_predict_orders=15.0,
                fact_pay_for_order=999.0,
            )
        )
    )
    complex_adv = SimpleNamespace(auto_fact_cpo=80.0)

    with patch(
        "app.shared.domains.wb.utils.auto_campaign_cost_activity."
        "full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=150.0),
    ):
        metrics = await get_auto_campaign_cost_activity_metrics(
            adv,
            plan_fact_reader=reader,
            complex_adv=complex_adv,
        )

    assert metrics.fact_pay_for_order == 80.0
    assert metrics.is_active is None

@pytest.mark.asyncio
async def test_cost_activity_missing_auto_cpo_does_not_fallback_to_aggregate() -> None:
    """Missing Auto CPO остаётся unknown даже при плохом aggregate CPO."""
    adv = _FakeAdvSetting(
        110,
        plan_for_sales_for_day=10,
        target_price_for_order=100,
        max_price_for_order=200,
    )
    reader = SimpleNamespace(
        get_latest_plan_fact=AsyncMock(
            return_value=_plan_fact_summary(
                fact_predict_orders=15.0,
                fact_pay_for_order=999.0,
            )
        )
    )
    complex_adv = SimpleNamespace(auto_fact_cpo=None)

    with patch(
        "app.shared.domains.wb.utils.auto_campaign_cost_activity."
        "full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=150.0),
    ):
        metrics = await get_auto_campaign_cost_activity_metrics(
            adv,
            plan_fact_reader=reader,
            complex_adv=complex_adv,
        )

    assert metrics.fact_pay_for_order is None
    assert metrics.is_active is None
