"""Unit: уровни данных V3 (свои → агрегат РК → max по ключам → N-state)."""

from __future__ import annotations

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
    KeywordV3DecisionTier,
    keyword_lacks_v3_decision_data,
    resolve_keyword_v3_decision,
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
def test_full_tier_when_own_conv_and_ch() -> None:
    kw = _calculated_kw_fixture(
        ks_id=1, text="a", mode=KeywordStrategyMode.MIN_CPA, conv=0.05
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=_sample_profile())
    decision = resolve_keyword_v3_decision(ctx, [ctx])
    assert decision.tier == KeywordV3DecisionTier.FULL
    assert not decision.imputed
    assert not keyword_lacks_v3_decision_data(ctx, [ctx])


@pytest.mark.unit
def test_rk_aggregate_when_no_own_views_but_campaign_has() -> None:
    """Сначала агрегат РК (средневзвешенная conv), не peer_max."""
    dead = _calculated_kw_fixture(
        ks_id=1, text="dead", mode=KeywordStrategyMode.OFF, conv=0.0
    )
    dead_stat = dead.cluster_stat.model_copy(update={"views": 0, "conv_views_to_orders": 0.0})
    dead = dead.model_copy(update={"cluster_stat": dead_stat})
    alive = _calculated_kw_fixture(
        ks_id=2, text="alive", mode=KeywordStrategyMode.MIN_CPA, conv=0.12
    )
    profile = _sample_profile()
    dead_ctx = KeywordV3Context(keyword=dead, position_profile=profile)
    alive_ctx = KeywordV3Context(keyword=alive, position_profile=profile)
    contexts = [dead_ctx, alive_ctx]
    decision = resolve_keyword_v3_decision(dead_ctx, contexts)
    assert decision.tier == KeywordV3DecisionTier.RK_AGGREGATE
    assert decision.effective_conv_views_to_orders == pytest.approx(0.12)
    assert decision.imputed
    assert not keyword_lacks_v3_decision_data(dead_ctx, contexts)


@pytest.mark.unit
def test_peer_max_when_no_views_anywhere_but_conv_in_stat() -> None:
    """Нет показов в окне — max conv среди других ключей (если агрегат пуст)."""
    a = _calculated_kw_fixture(ks_id=1, text="a", mode=KeywordStrategyMode.OFF, conv=0.15)
    a_stat = a.cluster_stat.model_copy(update={"views": 0, "conv_views_to_orders": 0.15})
    a = a.model_copy(update={"cluster_stat": a_stat})
    b = _calculated_kw_fixture(ks_id=2, text="b", mode=KeywordStrategyMode.MIN_CPA, conv=0.09)
    b_stat = b.cluster_stat.model_copy(update={"views": 0, "conv_views_to_orders": 0.09})
    b = b.model_copy(update={"cluster_stat": b_stat})
    profile = _sample_profile()
    a_ctx = KeywordV3Context(keyword=a, position_profile=profile)
    b_ctx = KeywordV3Context(keyword=b, position_profile=profile)
    decision = resolve_keyword_v3_decision(a_ctx, [a_ctx, b_ctx])
    assert decision.tier == KeywordV3DecisionTier.PEER_MAX
    assert decision.effective_conv_views_to_orders == pytest.approx(0.09)


@pytest.mark.unit
def test_no_conv_tier_when_ch_but_no_imputation() -> None:
    """CH есть, conv нельзя импутировать — отдельный tier, не NO_CH_MATRIX."""
    kw = _calculated_kw_fixture(
        ks_id=1, text="solo", mode=KeywordStrategyMode.OFF, conv=0.0
    )
    stat = kw.cluster_stat.model_copy(update={"views": 0, "conv_views_to_orders": 0.0})
    kw = kw.model_copy(update={"cluster_stat": stat})
    profile = _sample_profile()
    ctx = KeywordV3Context(keyword=kw, position_profile=profile)
    decision = resolve_keyword_v3_decision(ctx, [ctx])
    assert decision.tier == KeywordV3DecisionTier.NO_CONV
    assert decision.has_ch_position_profile
    assert keyword_lacks_v3_decision_data(ctx, [ctx])


@pytest.mark.unit
def test_no_ch_matrix_triggers_n_state() -> None:
    kw = _calculated_kw_fixture(
        ks_id=1, text="a", mode=KeywordStrategyMode.OFF, conv=0.08
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=None)
    assert resolve_keyword_v3_decision(ctx, [ctx]).tier == KeywordV3DecisionTier.NO_CH_MATRIX
    assert keyword_lacks_v3_decision_data(ctx, [ctx])
