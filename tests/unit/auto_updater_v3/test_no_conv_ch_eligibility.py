"""Unit: CH + NO_CONV → pessimistic worst ladder (не INVALID)."""

from __future__ import annotations

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
    KeywordDataTier,
    resolve_keyword_v3_eligibility,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
    LadderInputs,
    cost_for_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.no_data_activation import (
    diagnose_keyword_v3_data,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
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


@pytest.mark.unit
def test_no_conv_with_ch_eligibility_participates_in_ladder() -> None:
    """NO_CONV + CH → PESSIMISTIC_FALLBACK, не INVALID."""
    solo = _calculated_kw_fixture(
        ks_id=1, text="solo", mode=KeywordStrategyMode.OFF, conv=0.0
    )
    stat = solo.cluster_stat.model_copy(update={"views": 0, "conv_views_to_orders": 0.0})
    solo = solo.model_copy(update={"cluster_stat": stat})
    profile = _sample_profile()
    solo_ctx = KeywordV3Context(keyword=solo, position_profile=profile)
    elig = resolve_keyword_v3_eligibility(solo_ctx, [solo_ctx])
    assert elig.data_tier == KeywordDataTier.KEYWORD_PESSIMISTIC_FALLBACK
    assert elig.participates_in_ladder is True


@pytest.mark.unit
def test_no_conv_ch_uses_worst_from_donor() -> None:
    """Ключ без conv, донор с conv — CPO MIN через worst, не ``inf``."""
    donor = _calc_kw(
        ks_id=1,
        text="donor",
        mode=KeywordStrategyMode.MIN_CPA,
        rating=1.0,
        conv=_conv_for_pay_for_order(30.0),
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
    donor_ctx = KeywordV3Context(keyword=donor, position_profile=prof)
    target_ctx = KeywordV3Context(keyword=target, position_profile=prof)
    contexts = [donor_ctx, target_ctx]
    ladder_inputs = LadderInputs.from_contexts(contexts)
    elig = resolve_keyword_v3_eligibility(target_ctx, contexts)
    cost, imputed = cost_for_mode(
        target_ctx,
        KeywordStrategyMode.MIN_CPA,
        ladder_inputs=ladder_inputs,
        eligibility=elig,
    )
    assert cost != float("inf")
    diag = diagnose_keyword_v3_data(target, prof, peer_contexts=contexts)
    assert not diag.n_state
    assert diag.imputed_conv


@pytest.mark.unit
def test_no_ch_on_keyword_shows_campaign_worst_cpo() -> None:
    """Нет CH на ключе, донор с CH+conv — M/O/C CPO из worst_costs."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        resolve_ladder_stage_display,
    )

    donor = _calc_kw(
        ks_id=1,
        text="donor",
        mode=KeywordStrategyMode.MIN_CPA,
        rating=1.0,
        conv=_conv_for_pay_for_order(40.0),
    )
    target = _calc_kw(
        ks_id=2,
        text="solo_no_ch",
        mode=KeywordStrategyMode.OFF,
        rating=1.0,
        conv=0.0,
    )
    prof = _rollout_profile()
    donor_ctx = KeywordV3Context(keyword=donor, position_profile=prof)
    target_ctx = KeywordV3Context(keyword=target, position_profile=None)
    ladder_inputs = LadderInputs.from_contexts([donor_ctx, target_ctx])
    assert ladder_inputs.worst_costs.get(AggressionTargetMode.MIN_CPA) is not None
    view = resolve_ladder_stage_display(target_ctx, ladder_inputs)
    min_stage = view.stages[AggressionTargetMode.MIN_CPA]
    assert min_stage.is_valid
    assert min_stage.cost is not None
    assert min_stage.source.value == "worst"


@pytest.mark.unit
def test_invalid_eligibility_blocks_no_ch_worst_fallback() -> None:
    """KEYWORD_INVALID: worst по РК не показываем и не считаем finite cost."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
        KeywordDataTier,
        resolve_keyword_v3_eligibility,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        LadderCostSource,
        cost_for_mode,
        resolve_ladder_stage_display,
    )

    donor = _calc_kw(
        ks_id=1,
        text="donor",
        mode=KeywordStrategyMode.MIN_CPA,
        rating=1.0,
        conv=_conv_for_pay_for_order(40.0),
    )
    target = _calc_kw(
        ks_id=2,
        text="invalid_no_ch",
        mode=KeywordStrategyMode.OFF,
        rating=1.0,
        conv=0.0,
        cpm_set_bid=0,
    )
    stat = target.cluster_stat.model_copy(update={"views": 0, "conv_views_to_orders": 0.0})
    target = target.model_copy(update={"cluster_stat": stat})
    prof = _rollout_profile()
    donor_ctx = KeywordV3Context(keyword=donor, position_profile=prof)
    target_ctx = KeywordV3Context(keyword=target, position_profile=None)
    contexts = [donor_ctx, target_ctx]
    ladder_inputs = LadderInputs.from_contexts(contexts)
    elig = resolve_keyword_v3_eligibility(target_ctx, contexts)
    assert elig.data_tier == KeywordDataTier.KEYWORD_INVALID
    assert not elig.participates_in_ladder

    cost, _ = cost_for_mode(
        target_ctx,
        KeywordStrategyMode.MIN_CPA,
        ladder_inputs=ladder_inputs,
        eligibility=elig,
    )
    assert cost == float("inf")

    view = resolve_ladder_stage_display(
        target_ctx, ladder_inputs, eligibility=elig
    )
    min_stage = view.stages[AggressionTargetMode.MIN_CPA]
    assert not min_stage.is_valid
    assert min_stage.source == LadderCostSource.NONE
