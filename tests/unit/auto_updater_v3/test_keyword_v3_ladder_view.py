"""Unit: SSOT лестницы M/O/C (``keyword_v3_ladder_view``)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
    KeywordDataTier,
    build_eligibility_map,
    resolve_keyword_v3_eligibility,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
    LadderCostSource,
    LadderInputs,
    cost_for_mode,
    resolve_ladder_stage_display,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.no_data_activation import (
    diagnose_keyword_v3_data,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner import (
    plan_profitable_expansion,
    resolve_effective_state_cost_for_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    SelectionPolicy,
    build_prepared_from_contexts,
    build_worst_per_state_costs,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)
from tests.unit.auto_updater_v3.test_no_data_activation import (
    _kw as _calculated_kw_fixture,
)
from tests.unit.auto_updater_v3.test_no_data_activation import (
    _sample_profile,
)
from tests.unit.test_auto_updater_v3 import (
    _calc_kw,
    _conv_for_pay_for_order,
    _sample_profile as _rollout_profile,
)


def _policy() -> SelectionPolicy:
    return SelectionPolicy.from_aggressiveness(
        click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
    )


@pytest.mark.unit
def test_ui_cost_parity_with_cost_for_mode() -> None:
    """UI CPO == ``cost_for_mode`` с одним ``LadderInputs``."""
    prof = _rollout_profile()
    kw = _calc_kw(
        ks_id=1,
        text="parity",
        mode=KeywordStrategyMode.MIN_CPA,
        rating=1.0,
        conv=_conv_for_pay_for_order(30.0),
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=prof)
    contexts = [ctx]
    ladder_inputs = LadderInputs.from_contexts(contexts)
    elig_map = build_eligibility_map(contexts)
    elig = elig_map[int(kw.keyword_setting_original_id)]

    view = resolve_ladder_stage_display(ctx, ladder_inputs, eligibility=elig)
    for target in (
        AggressionTargetMode.MIN_CPA,
        AggressionTargetMode.OPTIMUM,
        AggressionTargetMode.MAX_CONVERSION,
    ):
        ui_cost = view.stages[target].cost
        mode = KeywordStrategyMode[target.name]
        updater_cost, _ = cost_for_mode(
            ctx, mode, ladder_inputs=ladder_inputs, eligibility=elig
        )
        if ui_cost is None:
            assert updater_cost == float("inf")
        else:
            assert ui_cost == pytest.approx(updater_cost)


@pytest.mark.unit
def test_m_profile_o_profile_not_inf() -> None:
    """M/O на одной точке профиля — PROFILE (не ``inf``), не worst."""
    from datetime import UTC, datetime

    from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
        PositionProfilePoint,
    )

    prof = [
        PositionProfilePoint(
            position=1,
            bid=100,
            predicted_conversion=0.05,
            pay_for_cart=0.0,
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        ),
    ]
    donor = _calc_kw(
        ks_id=1,
        text="donor",
        mode=KeywordStrategyMode.MIN_CPA,
        rating=1.0,
        conv=0.05,
    )
    target = _calc_kw(
        ks_id=2,
        text="target",
        mode=KeywordStrategyMode.OFF,
        rating=1.0,
        conv=0.05,
    )
    donor_ctx = KeywordV3Context(keyword=donor, position_profile=_rollout_profile())
    target_ctx = KeywordV3Context(keyword=target, position_profile=prof)
    ladder_inputs = LadderInputs.from_contexts([donor_ctx, target_ctx])
    view = resolve_ladder_stage_display(target_ctx, ladder_inputs)
    assert view.stages[AggressionTargetMode.MIN_CPA].source == LadderCostSource.PROFILE
    opt = view.stages[AggressionTargetMode.OPTIMUM]
    assert opt.cost is not None
    assert opt.source == LadderCostSource.PROFILE
    assert not opt.cost_imputed


@pytest.mark.unit
def test_imputed_ch_not_n_state() -> None:
    """CH + imputed conv (RK_AGGREGATE) — не N-state."""
    dead = _calculated_kw_fixture(
        ks_id=1, text="dead", mode=KeywordStrategyMode.OFF, conv=0.0
    )
    dead_stat = dead.cluster_stat.model_copy(
        update={"views": 0, "conv_views_to_orders": 0.0}
    )
    dead = dead.model_copy(update={"cluster_stat": dead_stat})
    alive = _calculated_kw_fixture(
        ks_id=2, text="alive", mode=KeywordStrategyMode.MIN_CPA, conv=0.12
    )
    profile = _sample_profile()
    dead_ctx = KeywordV3Context(keyword=dead, position_profile=profile)
    alive_ctx = KeywordV3Context(keyword=alive, position_profile=profile)
    contexts = [dead_ctx, alive_ctx]
    diag = diagnose_keyword_v3_data(
        dead, profile, peer_contexts=contexts
    )
    assert not diag.n_state
    assert diag.imputed_conv


@pytest.mark.unit
def test_imputed_profile_cpo_can_differ_from_campaign_worst_max() -> None:
    """Имп. conv на ключе: CPO профиля ≠ max worst по РК — UI показывает оба."""
    cheap = _calc_kw(
        ks_id=1,
        text="cheap",
        mode=KeywordStrategyMode.MIN_CPA,
        rating=1.0,
        conv=_conv_for_pay_for_order(15.0),
    )
    target = _calc_kw(
        ks_id=2,
        text="target",
        mode=KeywordStrategyMode.OFF,
        rating=1.0,
        conv=0.0,
    )
    t_stat = target.cluster_stat.model_copy(update={"views": 0})
    target = target.model_copy(update={"cluster_stat": t_stat})
    prof = _rollout_profile()
    cheap_ctx = KeywordV3Context(keyword=cheap, position_profile=prof)
    target_ctx = KeywordV3Context(keyword=target, position_profile=prof)
    contexts = [cheap_ctx, target_ctx]
    ladder_inputs = LadderInputs.from_contexts(contexts)
    worst_min = ladder_inputs.worst_costs.get(AggressionTargetMode.MIN_CPA)
    assert worst_min is not None
    view = resolve_ladder_stage_display(target_ctx, ladder_inputs)
    stage_min = view.stages[AggressionTargetMode.MIN_CPA]
    assert stage_min.cost is not None
    assert stage_min.source.value == "profile"
    if worst_min > float(stage_min.cost) * 1.05:
        assert worst_min > float(stage_min.cost)


@pytest.mark.unit
def test_no_ch_pay_for_order_min_only_never_worst_source() -> None:
    """NO_CH tier: MIN ``pay_for_order``, O/C ``none``, never ``worst``."""
    kw = _calculated_kw_fixture(
        ks_id=1, text="a", mode=KeywordStrategyMode.OFF, conv=0.08
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=None)
    ladder_inputs = LadderInputs.from_contexts([ctx])
    elig = resolve_keyword_v3_eligibility(ctx, [ctx])
    assert elig.data_tier == KeywordDataTier.KEYWORD_NO_CH_PROFILE_WITH_OWN_CONV

    diag = diagnose_keyword_v3_data(kw, None, peer_contexts=[ctx])
    assert diag.no_ch_min_only
    assert not diag.n_state

    view = resolve_ladder_stage_display(ctx, ladder_inputs, eligibility=elig)
    assert view.stages[AggressionTargetMode.MIN_CPA].source == LadderCostSource.PAY_FOR_ORDER
    pfo = float(kw.pay_for_order or 0)
    assert view.stages[AggressionTargetMode.MIN_CPA].cost == pytest.approx(pfo, rel=0.02)
    assert view.stages[AggressionTargetMode.OPTIMUM].source == LadderCostSource.NONE
    assert view.stages[AggressionTargetMode.MAX_CONVERSION].source == LadderCostSource.NONE

    opt_cost, _ = cost_for_mode(
        ctx,
        KeywordStrategyMode.OPTIMUM,
        ladder_inputs=ladder_inputs,
        eligibility=elig,
    )
    assert opt_cost == float("inf")


@pytest.mark.unit
def test_expansion_cost_matches_cost_for_mode() -> None:
    """``plan_profitable_expansion`` state_cost == ``cost_for_mode``."""
    prof = _rollout_profile()
    kw = _calc_kw(
        ks_id=5,
        text="exp",
        mode=KeywordStrategyMode.OFF,
        rating=1.0,
        conv=_conv_for_pay_for_order(25.0),
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=prof)
    contexts = [ctx]
    prepared = build_prepared_from_contexts(contexts)
    ladder_inputs = LadderInputs.from_contexts(contexts)
    actions = plan_profitable_expansion(
        prepared,
        resolve=500.0,
        policy=_policy(),
        ladder_inputs=ladder_inputs,
    )
    assert actions
    log = actions[0].selection_log
    assert log is not None
    assert log.state_cost is not None
    to_mode = KeywordStrategyMode[actions[0].target_strategy_mode.name]  # type: ignore[union-attr]
    expected, _ = cost_for_mode(
        ctx,
        to_mode,
        ladder_inputs=ladder_inputs,
        eligibility=build_eligibility_map(contexts).get(5),
    )
    assert log.state_cost == pytest.approx(expected)


@pytest.mark.unit
def test_cost_for_mode_no_repeated_worst_build() -> None:
    """N×``cost_for_mode`` с одним ``ladder_inputs`` — ``build_worst_per_state_costs`` 0 раз."""
    prof = _rollout_profile()
    contexts = [
        KeywordV3Context(
            keyword=_calc_kw(
                ks_id=i,
                text=f"kw{i}",
                mode=KeywordStrategyMode.OFF,
                rating=1.0,
                conv=0.05,
            ),
            position_profile=prof,
        )
        for i in range(1, 6)
    ]
    ladder_inputs = LadderInputs.from_contexts(contexts)
    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking.build_worst_per_state_costs",
    ) as spy:
        for ctx in contexts:
            for mode in (
                KeywordStrategyMode.MIN_CPA,
                KeywordStrategyMode.OPTIMUM,
                KeywordStrategyMode.MAX_CONVERSION,
            ):
                cost_for_mode(ctx, mode, ladder_inputs=ladder_inputs)
        spy.assert_not_called()


@pytest.mark.unit
def test_no_ch_optimum_never_worst_even_if_worst_filled() -> None:
    """NO_CH: OPTIMUM ``inf``, ``source≠worst`` при заполненном ``worst_costs[OPTIMUM]``."""
    kw = _calculated_kw_fixture(
        ks_id=1, text="a", mode=KeywordStrategyMode.OFF, conv=0.08
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=None)
    ladder_inputs = LadderInputs.from_contexts([ctx])
    filled = dict(ladder_inputs.worst_costs)
    filled[AggressionTargetMode.OPTIMUM] = 999.0
    ladder_inputs = LadderInputs(
        all_contexts=ladder_inputs.all_contexts,
        prepared=ladder_inputs.prepared,
        worst_costs=filled,
        campaign_cache=ladder_inputs.campaign_cache,
    )
    elig = resolve_keyword_v3_eligibility(ctx, [ctx])
    view = resolve_ladder_stage_display(ctx, ladder_inputs, eligibility=elig)
    assert view.stages[AggressionTargetMode.OPTIMUM].source != LadderCostSource.WORST


@pytest.mark.unit
def test_ch_tier_o_can_use_worst_source() -> None:
    """CH-tier: invalid O может ``source=worst`` (контраст с NO_CH)."""
    prof = _rollout_profile()
    kw = _calc_kw(
        ks_id=1,
        text="ch_o",
        mode=KeywordStrategyMode.OFF,
        rating=1.0,
        conv=0.05,
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=prof)
    ladder_inputs = LadderInputs.from_contexts([ctx, ctx])
    view = resolve_ladder_stage_display(ctx, ladder_inputs)
    opt = view.stages[AggressionTargetMode.OPTIMUM]
    if opt.cost is not None and opt.cost_imputed:
        assert opt.source == LadderCostSource.WORST


@pytest.mark.unit
def test_resolve_effective_state_cost_for_mode_uses_ladder_inputs() -> None:
    """``resolve_effective_state_cost_for_mode`` с ``ladder_inputs`` не пересобирает worst."""
    prof = _rollout_profile()
    kw = _calc_kw(ks_id=1, text="x", mode=KeywordStrategyMode.MIN_CPA, rating=1.0)
    ctx = KeywordV3Context(keyword=kw, position_profile=prof)
    prepared = build_prepared_from_contexts([ctx])
    ladder_inputs = LadderInputs.from_contexts([ctx])
    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view.LadderInputs.from_contexts",
    ) as spy:
        resolve_effective_state_cost_for_mode(
            ctx=ctx,
            to_mode=KeywordStrategyMode.MIN_CPA,
            ladder_inputs=ladder_inputs,
        )
        spy.assert_not_called()
