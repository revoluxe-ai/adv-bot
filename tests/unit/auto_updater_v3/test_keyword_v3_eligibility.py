"""Unit: KeywordDataTier, eligibility helpers, can_target_mode."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
    CampaignV3DecisionCache,
    keyword_has_v2_cpo,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
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
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_stat import (
    make_zero_keyword_stat,
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
    assert elig.data_tier == KeywordDataTier.KEYWORD_PFO
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
    assert elig.data_tier == KeywordDataTier.KEYWORD_PFO
    assert elig.fallback_kind == "v2_cpo"


@pytest.mark.unit
def test_eligibility_invalid_empty_allowed_modes() -> None:
    kw = _calculated_kw_fixture(
        ks_id=1, text="solo", mode=KeywordStrategyMode.OFF, conv=0.0, cpm_set_bid=0
    )
    stat = kw.cluster_stat.model_copy(update={"views": 0, "conv_views_to_orders": 0.0})
    kw = kw.model_copy(update={"cluster_stat": stat})
    # INVALID: нет CH и нет V2 CPO (NO_CONV требует CH-матрицу на ключе)
    ctx = KeywordV3Context(keyword=kw, position_profile=None)
    elig = resolve_keyword_v3_eligibility(ctx, [ctx])
    assert elig.data_tier == KeywordDataTier.KEYWORD_NO_DATA
    assert elig.allowed_modes == frozenset()
    assert not elig.participates_in_ladder


@pytest.mark.unit
def test_build_eligibility_map_builds_campaign_cache_once() -> None:
    """Один ``CampaignV3DecisionCache.from_contexts`` на ``build_eligibility_map``."""
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
    with patch.object(
        CampaignV3DecisionCache,
        "from_contexts",
        wraps=CampaignV3DecisionCache.from_contexts,
    ) as cache_mock:
        result = build_eligibility_map(contexts)

    assert cache_mock.call_count == 1
    assert len(result) == 2


@pytest.mark.unit
def test_eligibility_ladder_catalog_uses_campaign_orders_per_cart() -> None:
    """``state_candidates_by_mode_for_ctx`` с campaign OPC строит valid MIN."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        LadderInputs,
        state_candidates_by_mode_for_ctx,
    )
    from tests.unit.auto_updater_v3.test_build_mode_candidates_ch_observed import (
        _point,
    )

    profile = [
        _point(13, 21699, 0.0035, ch_observed=True),
        _point(40, 4189, 0.0157, ch_observed=True),
    ]
    stat = make_zero_keyword_stat("opc_parity").model_copy(
        update={"orders": 0, "add_to_cart": 0, "conv_views_to_orders": 0.05}
    )
    kw = _calculated_kw_fixture(
        ks_id=8, text="opc_parity", mode=KeywordStrategyMode.MIN_CPA, conv=0.05
    )
    kw = kw.model_copy(update={"cluster_stat": stat})
    ctx = KeywordV3Context(keyword=kw, position_profile=profile)
    campaign_opc = 0.2618
    ladder = LadderInputs.from_contexts(
        [ctx], campaign_orders_per_cart_7d=campaign_opc
    )
    ladder_cat = state_candidates_by_mode_for_ctx(ctx, ladder)
    assert ladder_cat[AggressionTargetMode.MIN_CPA].is_valid


@pytest.mark.unit
def test_eligibility_collapsed_ch_min_only_preserves_data_tier() -> None:
    """Collapsed CH + pay_for_order: MIN-only и place 0, tier FULL не меняется."""
    from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
        PositionProfilePoint,
    )

    profile = [
        PositionProfilePoint(
            position=1,
            bid=1000,
            predicted_conversion=0.1,
            pay_for_cart=100.0,
            ch_observed=False,
        ),
    ]
    kw = _calculated_kw_fixture(
        ks_id=7, text="collapsed", mode=KeywordStrategyMode.MIN_CPA, conv=0.08
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=profile)
    elig = resolve_keyword_v3_eligibility(ctx, [ctx])
    assert elig.data_tier == KeywordDataTier.KEYWORD_FULL
    assert KeywordStrategyMode.MAX_CONVERSION in elig.allowed_modes
    assert build_target_place_fallback_zero_by_keyword_id([ctx]).get(7) is False


@pytest.mark.unit
def test_build_target_place_fallback_zero_not_full_active_false() -> None:
    """NOT FULL active: sync не форсит 0 через fallback map (без overspend)."""
    kw = _calculated_kw_fixture(
        ks_id=6, text="nf", mode=KeywordStrategyMode.MIN_CPA, conv=0.08
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=None)
    assert build_target_place_fallback_zero_by_keyword_id([ctx]).get(6) is False


@pytest.mark.unit
def test_build_target_place_fallback_zero_not_full_overspend_true() -> None:
    """NOT FULL active при fact CPO > MAX: sync force tp=0."""
    kw = _calculated_kw_fixture(
        ks_id=6, text="nf", mode=KeywordStrategyMode.MIN_CPA, conv=0.08
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=None)
    assert (
        build_target_place_fallback_zero_by_keyword_id(
            [ctx], campaign_overspend=True
        ).get(6)
        is True
    )


@pytest.mark.unit
def test_build_target_place_fallback_zero_excludes_off_mode() -> None:
    """OFF после guard: map без True, хотя tier NO_CH даёт fallback в eligibility."""
    kw = _calculated_kw_fixture(
        ks_id=5, text="off_no_ch", mode=KeywordStrategyMode.OFF, conv=0.08
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=None)
    result = build_target_place_fallback_zero_by_keyword_id([ctx])
    assert result[5] is False


@pytest.mark.unit
def test_build_target_place_fallback_zero_matches_eligibility_map() -> None:
    """``build_target_place_fallback_zero_by_keyword_id`` согласован с eligibility."""
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
    result = build_target_place_fallback_zero_by_keyword_id(contexts)
    assert result == expected
