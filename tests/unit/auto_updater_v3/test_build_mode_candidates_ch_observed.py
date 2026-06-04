"""Unit: M/O/C и синтетика _fill_positions (ch_observed=False) vs INCLUDE_SYNTHETIC."""

from __future__ import annotations

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.candidates import (
    build_mode_candidates,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
    PositionProfilePoint,
)


def _point(
    position: int,
    bid: int,
    conv: float,
    *,
    ch_observed: bool = True,
) -> PositionProfilePoint:
    return PositionProfilePoint(
        position=position,
        bid=bid,
        predicted_conversion=conv,
        pay_for_cart=100.0,
        ch_observed=ch_observed,
    )


@pytest.mark.unit
def test_synthetic_plateau_excluded_moc_not_all_same() -> None:
    """Синтетика pos 1–12 @ high bid не участвует; M/O/C различаются."""
    profile = [
        _point(1, 21699, 0.094, ch_observed=False),
        _point(13, 21699, 0.0035, ch_observed=True),
        _point(14, 20533, 0.0058, ch_observed=True),
        _point(40, 4189, 0.0157, ch_observed=True),
        _point(49, 590, 0.002, ch_observed=True),
    ]
    rk = 0.2618
    cat = build_mode_candidates(
        profile=profile,
        keyword_text="kw",
        rk_orders_per_cart=rk,
        include_synthetic=False,
    )
    assert cat[AggressionTargetMode.MIN_CPA].position == 40
    assert cat[AggressionTargetMode.OPTIMUM].position != 1
    assert cat[AggressionTargetMode.MAX_CONVERSION].position != 1
    assert all(
        cat[m].position in {13, 14, 40, 49} for m in AggressionTargetMode
    )


@pytest.mark.unit
def test_only_synthetic_points_invalid_ladder() -> None:
    """Без CH-точек лестница invalid (no_conversion_points)."""
    profile = [
        _point(1, 1000, 0.1, ch_observed=False),
        _point(2, 1000, 0.2, ch_observed=False),
    ]
    cat = build_mode_candidates(
        profile=profile,
        keyword_text="kw",
        rk_orders_per_cart=0.25,
        include_synthetic=False,
    )
    assert not cat[AggressionTargetMode.MIN_CPA].is_valid
    assert cat[AggressionTargetMode.MIN_CPA].invalid_reason == "no_conversion_points"


@pytest.mark.unit
def test_synthetic_plateau_included_when_flag_true() -> None:
    """Синтетика участвует: prior-conv на pos=1 может выиграть MAX."""
    profile = [
        _point(1, 21699, 0.094, ch_observed=False),
        _point(13, 21699, 0.0035, ch_observed=True),
        _point(14, 20533, 0.0058, ch_observed=True),
        _point(40, 4189, 0.0157, ch_observed=True),
        _point(49, 590, 0.002, ch_observed=True),
    ]
    rk = 0.2618
    cat = build_mode_candidates(
        profile=profile,
        keyword_text="kw",
        rk_orders_per_cart=rk,
        include_synthetic=True,
    )
    assert cat[AggressionTargetMode.MAX_CONVERSION].is_valid
    assert cat[AggressionTargetMode.MAX_CONVERSION].position == 1
    assert cat[AggressionTargetMode.MIN_CPA].is_valid


@pytest.mark.unit
def test_only_synthetic_points_valid_when_flag_true() -> None:
    """Только синтетика с conv — valid MIN при включённом флаге."""
    profile = [
        _point(1, 1000, 0.1, ch_observed=False),
        _point(2, 1000, 0.2, ch_observed=False),
    ]
    cat = build_mode_candidates(
        profile=profile,
        keyword_text="kw",
        rk_orders_per_cart=0.25,
        include_synthetic=True,
    )
    assert cat[AggressionTargetMode.MIN_CPA].is_valid
    assert cat[AggressionTargetMode.MIN_CPA].position == 2
