"""Unit: ResetOverMaxCpoOnOverspendExecutor и cpo percent gate."""

from __future__ import annotations

from dataclasses import replace

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.reset_over_max_cpo_on_overspend import (
    ResetOverMaxCpoOnOverspendExecutor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.ladder_state_pick import (
    pick_max_ladder_state_at_or_below_cpo,
)
from tests.unit.auto_updater_v3.test_pay_for_order_over_max_off_on_deep_overspend_executor import (
    _adv_state,
    _context,
    _dto,
)


@pytest.mark.unit
def test_skip_when_cpo_percent_is_85() -> None:
    ctx = _context([_dto()], _adv_state(fact=85.0, max_cpo=100.0))
    executor = ResetOverMaxCpoOnOverspendExecutor()
    executor.execute(ctx)
    assert executor.skip_reason == "cpo_percent_lt_100"
    assert ctx.keywords[0].next_state == []


@pytest.mark.unit
def test_skip_when_cpo_percent_is_95() -> None:
    ctx = _context([_dto()], _adv_state(fact=95.0, max_cpo=100.0))
    executor = ResetOverMaxCpoOnOverspendExecutor()
    executor.execute(ctx)
    assert executor.skip_reason == "cpo_percent_lt_100"
    assert ctx.keywords[0].next_state == []


@pytest.mark.unit
def test_skip_when_max_cpo_is_none() -> None:
    ctx = _context([_dto()], _adv_state(fact=95.0, max_cpo=100.0))
    ctx.adv_state = replace(ctx.adv_state, max_pay_for_order=None)
    executor = ResetOverMaxCpoOnOverspendExecutor()
    executor.execute(ctx)
    assert executor.skip_reason == "no_current_cpo_percent"
    assert ctx.keywords[0].next_state == []


@pytest.mark.unit
def test_overspend_resets_expensive_ladder_cheap_trim() -> None:
    from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.keyword_v3_ladder_state import (
        KeywordV3LadderState,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.ladder_state_kind import (
        V3LadderStageKind,
    )

    cheap_states = (
        KeywordV3LadderState(
            keyword_setting_id=1,
            stage=V3LadderStageKind.OFF,
            strategy_mode=KeywordStrategyMode.OFF,
            target_position=0,
            cpo=None,
        ),
        KeywordV3LadderState(
            keyword_setting_id=1,
            stage=V3LadderStageKind.MIN_CPA,
            strategy_mode=KeywordStrategyMode.MIN_CPA,
            target_position=10,
            cpo=300.0,
        ),
        KeywordV3LadderState(
            keyword_setting_id=1,
            stage=V3LadderStageKind.OPTIMUM,
            strategy_mode=KeywordStrategyMode.OPTIMUM,
            target_position=20,
            cpo=600.0,
        ),
        KeywordV3LadderState(
            keyword_setting_id=1,
            stage=V3LadderStageKind.MAX_CONVERSION,
            strategy_mode=KeywordStrategyMode.MAX_CONVERSION,
            target_position=30,
            cpo=850.0,
        ),
    )
    expensive_states = (
        KeywordV3LadderState(
            keyword_setting_id=2,
            stage=V3LadderStageKind.OFF,
            strategy_mode=KeywordStrategyMode.OFF,
            target_position=0,
            cpo=None,
        ),
        KeywordV3LadderState(
            keyword_setting_id=2,
            stage=V3LadderStageKind.MIN_CPA,
            strategy_mode=KeywordStrategyMode.MIN_CPA,
            target_position=10,
            cpo=300.0,
        ),
        KeywordV3LadderState(
            keyword_setting_id=2,
            stage=V3LadderStageKind.OPTIMUM,
            strategy_mode=KeywordStrategyMode.OPTIMUM,
            target_position=20,
            cpo=850.0,
        ),
    )
    cheap_kw = _dto(ks_id=1, mode=KeywordStrategyMode.MAX_CONVERSION).calculated_keyword
    expensive_kw = _dto(
        ks_id=2, mode=KeywordStrategyMode.OPTIMUM, pfo_target=850.0
    ).calculated_keyword
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto import (
        KeywordDTO,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
        KeywordV3Context,
    )

    cheap = KeywordDTO.from_context(
        KeywordV3Context(keyword=cheap_kw, position_profile=None),
        ladder_states=cheap_states,
    )
    expensive = KeywordDTO.from_context(
        KeywordV3Context(keyword=expensive_kw, position_profile=None),
        ladder_states=expensive_states,
    )
    adv = replace(
        _adv_state(fact=800.0, max_cpo=500.0, guard_condition=True),
        guard_condition=True,
        v3_substitute_fact_cpo_for_max=True,
    )
    ctx = _context([cheap, expensive], adv)
    ResetOverMaxCpoOnOverspendExecutor().execute(ctx)
    assert cheap.current_mode == KeywordStrategyMode.OPTIMUM
    assert expensive.current_mode == KeywordStrategyMode.MIN_CPA


@pytest.mark.unit
def test_pick_max_ladder_state_includes_invalid_operable_state_for_trim() -> None:
    from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.keyword_v3_ladder_state import (
        KeywordV3LadderState,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.ladder_state_kind import (
        V3LadderStageKind,
    )

    states = (
        KeywordV3LadderState(
            keyword_setting_id=1,
            stage=V3LadderStageKind.OFF,
            strategy_mode=KeywordStrategyMode.OFF,
            target_position=0,
            cpo=None,
        ),
        KeywordV3LadderState(
            keyword_setting_id=1,
            stage=V3LadderStageKind.MIN_CPA,
            strategy_mode=KeywordStrategyMode.MIN_CPA,
            target_position=10,
            cpo=300.0,
        ),
        KeywordV3LadderState(
            keyword_setting_id=1,
            stage=V3LadderStageKind.OPTIMUM,
            strategy_mode=KeywordStrategyMode.OPTIMUM,
            target_position=20,
            cpo=400.0,
            is_valid=False,
        ),
        KeywordV3LadderState(
            keyword_setting_id=1,
            stage=V3LadderStageKind.MAX_CONVERSION,
            strategy_mode=KeywordStrategyMode.MAX_CONVERSION,
            target_position=30,
            cpo=800.0,
        ),
    )
    dto = _dto(ks_id=1, mode=KeywordStrategyMode.MAX_CONVERSION)
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto import (
        KeywordDTO,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
        KeywordV3Context,
    )

    dto = KeywordDTO.from_context(
        KeywordV3Context(keyword=dto.calculated_keyword, position_profile=None),
        ladder_states=states,
    )
    picked = pick_max_ladder_state_at_or_below_cpo(dto, 500.0, strict_ceiling=True)
    assert picked is not None
    assert picked.strategy_mode == KeywordStrategyMode.OPTIMUM
    assert picked.is_valid is False


@pytest.mark.unit
def test_not_skipped_when_cpo_percent_is_105() -> None:
    ctx = _context([_dto()], _adv_state(fact=105.0, max_cpo=100.0, guard_condition=True))
    executor = ResetOverMaxCpoOnOverspendExecutor()
    executor.execute(ctx)
    assert executor.skip_reason != "cpo_percent_lt_100"
