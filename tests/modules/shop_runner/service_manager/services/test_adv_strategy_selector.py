from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.modules.common_slaves.wildberries.models.enums.strategy import Strategy
from app.modules.shop_runner.service_manager.services.adv_strategy_selector import (
    AdvStrategySelector,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import KeywordStatus


def _make_complex_adv(
    *,
    rec_system_promotion_mode_active: bool,
    auto_adv_active_status: bool,
    plan_orders: int = 10,
    target_price_for_order: float = 100.0,
    max_price_for_order: float = 200.0,
    fact_orders: float = 5.0,
    fact_pay_for_order: float = 150.0,
    keywords: list[SimpleNamespace] | None = None,
    traffic_clicks_dto: SimpleNamespace | None = None,
) -> SimpleNamespace:
    adv_setting = SimpleNamespace(
        plan_for_sales_for_day=plan_orders,
        target_price_for_order=target_price_for_order,
        max_price_for_order=max_price_for_order,
    )
    keywords_result = keywords if keywords is not None else []
    return SimpleNamespace(
        adv_setting=adv_setting,
        adv_id=101,
        rec_system_promotion_mode_active=rec_system_promotion_mode_active,
        auto_adv_active_status=auto_adv_active_status,
        get_keywords=AsyncMock(return_value=keywords_result),
        traffic_clicks_dto=traffic_clicks_dto,
    )


def _plan_fact_reader(*, fact_orders: float, fact_pay_for_order: float) -> SimpleNamespace:
    return SimpleNamespace(
        get_latest_plan_fact=AsyncMock(
            return_value=SimpleNamespace(
                fact_predict_orders=fact_orders,
                fact_pay_for_order=fact_pay_for_order,
            )
        )
    )


@pytest.mark.asyncio
async def test_select_target_strategy_base_rule_orders_reached_plan_returns_min_cpo() -> None:
    selector = AdvStrategySelector()
    complex_adv = _make_complex_adv(
        rec_system_promotion_mode_active=False,
        auto_adv_active_status=True,
        plan_orders=10,
        fact_orders=12.0,
        fact_pay_for_order=50.0,
    )

    result = await selector.select_target_strategy(
        complex_adv,
        plan_fact_reader=_plan_fact_reader(fact_orders=12.0, fact_pay_for_order=50.0),
    )

    assert result is not None
    assert result.strategy == Strategy.MIN_CPO


@pytest.mark.asyncio
async def test_select_target_strategy_base_rule_cost_branches() -> None:
    selector = AdvStrategySelector()
    reader = _plan_fact_reader(fact_orders=4.0, fact_pay_for_order=220.0)

    complex_adv_high_cost = _make_complex_adv(
        rec_system_promotion_mode_active=False,
        auto_adv_active_status=True,
        plan_orders=10,
        target_price_for_order=100.0,
        max_price_for_order=200.0,
        fact_orders=4.0,
        fact_pay_for_order=220.0,
    )
    result_high = await selector.select_target_strategy(
        complex_adv_high_cost,
        plan_fact_reader=reader,
    )
    assert result_high is not None
    assert result_high.strategy == Strategy.MIN_CPO

    complex_adv_low_cost = _make_complex_adv(
        rec_system_promotion_mode_active=False,
        auto_adv_active_status=True,
        plan_orders=10,
        target_price_for_order=100.0,
        max_price_for_order=200.0,
        fact_orders=4.0,
        fact_pay_for_order=160.0,
    )
    result_low = await selector.select_target_strategy(
        complex_adv_low_cost,
        plan_fact_reader=_plan_fact_reader(fact_orders=4.0, fact_pay_for_order=160.0),
    )
    assert result_low is not None
    assert result_low.strategy == Strategy.MAX_CONV


@pytest.mark.asyncio
async def test_select_target_strategy_plan_and_cost_path_reads_plan_fact_once() -> None:
    selector = AdvStrategySelector()
    reader = _plan_fact_reader(fact_orders=4.0, fact_pay_for_order=160.0)
    complex_adv = _make_complex_adv(
        rec_system_promotion_mode_active=False,
        auto_adv_active_status=True,
        plan_orders=10,
        target_price_for_order=100.0,
        max_price_for_order=200.0,
        fact_orders=4.0,
        fact_pay_for_order=160.0,
    )

    result = await selector.select_target_strategy(
        complex_adv,
        plan_fact_reader=reader,
    )

    assert result is not None
    assert result.strategy == Strategy.MAX_CONV
    reader.get_latest_plan_fact.assert_awaited_once_with(complex_adv.adv_id)


@pytest.mark.asyncio
async def test_select_target_strategy_rec_mode_inactive_auto_falls_back_to_base_logic() -> None:
    selector = AdvStrategySelector()
    complex_adv = _make_complex_adv(
        rec_system_promotion_mode_active=True,
        auto_adv_active_status=False,
        plan_orders=10,
        target_price_for_order=100.0,
        max_price_for_order=200.0,
        fact_orders=5.0,
        fact_pay_for_order=160.0,
    )

    result = await selector.select_target_strategy(
        complex_adv,
        plan_fact_reader=_plan_fact_reader(fact_orders=5.0, fact_pay_for_order=160.0),
    )

    assert result is not None
    assert result.strategy == Strategy.MAX_CONV


@pytest.mark.asyncio
async def test_select_target_strategy_rec_mode_active_auto_not_all_shelf_keywords_enabled() -> None:
    selector = AdvStrategySelector()
    keywords = [
        SimpleNamespace(
            above_rec_conversion=True,
            hard_status=1,
            status=KeywordStatus.BAD,
        )
    ]
    complex_adv = _make_complex_adv(
        rec_system_promotion_mode_active=True,
        auto_adv_active_status=True,
        keywords=keywords,
    )

    result = await selector.select_target_strategy(
        complex_adv,
        plan_fact_reader=_plan_fact_reader(fact_orders=1.0, fact_pay_for_order=500.0),
    )

    assert result is not None
    assert result.strategy == Strategy.MIN_CPO


@pytest.mark.asyncio
async def test_select_target_strategy_rec_mode_active_auto_all_shelf_keywords_cost_exceeded_returns_min_cpo() -> None:
    """When cost is above target, MIN_CPO is returned even if all shelf keywords are enabled."""
    selector = AdvStrategySelector()
    keywords = [
        SimpleNamespace(
            above_rec_conversion=True,
            hard_status=1,
            status=KeywordStatus.GOOD,
        ),
        # Исключается из проверки (black-list)
        SimpleNamespace(
            above_rec_conversion=True,
            hard_status=0,
            status=KeywordStatus.BAD,
        ),
        # Исключается из проверки (turn-off)
        SimpleNamespace(
            above_rec_conversion=True,
            hard_status=3,
            status=KeywordStatus.BAD,
        ),
        # Не полочный ключ
        SimpleNamespace(
            above_rec_conversion=False,
            hard_status=1,
            status=KeywordStatus.BAD,
        ),
    ]
    complex_adv = _make_complex_adv(
        rec_system_promotion_mode_active=True,
        auto_adv_active_status=True,
        plan_orders=10,
        target_price_for_order=100.0,
        max_price_for_order=200.0,
        keywords=keywords,
    )

    # План не выполнен → целевая себестоимость = max_price_for_order (200). Нужно fact_pay_for_order > 200,
    # иначе (как при 4 заказах и 160) получится cost_below_or_equal_target / MAX_CONV, а не cost_above_target.
    result = await selector.select_target_strategy(
        complex_adv,
        plan_fact_reader=_plan_fact_reader(fact_orders=4.0, fact_pay_for_order=220.0),
    )

    assert result is not None
    assert result.strategy == Strategy.MIN_CPO
    assert result.reason == "cost_above_target"


def _all_shelf_keywords_with_exclusions() -> list[SimpleNamespace]:
    return [
        SimpleNamespace(
            above_rec_conversion=True,
            hard_status=1,
            status=KeywordStatus.GOOD,
        ),
        SimpleNamespace(
            above_rec_conversion=True,
            hard_status=0,
            status=KeywordStatus.BAD,
        ),
        SimpleNamespace(
            above_rec_conversion=True,
            hard_status=3,
            status=KeywordStatus.BAD,
        ),
        SimpleNamespace(
            above_rec_conversion=False,
            hard_status=1,
            status=KeywordStatus.BAD,
        ),
    ]


@pytest.mark.asyncio
async def test_select_target_strategy_rec_mode_active_auto_all_shelf_keywords_cost_ok_returns_max_conv() -> None:
    """When all shelf keywords are enabled and cost is not exceeded, MAX_CONV is returned."""
    selector = AdvStrategySelector()
    complex_adv = _make_complex_adv(
        rec_system_promotion_mode_active=True,
        auto_adv_active_status=True,
        plan_orders=10,
        target_price_for_order=100.0,
        max_price_for_order=200.0,
        fact_orders=1.0,
        fact_pay_for_order=150.0,
        keywords=_all_shelf_keywords_with_exclusions(),
    )

    result = await selector.select_target_strategy(
        complex_adv,
        plan_fact_reader=_plan_fact_reader(fact_orders=1.0, fact_pay_for_order=150.0),
    )

    assert result is not None
    assert result.strategy == Strategy.MAX_CONV
    assert result.reason == "all_shelf_keywords_activated"


@pytest.mark.asyncio
async def test_select_target_strategy_rec_mode_active_plan_fulfilled_all_shelf_good_returns_min_cpo() -> None:
    selector = AdvStrategySelector()
    keywords = [
        SimpleNamespace(
            above_rec_conversion=True,
            hard_status=1,
            status=KeywordStatus.GOOD,
        ),
    ]
    complex_adv = _make_complex_adv(
        rec_system_promotion_mode_active=True,
        auto_adv_active_status=True,
        plan_orders=10,
        target_price_for_order=100.0,
        max_price_for_order=200.0,
        keywords=keywords,
    )

    result = await selector.select_target_strategy(
        complex_adv,
        plan_fact_reader=_plan_fact_reader(fact_orders=12.0, fact_pay_for_order=50.0),
    )

    assert result is not None
    assert result.strategy == Strategy.MIN_CPO
    assert result.reason == "orders_reached_plan"


@pytest.mark.asyncio
async def test_select_target_strategy_rec_mode_active_cost_above_target_all_shelf_good_returns_min_cpo() -> None:
    selector = AdvStrategySelector()
    keywords = [
        SimpleNamespace(
            above_rec_conversion=True,
            hard_status=1,
            status=KeywordStatus.GOOD,
        ),
    ]
    complex_adv = _make_complex_adv(
        rec_system_promotion_mode_active=True,
        auto_adv_active_status=True,
        plan_orders=10,
        target_price_for_order=100.0,
        max_price_for_order=200.0,
        keywords=keywords,
    )

    result = await selector.select_target_strategy(
        complex_adv,
        plan_fact_reader=_plan_fact_reader(fact_orders=1.0, fact_pay_for_order=500.0),
    )

    assert result is not None
    assert result.strategy == Strategy.MIN_CPO
    assert result.reason == "cost_above_target"
