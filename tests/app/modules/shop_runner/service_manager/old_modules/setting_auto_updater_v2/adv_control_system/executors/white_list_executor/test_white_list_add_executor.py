"""Unit tests for WhiteListAddExecutor."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.keywords_manager.keywords_manager import KeywordsManager
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.data_classes.data_classes import (
    ForceContext,
    PipelineContext,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.executors.white_list_executor.white_list_add_executor import (
    WhiteListAddExecutor,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    SalesStates,
)

pytestmark = pytest.mark.unit


def _ctx(
    *,
    plan_orders: int = 10,
    target_pay: int = 100,
    max_pay: int = 300,
    predict_orders: float = 5.0,
    pay_for_order: float | None = 80.0,
) -> PipelineContext:
    adv = MagicMock()
    adv.adv_id = 500
    adv.adv_setting = MagicMock()
    plan = PlanData(
        orders=plan_orders,
        target_pay_for_order=target_pay,
        max_pay_for_order=max_pay,
    )
    fact = FactData(
        predict_orders=predict_orders,
        pay_for_order=pay_for_order,
        original_orders=5,
        fact_method=FactMethods.DIRECT_SALES,
    )
    session = MagicMock()
    session.execute = AsyncMock()
    return PipelineContext(
        complex_adv=adv,
        plan=plan,
        fact=fact,
        session=session,
        state=SalesStates.UNDERPERFORM,
        force=ForceContext(value=1.0),
    )


def _candidate(*, ks_id: int, rating: float, text: str = "kw") -> MagicMock:
    kw = MagicMock()
    kw.keyword_setting_original_id = ks_id
    kw.rating = rating
    kw.text = text
    return kw


@pytest.mark.asyncio
async def test_white_list_add_skips_when_rate_limited() -> None:
    ctx = _ctx()
    with (
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2."
            "adv_control_system.executors.white_list_executor.white_list_add_executor.LastAutoAddPhraseToWhiteListV2",
        ) as redis_cls,
        patch.object(
            KeywordsManager,
            "get_candidates_to_white_list",
            new=AsyncMock(return_value=[_candidate(ks_id=1, rating=1.0)]),
        ),
    ):
        redis_inst = MagicMock()
        redis_inst.check_pass_time = AsyncMock(return_value=False)
        redis_cls.return_value = redis_inst
        result = await WhiteListAddExecutor().execute(ctx)
    assert result.success is False
    ctx.session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_white_list_add_skips_when_pay_above_threshold() -> None:
    """Plan not met → target cost uses max_pay; threshold = 0.9 * max."""
    ctx = _ctx(predict_orders=5.0, pay_for_order=270.0, max_pay=300)
    with (
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2."
            "adv_control_system.executors.white_list_executor.white_list_add_executor.LastAutoAddPhraseToWhiteListV2",
        ) as redis_cls,
        patch.object(
            KeywordsManager,
            "get_candidates_to_white_list",
            new=AsyncMock(return_value=[_candidate(ks_id=1, rating=9.0)]),
        ),
    ):
        redis_inst = MagicMock()
        redis_inst.check_pass_time = AsyncMock(return_value=True)
        redis_cls.return_value = redis_inst
        result = await WhiteListAddExecutor().execute(ctx)
    assert result.success is False
    ctx.session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_white_list_add_skips_when_no_candidates() -> None:
    ctx = _ctx()
    with (
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2."
            "adv_control_system.executors.white_list_executor.white_list_add_executor.LastAutoAddPhraseToWhiteListV2",
        ) as redis_cls,
        patch.object(
            KeywordsManager,
            "get_candidates_to_white_list",
            new=AsyncMock(return_value=[]),
        ),
    ):
        redis_inst = MagicMock()
        redis_inst.check_pass_time = AsyncMock(return_value=True)
        redis_cls.return_value = redis_inst
        result = await WhiteListAddExecutor().execute(ctx)
    assert result.success is False


@pytest.mark.asyncio
async def test_white_list_add_updates_best_candidate_by_rating() -> None:
    ctx = _ctx()
    low = _candidate(ks_id=1, rating=1.0, text="low")
    high = _candidate(ks_id=2, rating=9.0, text="high")
    with (
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2."
            "adv_control_system.executors.white_list_executor.white_list_add_executor.LastAutoAddPhraseToWhiteListV2",
        ) as redis_cls,
        patch.object(
            KeywordsManager,
            "get_candidates_to_white_list",
            new=AsyncMock(return_value=[low, high]),
        ),
    ):
        redis_inst = MagicMock()
        redis_inst.check_pass_time = AsyncMock(return_value=True)
        redis_inst.set = AsyncMock()
        redis_cls.return_value = redis_inst
        result = await WhiteListAddExecutor().execute(ctx)
    assert result.success is True
    ctx.session.execute.assert_awaited_once()
    redis_inst.set.assert_awaited_once()


@pytest.mark.asyncio
async def test_white_list_add_skips_when_fact_pay_for_order_is_none() -> None:
    ctx = _ctx(pay_for_order=None)
    with (
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2."
            "adv_control_system.executors.white_list_executor.white_list_add_executor.LastAutoAddPhraseToWhiteListV2",
        ) as redis_cls,
        patch.object(
            KeywordsManager,
            "get_candidates_to_white_list",
            new=AsyncMock(return_value=[_candidate(ks_id=1, rating=1.0)]),
        ),
    ):
        redis_inst = MagicMock()
        redis_inst.check_pass_time = AsyncMock(return_value=True)
        redis_cls.return_value = redis_inst
        result = await WhiteListAddExecutor().execute(ctx)
    assert result.success is False
