"""Unit: NO_CONV / NO CH без worst-imputation — FULL / PFO / NO DATA."""

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
    LadderCostSource,
    LadderInputs,
    cost_for_mode,
    resolve_ladder_stage_display,
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


@pytest.mark.unit
def test_no_conv_with_ch_no_pfo_is_no_data() -> None:
    """CH без своей conv и без ``pay_for_order`` → NO DATA, не ladder."""
    solo = _calculated_kw_fixture(
        ks_id=1, text="solo", mode=KeywordStrategyMode.OFF, conv=0.0, cpm_set_bid=0
    )
    stat = solo.cluster_stat.model_copy(update={"views": 0, "conv_views_to_orders": 0.0})
    solo = solo.model_copy(update={"cluster_stat": stat})
    profile = _sample_profile()
    solo_ctx = KeywordV3Context(keyword=solo, position_profile=profile)
    elig = resolve_keyword_v3_eligibility(solo_ctx, [solo_ctx])
    assert elig.data_tier == KeywordDataTier.KEYWORD_NO_DATA
    assert not elig.participates_in_ladder


@pytest.mark.unit
def test_no_ch_without_pfo_cost_is_inf() -> None:
    """Нет CH и нет PFO — CPO недоступен (worst удалён)."""
    donor = _calculated_kw_fixture(
        ks_id=1, text="donor", mode=KeywordStrategyMode.MIN_CPA, conv=0.05
    )
    target = _calculated_kw_fixture(
        ks_id=2, text="target", mode=KeywordStrategyMode.OFF, conv=0.0, cpm_set_bid=0
    )
    t_stat = target.cluster_stat.model_copy(update={"views": 0})
    target = target.model_copy(update={"cluster_stat": t_stat})
    prof = _sample_profile()
    donor_ctx = KeywordV3Context(keyword=donor, position_profile=prof)
    target_ctx = KeywordV3Context(keyword=target, position_profile=None)
    contexts = [donor_ctx, target_ctx]
    ladder_inputs = LadderInputs.from_contexts(contexts)
    elig = resolve_keyword_v3_eligibility(target_ctx, contexts)
    assert elig.data_tier == KeywordDataTier.KEYWORD_NO_DATA
    cost, _imputed = cost_for_mode(
        target_ctx,
        KeywordStrategyMode.MIN_CPA,
        ladder_inputs=ladder_inputs,
        eligibility=elig,
    )
    assert cost == float("inf")


@pytest.mark.unit
def test_no_ch_with_pfo_uses_pay_for_order_only() -> None:
    """PFO tier: MIN через ``pay_for_order``, не worst."""
    target = _calculated_kw_fixture(
        ks_id=2, text="pfo", mode=KeywordStrategyMode.OFF, conv=0.08
    )
    target_ctx = KeywordV3Context(keyword=target, position_profile=None)
    contexts = [target_ctx]
    ladder_inputs = LadderInputs.from_contexts(contexts)
    elig = resolve_keyword_v3_eligibility(target_ctx, contexts)
    assert elig.data_tier == KeywordDataTier.KEYWORD_PFO
    view = resolve_ladder_stage_display(
        target_ctx, ladder_inputs, eligibility=elig
    )
    min_stage = view.stages[AggressionTargetMode.MIN_CPA]
    assert min_stage.is_valid
    assert min_stage.source == LadderCostSource.PAY_FOR_ORDER
    assert min_stage.cost is not None
