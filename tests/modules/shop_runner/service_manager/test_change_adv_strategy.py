from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.common_slaves.wildberries.models.enums.strategy import Strategy
from app.modules.shop_runner.service_manager.manager import CoroutinesManager
from app.modules.shop_runner.service_manager.services.adv_strategy_selector import (
    StrategySelection,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)


def _make_adv(
    *,
    adv_setting_original_id: int,
    adv_id: int,
    strategy: Strategy,
    bot_active: bool = True,
    auto_adv_active_status: bool = True,
    auto_update_strategy: bool = True,
    is_part_auto_setting_active: bool = True,
) -> SimpleNamespace:
    return SimpleNamespace(
        adv_setting_original_id=adv_setting_original_id,
        adv_id=adv_id,
        strategy=strategy,
        bot_active=bot_active,
        auto_adv_active_status=auto_adv_active_status,
        auto_update_strategy=auto_update_strategy,
        is_part_auto_setting_active=is_part_auto_setting_active,
    )


@pytest.mark.asyncio
async def test_change_adv_strategy_updates_only_started_and_enabled_campaigns() -> None:
    manager = CoroutinesManager.__new__(CoroutinesManager)
    manager.shop_id = "shop-1"
    manager._tasks_manager = MagicMock()
    manager._plan_fact_reader = MagicMock()
    manager._wb_shop_data_manager = SimpleNamespace(get_complex_advs=AsyncMock())
    manager._adv_strategy_selector = SimpleNamespace(select_target_strategy=AsyncMock())
    manager._apply_strategy_updates = AsyncMock()

    adv_needs_change = _make_adv(
        adv_setting_original_id=1,
        adv_id=101,
        strategy=Strategy.MIN_CPO,
        bot_active=True,
        auto_adv_active_status=True,
        auto_update_strategy=True,
    )
    adv_same_strategy = _make_adv(
        adv_setting_original_id=2,
        adv_id=102,
        strategy=Strategy.MAX_CONV,
        bot_active=True,
        auto_adv_active_status=True,
        auto_update_strategy=True,
    )
    adv_paused = _make_adv(
        adv_setting_original_id=3,
        adv_id=103,
        strategy=Strategy.MIN_CPO,
        bot_active=True,
        auto_adv_active_status=False,
        auto_update_strategy=False,
        is_part_auto_setting_active=False,
    )
    adv_disabled = _make_adv(
        adv_setting_original_id=4,
        adv_id=104,
        strategy=Strategy.MIN_CPO,
        bot_active=True,
        auto_adv_active_status=True,
        auto_update_strategy=False,
    )
    manager._wb_shop_data_manager.get_complex_advs.return_value = [
        adv_needs_change,
        adv_same_strategy,
        adv_paused,
        adv_disabled,
    ]

    async def _select_target_strategy(adv, *, plan_fact_reader):
        assert plan_fact_reader is manager._plan_fact_reader
        if adv is adv_needs_change:
            return StrategySelection(strategy=Strategy.MAX_CONV, reason="test_change")
        if adv is adv_same_strategy:
            return StrategySelection(strategy=Strategy.MAX_CONV, reason="same")
        raise AssertionError("Unexpected campaign passed to selector")

    manager._adv_strategy_selector.select_target_strategy.side_effect = _select_target_strategy

    async def _run_tasks(handlers, *args, **kwargs):
        results = []
        for handler in handlers:
            results.append(await handler())
        return results

    async def _mock_split_fresh(self, candidates, *, operation_name):
        return candidates, []

    with patch(
        "app.modules.shop_runner.service_manager.manager.run_tasks",
        new=_run_tasks,
    ), patch(
        "app.modules.shop_runner.service_manager.manager.CoroutinesManager._split_advs_by_stats_freshness",
        _mock_split_fresh,
    ):
        await manager.change_adv_strategy.__wrapped__(manager, only_bot_active=True)

    manager._apply_strategy_updates.assert_awaited_once_with(
        [(1, 101, Strategy.MIN_CPO, Strategy.MAX_CONV, "test_change")]
    )
    assert manager._adv_strategy_selector.select_target_strategy.await_count == 2


def test_complex_adv_auto_update_strategy_defaults_to_true_when_field_missing() -> None:
    adv_setting = SimpleNamespace(
        strategy=Strategy.MIN_CPO,
        auto_update_strategy=None,
        plan_for_sales_for_day=1,
        target_price_for_order=100,
        max_price_for_order=200,
    )
    complex_adv = ComplexAdv(
        adv_setting=adv_setting,
        search_adv=None,
    )

    assert complex_adv.auto_update_strategy is True
