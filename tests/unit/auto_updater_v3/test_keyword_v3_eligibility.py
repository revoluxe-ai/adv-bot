"""Unit: KeywordDataTier, eligibility helpers, can_target_mode."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
    keyword_has_v2_cpo,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
    _weighted_campaign_conv,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
    KeywordDataTier,
    build_eligibility_map,
    build_target_place_fallback_zero_by_keyword_id,
    can_target_mode,
    resolve_keyword_v3_eligibility,
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
def test_can_target_mode_rejects_off() -> None:
    kw = _calculated_kw_fixture(
        ks_id=1, text="a", mode=KeywordStrategyMode.MIN_CPA, conv=0.05
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=_sample_profile())
    elig = resolve_keyword_v3_eligibility(ctx, [ctx])
    assert not can_target_mode(elig, KeywordStrategyMode.OFF)


@pytest.mark.unit
def test_eligibility_no_ch_own_conv_allowed_modes_min_only() -> None:
    kw = _calculated_kw_fixture(
        ks_id=1, text="a", mode=KeywordStrategyMode.OFF, conv=0.08
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=None)
    elig = resolve_keyword_v3_eligibility(ctx, [ctx])
    assert elig.data_tier == KeywordDataTier.KEYWORD_NO_CH_PROFILE_WITH_OWN_CONV
    assert elig.allowed_modes == frozenset({KeywordStrategyMode.MIN_CPA})
    assert elig.participates_in_ladder is True
    assert elig.target_place_fallback_zero is True
    assert can_target_mode(elig, KeywordStrategyMode.MIN_CPA)
    assert not can_target_mode(elig, KeywordStrategyMode.OPTIMUM)


@pytest.mark.unit
def test_keyword_has_v2_cpo_from_pay_for_order_without_views() -> None:
    """V2 CPO через pay_for_order/conv+cpm, даже без показов в окне."""
    kw = _calculated_kw_fixture(
        ks_id=2, text="b", mode=KeywordStrategyMode.OFF, conv=0.05, cpm_set_bid=200
    )
    stat = kw.cluster_stat.model_copy(update={"views": 0, "conv_views_to_orders": 0.05})
    kw = kw.model_copy(update={"cluster_stat": stat})
    assert keyword_has_v2_cpo(kw)
    ctx = KeywordV3Context(keyword=kw, position_profile=None)
    elig = resolve_keyword_v3_eligibility(ctx, [ctx])
    assert elig.data_tier == KeywordDataTier.KEYWORD_NO_CH_PROFILE_WITH_OWN_CONV
    assert elig.fallback_kind == "v2_cpo"


@pytest.mark.unit
def test_eligibility_invalid_empty_allowed_modes() -> None:
    kw = _calculated_kw_fixture(
        ks_id=1, text="solo", mode=KeywordStrategyMode.OFF, conv=0.0, cpm_set_bid=0
    )
    stat = kw.cluster_stat.model_copy(update={"views": 0, "conv_views_to_orders": 0.0})
    kw = kw.model_copy(update={"cluster_stat": stat})
    ctx = KeywordV3Context(keyword=kw, position_profile=_sample_profile())
    elig = resolve_keyword_v3_eligibility(ctx, [ctx])
    assert elig.data_tier == KeywordDataTier.KEYWORD_INVALID
    assert elig.allowed_modes == frozenset()
    assert not elig.participates_in_ladder


@pytest.mark.unit
def test_build_eligibility_map_computes_weighted_conv_once() -> None:
    """Один агрегат РК на ``build_eligibility_map``, не на каждый ключ без своей conv."""
    kw_a = _calculated_kw_fixture(
        ks_id=10, text="a", mode=KeywordStrategyMode.MIN_CPA, conv=0.05
    )
    kw_b = _calculated_kw_fixture(
        ks_id=11, text="b", mode=KeywordStrategyMode.MIN_CPA, conv=0.04
    )
    contexts = [
        KeywordV3Context(keyword=kw_a, position_profile=_sample_profile()),
        KeywordV3Context(keyword=kw_b, position_profile=_sample_profile()),
    ]
    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data._weighted_campaign_conv",
        wraps=_weighted_campaign_conv,
    ) as weighted_mock:
        result = build_eligibility_map(contexts)

    assert weighted_mock.call_count == 1
    assert len(result) == 2


@pytest.mark.unit
def test_build_target_place_fallback_zero_computes_weighted_conv_once() -> None:
    """Один агрегат РК на вызов; результат совпадает с ``build_eligibility_map``."""
    kw_a = _calculated_kw_fixture(
        ks_id=10, text="a", mode=KeywordStrategyMode.MIN_CPA, conv=0.05
    )
    kw_b = _calculated_kw_fixture(
        ks_id=11, text="b", mode=KeywordStrategyMode.MIN_CPA, conv=0.04
    )
    contexts = [
        KeywordV3Context(keyword=kw_a, position_profile=_sample_profile()),
        KeywordV3Context(keyword=kw_b, position_profile=_sample_profile()),
    ]
    expected = {
        ks_id: elig.target_place_fallback_zero
        for ks_id, elig in build_eligibility_map(contexts).items()
    }
    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data._weighted_campaign_conv",
        wraps=_weighted_campaign_conv,
    ) as weighted_mock:
        result = build_target_place_fallback_zero_by_keyword_id(contexts)

    assert weighted_mock.call_count == 1
    assert result == expected
