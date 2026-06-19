"""Unit: ClampStatesToResolveWhenNoEffectiveStepsExecutor."""

# pyright: reportPrivateUsage=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportCallIssue=false

from __future__ import annotations

from dataclasses import replace

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto import (
    KeywordDTO,
    UpdateContextManager,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    AdvState,
    KeywordsPreparedList,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.keyword_v3_ladder_state import (
    KeywordV3LadderState,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.ladder_state_kind import (
    V3LadderStageKind,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    SelectionPolicy,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.clamp_states_to_resolve_when_no_effective_steps import (
    ClampStatesToResolveWhenNoEffectiveStepsExecutor,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
    PositionProfilePoint,
)
from tests.unit.test_auto_updater_v3 import _calc_kw, _conv_for_pay_for_order, _sample_profile


def _ladder_states(
    ks_id: int,
    *,
    min_cpo: float | None = 300.0,
    opt_cpo: float | None = 400.0,
    max_cpo: float | None = 600.0,
) -> tuple[KeywordV3LadderState, ...]:
    """Return a standard CH-backed ladder used by resolve-clamp scenarios."""
    return (
        KeywordV3LadderState(
            keyword_setting_id=ks_id,
            stage=V3LadderStageKind.OFF,
            strategy_mode=KeywordStrategyMode.OFF,
            target_position=0,
            cpo=None,
        ),
        KeywordV3LadderState(
            keyword_setting_id=ks_id,
            stage=V3LadderStageKind.MIN_CPA,
            strategy_mode=KeywordStrategyMode.MIN_CPA,
            target_position=10,
            cpo=min_cpo,
        ),
        KeywordV3LadderState(
            keyword_setting_id=ks_id,
            stage=V3LadderStageKind.OPTIMUM,
            strategy_mode=KeywordStrategyMode.OPTIMUM,
            target_position=20,
            cpo=opt_cpo,
        ),
        KeywordV3LadderState(
            keyword_setting_id=ks_id,
            stage=V3LadderStageKind.MAX_CONVERSION,
            strategy_mode=KeywordStrategyMode.MAX_CONVERSION,
            target_position=30,
            cpo=max_cpo,
        ),
    )


def _dto(
    *,
    ks_id: int = 1,
    mode: KeywordStrategyMode = KeywordStrategyMode.MIN_CPA,
    ladder: tuple[KeywordV3LadderState, ...] | None = None,
    pay_for_order: float | None = None,
    position_profile: list[PositionProfilePoint] | None = None,
    target_place: int | None = None,
) -> KeywordDTO:
    """Construct a keyword DTO for CH-backed and no-CH resolve clamp tests."""
    conv = (
        _conv_for_pay_for_order(float(pay_for_order))
        if pay_for_order is not None
        else 0.05
    )
    kw = _calc_kw(
        ks_id=ks_id,
        text=f"kw{ks_id}",
        mode=mode,
        rating=1.0,
        hard_status=2,
        conv=conv,
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=position_profile)
    states = ladder if ladder is not None else _ladder_states(ks_id)
    if target_place is None:
        for state in states:
            if state.strategy_mode == mode and state.cpo is not None:
                target_place = int(state.target_position)
                break
    if target_place is not None:
        kw.keyword_setting.target_place = target_place
    return KeywordDTO.from_context(ctx, ladder_states=states)


def _adv_state(
    *,
    resolve: float = 500.0,
    max_effective_steps: int = 0,
    configured_keyword_calibration_max_step: int = 0,
    aggressiveness: V3RolloutAggressiveness = V3RolloutAggressiveness.MAX,
) -> AdvState:
    """Build an ``AdvState`` with the live resolve and calibration settings."""
    return replace(
        AdvState.empty(),
        resolve=resolve,
        resolve_valid=True,
        max_effective_steps=max_effective_steps,
        configured_keyword_calibration_max_step=(
            configured_keyword_calibration_max_step
        ),
        policy=SelectionPolicy.from_aggressiveness(
            click_mode=ShelfClickMode.ORGANIC_DOMINANT,
            aggressiveness=aggressiveness,
        ),
        shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=aggressiveness,
    )


def _context(*keywords: KeywordDTO, adv_state: AdvState | None = None):
    """Wrap keywords into a normal preamble ``UpdateContext``."""
    return UpdateContextManager().from_prepared(
        KeywordsPreparedList(keywords=list(keywords)),
        adv_state=adv_state or _adv_state(),
    )


@pytest.mark.unit
def test_ch_max_conversion_downgrades_to_min_when_above_resolve() -> None:
    dto = _dto(
        ks_id=1,
        mode=KeywordStrategyMode.MAX_CONVERSION,
        ladder=_ladder_states(1, min_cpo=300.0, opt_cpo=650.0, max_cpo=800.0),
        position_profile=_sample_profile(),
    )
    ctx = _context(dto, adv_state=_adv_state(resolve=500.0))
    ClampStatesToResolveWhenNoEffectiveStepsExecutor().execute(ctx)
    assert dto.current_mode == KeywordStrategyMode.MIN_CPA
    assert dto.current_target_place == 10


@pytest.mark.unit
def test_ch_optimum_downgrades_to_min_when_above_resolve() -> None:
    dto = _dto(
        ks_id=1,
        mode=KeywordStrategyMode.OPTIMUM,
        ladder=_ladder_states(1, min_cpo=300.0, opt_cpo=650.0, max_cpo=800.0),
        position_profile=_sample_profile(),
    )
    ctx = _context(dto, adv_state=_adv_state(resolve=500.0))
    ClampStatesToResolveWhenNoEffectiveStepsExecutor().execute(ctx)
    assert dto.current_mode == KeywordStrategyMode.MIN_CPA
    assert dto.current_target_place == 10


@pytest.mark.unit
def test_ch_min_cpa_noops_when_within_resolve() -> None:
    dto = _dto(
        ks_id=1,
        mode=KeywordStrategyMode.MIN_CPA,
        ladder=_ladder_states(1, min_cpo=300.0, opt_cpo=650.0, max_cpo=800.0),
        position_profile=_sample_profile(),
    )
    ctx = _context(dto, adv_state=_adv_state(resolve=500.0))
    ClampStatesToResolveWhenNoEffectiveStepsExecutor().execute(ctx)
    assert dto.current_mode == KeywordStrategyMode.MIN_CPA
    assert dto.next_state == []


@pytest.mark.unit
def test_ch_downgrades_to_off_when_no_economic_state_exists() -> None:
    dto = _dto(
        ks_id=1,
        mode=KeywordStrategyMode.MAX_CONVERSION,
        ladder=_ladder_states(1, min_cpo=700.0, opt_cpo=650.0, max_cpo=800.0),
        position_profile=_sample_profile(),
    )
    ctx = _context(dto, adv_state=_adv_state(resolve=500.0))
    ClampStatesToResolveWhenNoEffectiveStepsExecutor().execute(ctx)
    assert dto.current_mode == KeywordStrategyMode.OFF
    assert dto.target_place is None


@pytest.mark.unit
def test_ch_respects_aggression_cap_when_candidate_is_higher() -> None:
    dto = _dto(
        ks_id=1,
        mode=KeywordStrategyMode.MAX_CONVERSION,
        ladder=_ladder_states(1, min_cpo=300.0, opt_cpo=350.0, max_cpo=800.0),
        position_profile=_sample_profile(),
    )
    ctx = _context(
        dto,
        adv_state=_adv_state(
            resolve=500.0,
            aggressiveness=V3RolloutAggressiveness.MIN,
        ),
    )
    ClampStatesToResolveWhenNoEffectiveStepsExecutor().execute(ctx)
    assert dto.current_mode == KeywordStrategyMode.MIN_CPA
    assert dto.current_target_place == 10


@pytest.mark.unit
def test_ch_unknown_current_cost_downgrades_to_valid_target() -> None:
    dto = _dto(
        ks_id=1,
        mode=KeywordStrategyMode.MAX_CONVERSION,
        ladder=(
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
                cpo=None,
            ),
            KeywordV3LadderState(
                keyword_setting_id=1,
                stage=V3LadderStageKind.MAX_CONVERSION,
                strategy_mode=KeywordStrategyMode.MAX_CONVERSION,
                target_position=30,
                cpo=None,
            ),
        ),
        position_profile=_sample_profile(),
        target_place=30,
    )
    ctx = _context(dto, adv_state=_adv_state(resolve=500.0))
    ClampStatesToResolveWhenNoEffectiveStepsExecutor().execute(ctx)
    assert dto.current_mode == KeywordStrategyMode.MIN_CPA
    assert dto.current_target_place == 10


@pytest.mark.unit
def test_ch_unknown_current_cost_goes_off_when_no_valid_target_exists() -> None:
    dto = _dto(
        ks_id=1,
        mode=KeywordStrategyMode.MAX_CONVERSION,
        ladder=(
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
                is_valid=False,
            ),
            KeywordV3LadderState(
                keyword_setting_id=1,
                stage=V3LadderStageKind.OPTIMUM,
                strategy_mode=KeywordStrategyMode.OPTIMUM,
                target_position=20,
                cpo=650.0,
            ),
            KeywordV3LadderState(
                keyword_setting_id=1,
                stage=V3LadderStageKind.MAX_CONVERSION,
                strategy_mode=KeywordStrategyMode.MAX_CONVERSION,
                target_position=30,
                cpo=None,
            ),
        ),
        position_profile=_sample_profile(),
        target_place=30,
    )
    ctx = _context(dto, adv_state=_adv_state(resolve=500.0))
    ClampStatesToResolveWhenNoEffectiveStepsExecutor().execute(ctx)
    assert dto.current_mode == KeywordStrategyMode.OFF


@pytest.mark.unit
def test_ch_resolve_invalid_is_noop() -> None:
    dto = _dto(
        ks_id=1,
        mode=KeywordStrategyMode.MAX_CONVERSION,
        ladder=_ladder_states(1, min_cpo=300.0, opt_cpo=350.0, max_cpo=800.0),
        position_profile=_sample_profile(),
        target_place=30,
    )
    ctx = _context(
        dto,
        adv_state=_adv_state(resolve=500.0, max_effective_steps=2),
    )
    ctx.adv_state.resolve_valid = False
    ClampStatesToResolveWhenNoEffectiveStepsExecutor().execute(ctx)
    assert dto.current_mode == KeywordStrategyMode.MAX_CONVERSION
    assert dto.next_state == []


@pytest.mark.unit
def test_ch_invalid_state_below_resolve_is_not_selected() -> None:
    dto = _dto(
        ks_id=1,
        mode=KeywordStrategyMode.OPTIMUM,
        ladder=(
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
                is_valid=False,
            ),
            KeywordV3LadderState(
                keyword_setting_id=1,
                stage=V3LadderStageKind.OPTIMUM,
                strategy_mode=KeywordStrategyMode.OPTIMUM,
                target_position=20,
                cpo=650.0,
            ),
        ),
        position_profile=_sample_profile(),
        target_place=20,
    )
    ctx = _context(dto, adv_state=_adv_state(resolve=500.0))
    ClampStatesToResolveWhenNoEffectiveStepsExecutor().execute(ctx)
    assert dto.current_mode == KeywordStrategyMode.OFF


@pytest.mark.unit
def test_ch_prefers_valid_candidate_over_invalid_one() -> None:
    dto = _dto(
        ks_id=1,
        mode=KeywordStrategyMode.MAX_CONVERSION,
        ladder=(
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
                is_valid=False,
            ),
            KeywordV3LadderState(
                keyword_setting_id=1,
                stage=V3LadderStageKind.OPTIMUM,
                strategy_mode=KeywordStrategyMode.OPTIMUM,
                target_position=20,
                cpo=350.0,
            ),
            KeywordV3LadderState(
                keyword_setting_id=1,
                stage=V3LadderStageKind.MAX_CONVERSION,
                strategy_mode=KeywordStrategyMode.MAX_CONVERSION,
                target_position=30,
                cpo=800.0,
            ),
        ),
        position_profile=_sample_profile(),
        target_place=30,
    )
    ctx = _context(dto, adv_state=_adv_state(resolve=500.0))
    ClampStatesToResolveWhenNoEffectiveStepsExecutor().execute(ctx)
    assert dto.current_mode == KeywordStrategyMode.OPTIMUM
    assert dto.current_target_place == 20


@pytest.mark.unit
def test_pfo_active_above_resolve_goes_off() -> None:
    dto = _dto(
        ks_id=2,
        mode=KeywordStrategyMode.MIN_CPA,
        pay_for_order=600.0,
        position_profile=None,
        ladder=(
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
                target_position=0,
                cpo=600.0,
            ),
        ),
    )
    ctx = _context(dto, adv_state=_adv_state(resolve=500.0))
    ClampStatesToResolveWhenNoEffectiveStepsExecutor().execute(ctx)
    assert dto.current_mode == KeywordStrategyMode.OFF
    assert dto.target_place == 0


@pytest.mark.unit
def test_pfo_active_within_resolve_is_unchanged() -> None:
    dto = _dto(
        ks_id=2,
        mode=KeywordStrategyMode.MIN_CPA,
        pay_for_order=400.0,
        position_profile=None,
        ladder=(
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
                target_position=0,
                cpo=400.0,
            ),
        ),
    )
    ctx = _context(dto, adv_state=_adv_state(resolve=500.0))
    ClampStatesToResolveWhenNoEffectiveStepsExecutor().execute(ctx)
    assert dto.current_mode == KeywordStrategyMode.MIN_CPA
    assert dto.next_state == []


@pytest.mark.unit
def test_configured_steps_gt_zero_skips_even_when_runtime_effective_is_zero() -> None:
    dto = _dto(
        ks_id=1,
        mode=KeywordStrategyMode.MAX_CONVERSION,
        ladder=_ladder_states(1, min_cpo=300.0, opt_cpo=650.0, max_cpo=800.0),
        position_profile=_sample_profile(),
    )
    ctx = _context(
        dto,
        adv_state=_adv_state(
            resolve=500.0,
            max_effective_steps=0,
            configured_keyword_calibration_max_step=20,
        ),
    )
    executor = ClampStatesToResolveWhenNoEffectiveStepsExecutor()
    executor.execute(ctx)
    assert executor.skip_reason == "configured_steps_gt_0"
    assert dto.current_mode == KeywordStrategyMode.MAX_CONVERSION
    assert dto.next_state == []


@pytest.mark.unit
def test_configured_steps_gt_zero_skips_when_runtime_effective_positive() -> None:
    dto = _dto(
        ks_id=1,
        mode=KeywordStrategyMode.MAX_CONVERSION,
        ladder=_ladder_states(1, min_cpo=300.0, opt_cpo=650.0, max_cpo=800.0),
        position_profile=_sample_profile(),
    )
    ctx = _context(
        dto,
        adv_state=_adv_state(
            resolve=500.0,
            max_effective_steps=20,
            configured_keyword_calibration_max_step=20,
        ),
    )
    executor = ClampStatesToResolveWhenNoEffectiveStepsExecutor()
    executor.execute(ctx)
    assert executor.skip_reason == "configured_steps_gt_0"
    assert dto.next_state == []


@pytest.mark.unit
def test_configured_zero_clamps_even_when_runtime_effective_positive() -> None:
    dto = _dto(
        ks_id=1,
        mode=KeywordStrategyMode.MAX_CONVERSION,
        ladder=_ladder_states(1, min_cpo=300.0, opt_cpo=350.0, max_cpo=800.0),
        position_profile=_sample_profile(),
    )
    ctx = _context(
        dto,
        adv_state=_adv_state(
            resolve=500.0,
            max_effective_steps=20,
            configured_keyword_calibration_max_step=0,
        ),
    )
    executor = ClampStatesToResolveWhenNoEffectiveStepsExecutor()
    executor.execute(ctx)
    assert executor.skip_reason is None
    assert dto.current_mode == KeywordStrategyMode.OPTIMUM
    assert dto.current_target_place == 20


@pytest.mark.unit
def test_configured_default_one_skips_without_explicit_zero() -> None:
    dto = _dto(
        ks_id=1,
        mode=KeywordStrategyMode.MAX_CONVERSION,
        ladder=_ladder_states(1, min_cpo=300.0, opt_cpo=650.0, max_cpo=800.0),
        position_profile=_sample_profile(),
    )
    ctx = _context(
        dto,
        adv_state=replace(
            _adv_state(resolve=500.0, max_effective_steps=0),
            configured_keyword_calibration_max_step=1,
        ),
    )
    executor = ClampStatesToResolveWhenNoEffectiveStepsExecutor()
    executor.execute(ctx)
    assert executor.skip_reason == "configured_steps_gt_0"
    assert dto.next_state == []


@pytest.mark.unit
def test_adv_32824944_like_scenario_skips_clamp() -> None:
    dto = _dto(
        ks_id=1,
        mode=KeywordStrategyMode.MAX_CONVERSION,
        ladder=_ladder_states(1, min_cpo=300.0, opt_cpo=800.0, max_cpo=900.0),
        position_profile=_sample_profile(),
    )
    ctx = _context(
        dto,
        adv_state=_adv_state(
            resolve=750.0,
            max_effective_steps=20,
            configured_keyword_calibration_max_step=20,
        ),
    )
    executor = ClampStatesToResolveWhenNoEffectiveStepsExecutor()
    executor.execute(ctx)
    assert executor.skip_reason == "configured_steps_gt_0"
    assert dto.current_mode == KeywordStrategyMode.MAX_CONVERSION
    assert dto.next_state == []


@pytest.mark.unit
def test_final_clamp_instance_skips_when_configured_gt_zero() -> None:
    dto = _dto(
        ks_id=1,
        mode=KeywordStrategyMode.MAX_CONVERSION,
        ladder=_ladder_states(1, min_cpo=300.0, opt_cpo=650.0, max_cpo=800.0),
        position_profile=_sample_profile(),
    )
    ctx = _context(
        dto,
        adv_state=_adv_state(
            resolve=500.0,
            configured_keyword_calibration_max_step=20,
        ),
    )
    executor = ClampStatesToResolveWhenNoEffectiveStepsExecutor(
        phase_name="final_clamp_states_to_resolve",
    )
    executor.execute(ctx)
    assert executor.skip_reason == "configured_steps_gt_0"
    assert dto.next_state == []


@pytest.mark.unit
def test_enabled_effective_steps_do_not_trigger_clamp_when_configured_gt_zero() -> None:
    dto = _dto(
        ks_id=1,
        mode=KeywordStrategyMode.MAX_CONVERSION,
        ladder=_ladder_states(1, min_cpo=300.0, opt_cpo=350.0, max_cpo=800.0),
        position_profile=_sample_profile(),
    )
    ctx = _context(
        dto,
        adv_state=_adv_state(
            resolve=500.0,
            max_effective_steps=2,
            configured_keyword_calibration_max_step=20,
        ),
    )
    executor = ClampStatesToResolveWhenNoEffectiveStepsExecutor()
    executor.execute(ctx)
    assert executor.skip_reason == "configured_steps_gt_0"
    assert dto.current_mode == KeywordStrategyMode.MAX_CONVERSION
    assert dto.next_state == []
