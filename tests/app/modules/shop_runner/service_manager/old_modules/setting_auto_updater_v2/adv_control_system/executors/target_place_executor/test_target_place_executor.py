"""Unit tests for target place executor helpers and executors."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.common_slaves.wildberries.models.enums import TargetPositionMode
from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.data_classes.data_classes import (
    ForceContext,
    PipelineContext,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.executors.target_place_executor import utils as tp_utils
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.executors.target_place_executor.target_place_down_executor import (
    TargetPlaceDownExecutor,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.executors.target_place_executor.target_place_up_executor import (
    TargetPlaceUpExecutor,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    SalesStates,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import KeywordStatus

pytestmark = pytest.mark.unit


def _plan_fact_ctx() -> tuple[PlanData, FactData]:
    plan = PlanData(orders=10, target_pay_for_order=100, max_pay_for_order=300)
    fact = FactData(
        predict_orders=5.0,
        pay_for_order=80.0,
        original_orders=5,
        fact_method=FactMethods.DIRECT_SALES,
    )
    return plan, fact


def _pipeline_ctx(*, complex_adv: MagicMock) -> PipelineContext:
    plan, fact = _plan_fact_ctx()
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return PipelineContext(
        complex_adv=complex_adv,
        plan=plan,
        fact=fact,
        session=session,
        state=SalesStates.OVERSPEND,
        force=ForceContext(value=1.0),
    )


def _keyword_mock(*, position: float, status: KeywordStatus = KeywordStatus.GOOD):
    kw = MagicMock()
    kw.status = status
    kw.position = position
    return kw


@pytest.mark.parametrize(
    ("auto_on", "search_on", "search_cpm", "auto_cpm", "expected"),
    [
        (True, True, 120, 90, 120),
        (True, True, None, 90, 90),
        (True, False, 99, 88, 88),
        (False, True, 77, 88, 77),
    ],
)
def test_get_current_cpm_branch_matrix(
    auto_on: bool,
    search_on: bool,
    search_cpm: int | None,
    auto_cpm: int,
    expected: int | None,
) -> None:
    adv = MagicMock()
    adv.is_bidder_for_search_adv_active = search_on
    adv.is_bidder_for_auto_cpm_active = auto_on
    adv.current_cpms.search_cpm = search_cpm
    adv.current_cpms.auto_cpm = auto_cpm
    assert tp_utils.get_current_cpm(adv) == expected


def test_get_current_cpm_returns_none_when_both_bidders_off() -> None:
    adv = MagicMock()
    adv.is_bidder_for_search_adv_active = False
    adv.is_bidder_for_auto_cpm_active = False
    assert tp_utils.get_current_cpm(adv) is None


@pytest.mark.asyncio
async def test_get_max_cpm_returns_complex_adv_max_user_cpm() -> None:
    adv = MagicMock()
    adv.max_user_cpm = 333
    assert await tp_utils.get_max_cpm(adv) == 333


@pytest.mark.asyncio
async def test_target_place_up_skips_when_position_control_disabled() -> None:
    adv = MagicMock()
    adv.individual_keywords_target_place_mode = False
    adv.is_target_position_control_enabled = False
    adv.adv_id = 1
    adv.db_id = 10
    adv.target_place = 50
    ctx = _pipeline_ctx(complex_adv=adv)
    with patch(
        "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2."
        "adv_control_system.executors.target_place_executor.target_place_up_executor.utils.get_current_cpm",
        return_value=50,
    ):
        result = await TargetPlaceUpExecutor().execute(ctx)
    assert result.success is False
    ctx.session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_target_place_up_skips_when_current_cpm_unknown() -> None:
    adv = MagicMock()
    adv.individual_keywords_target_place_mode = False
    adv.is_target_position_control_enabled = True
    adv.adv_id = 1
    ctx = _pipeline_ctx(complex_adv=adv)
    with patch(
        "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2."
        "adv_control_system.executors.target_place_executor.target_place_up_executor.utils.get_current_cpm",
        return_value=None,
    ):
        result = await TargetPlaceUpExecutor().execute(ctx)
    assert result.success is False


@pytest.mark.asyncio
async def test_target_place_up_skips_when_rate_limit_blocks() -> None:
    adv = MagicMock()
    adv.individual_keywords_target_place_mode = False
    adv.is_target_position_control_enabled = True
    adv.adv_id = 1
    adv.db_id = 99
    adv.target_place = 50
    ctx = _pipeline_ctx(complex_adv=adv)
    with (
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2."
            "adv_control_system.executors.target_place_executor.target_place_up_executor.utils.get_current_cpm",
            return_value=50,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2."
            "adv_control_system.executors.target_place_executor.target_place_up_executor.utils.get_max_cpm",
            new=AsyncMock(return_value=200),
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2."
            "adv_control_system.executors.target_place_executor.target_place_up_executor.LastTargetPlaceUpV2",
        ) as redis_cls,
    ):
        redis_inst = MagicMock()
        redis_inst.check_pass_time = AsyncMock(return_value=False)
        redis_cls.return_value = redis_inst
        result = await TargetPlaceUpExecutor().execute(ctx)
    assert result.success is False
    ctx.session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_target_place_up_updates_adv_when_allowed() -> None:
    adv = MagicMock()
    adv.individual_keywords_target_place_mode = False
    adv.is_target_position_control_enabled = True
    adv.adv_id = 1
    adv.db_id = 42
    adv.target_place = 50
    ctx = _pipeline_ctx(complex_adv=adv)
    with (
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2."
            "adv_control_system.executors.target_place_executor.target_place_up_executor.utils.get_current_cpm",
            return_value=50,
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2."
            "adv_control_system.executors.target_place_executor.target_place_up_executor.utils.get_max_cpm",
            new=AsyncMock(return_value=200),
        ),
        patch(
            "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2."
            "adv_control_system.executors.target_place_executor.target_place_up_executor.LastTargetPlaceUpV2",
        ) as redis_cls,
    ):
        redis_inst = MagicMock()
        redis_inst.check_pass_time = AsyncMock(return_value=True)
        redis_inst.set = AsyncMock()
        redis_cls.return_value = redis_inst
        result = await TargetPlaceUpExecutor().execute(ctx)
    assert result.success is True
    assert result.efficiency == 1.0
    ctx.session.execute.assert_awaited_once()
    ctx.session.commit.assert_awaited_once()
    redis_inst.set.assert_awaited_once()


@pytest.mark.asyncio
async def test_target_place_down_skips_when_position_control_disabled() -> None:
    adv = MagicMock()
    adv.individual_keywords_target_place_mode = False
    adv.is_target_position_control_enabled = False
    adv.adv_id = 1
    adv.get_keywords = AsyncMock(return_value=[_keyword_mock(position=40.0)])
    ctx = _pipeline_ctx(complex_adv=adv)
    result = await TargetPlaceDownExecutor().execute(ctx)
    assert result.success is False


@pytest.mark.asyncio
async def test_target_place_down_skips_when_no_good_keywords() -> None:
    adv = MagicMock()
    adv.individual_keywords_target_place_mode = False
    adv.is_target_position_control_enabled = True
    adv.adv_id = 1
    adv.get_keywords = AsyncMock(
        return_value=[_keyword_mock(position=40.0, status=KeywordStatus.BAD)]
    )
    ctx = _pipeline_ctx(complex_adv=adv)
    result = await TargetPlaceDownExecutor().execute(ctx)
    assert result.success is False


@pytest.mark.asyncio
async def test_target_place_down_updates_when_rate_limit_passes() -> None:
    adv = MagicMock()
    adv.individual_keywords_target_place_mode = False
    adv.is_target_position_control_enabled = True
    adv.adv_id = 1
    adv.db_id = 7
    adv.target_place = 10
    adv.get_keywords = AsyncMock(return_value=[_keyword_mock(position=99.0)])
    ctx = _pipeline_ctx(complex_adv=adv)
    with patch(
        "app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2."
        "adv_control_system.executors.target_place_executor.target_place_down_executor.LastTargetPlaceDownV2",
    ) as redis_cls:
        redis_inst = MagicMock()
        redis_inst.check_pass_time = AsyncMock(return_value=True)
        redis_inst.set = AsyncMock()
        redis_cls.return_value = redis_inst
        result = await TargetPlaceDownExecutor().execute(ctx)
    assert result.success is True
    ctx.session.execute.assert_awaited_once()
    ctx.session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_target_place_down_individual_mode_sets_min_cpa_when_needed() -> None:
    adv = MagicMock()
    adv.individual_keywords_target_place_mode = True
    adv.target_position_mode = TargetPositionMode.MAX_CART_TO_VIEWS_CONV
    adv.adv_setting_original_id = 55
    ctx = _pipeline_ctx(complex_adv=adv)
    result = await TargetPlaceDownExecutor().execute(ctx)
    assert result.success is True
    ctx.session.execute.assert_awaited_once()
    ctx.session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_target_place_up_individual_mode_noop_when_already_max_conv() -> None:
    adv = MagicMock()
    adv.individual_keywords_target_place_mode = True
    adv.target_position_mode = TargetPositionMode.MAX_CART_TO_VIEWS_CONV
    ctx = _pipeline_ctx(complex_adv=adv)
    result = await TargetPlaceUpExecutor().execute(ctx)
    assert result.success is False
    ctx.session.execute.assert_not_called()
