"""Unit: KeywordDataTier, eligibility helpers, can_target_mode."""

from __future__ import annotations

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
    KeywordDataTier,
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
