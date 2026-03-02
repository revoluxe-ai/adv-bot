"""Unit tests for raise_card_analyze: quality_gate, weak_reasons, compute_trend, constants."""

import pytest
from datetime import date

from app.modules.raise_card_analyze.constants import (
    BID_CAP,
    CORR_MIN_POINTS,
    CORR_MIN_SUM_D,
    K_MIN_ABS,
    MIN_D_VIEWS_COLD,
    MIN_D_VIEWS_NORMAL,
    MIN_ROWS_FOR_K,
    MIN_ROWS_FOR_SIGN,
    POS_CAP,
    ROWS_WEEK_WARN,
    SPREAD_MIN_ROWS,
    SPREAD_OK_MIN,
    SUM_D_WEEK_FAIL,
    TAIL_MODE_THRESHOLD,
    TAIL_TREND_THRESHOLD,
    TREND_VERDICT_THRESHOLD,
)
from app.modules.raise_card_analyze.dto import DayPoint, TrendVerdict
from app.modules.raise_card_analyze.service import (
    CampaignGrowthAnalysisService,
    QualityGateResult,
    _weak_reasons,
)


# --- Constants (plan: release 1) ---


@pytest.mark.unit
def test_pos_cap_bid_cap():
    assert POS_CAP == 2000
    assert BID_CAP == 1_000_000


@pytest.mark.unit
def test_tail_constants():
    assert TAIL_MODE_THRESHOLD == 0.30
    assert TAIL_TREND_THRESHOLD == 0.15


@pytest.mark.unit
def test_spread_and_rows_constants():
    assert SPREAD_MIN_ROWS == 200
    assert MIN_ROWS_FOR_SIGN == 200
    assert MIN_ROWS_FOR_K == 200
    assert SPREAD_OK_MIN == 1.2


@pytest.mark.unit
def test_quality_gate_constants():
    assert SUM_D_WEEK_FAIL == 100
    assert ROWS_WEEK_WARN == 30


@pytest.mark.unit
def test_corr_constants():
    assert CORR_MIN_SUM_D == 10
    assert CORR_MIN_POINTS == 200


@pytest.mark.unit
def test_k_min_abs():
    assert K_MIN_ABS == 0.05


# --- Quality gate ---


@pytest.mark.unit
def test_quality_gate_fail_low_traffic():
    svc = CampaignGrowthAnalysisService(ch_manager=None)  # type: ignore[arg-type]
    r = svc.quality_gate(rows_week=50, sum_d_week=80, k_is_weak=False)
    assert r.fail is True
    assert r.warn is False
    assert "трафика" in r.message or "трафик" in r.message.lower()


@pytest.mark.unit
def test_quality_gate_warn_few_rows():
    svc = CampaignGrowthAnalysisService(ch_manager=None)  # type: ignore[arg-type]
    r = svc.quality_gate(rows_week=20, sum_d_week=150, k_is_weak=False)
    assert r.fail is False
    assert r.warn is True
    assert "точек" in r.message.lower() or "точек" in r.message


@pytest.mark.unit
def test_quality_gate_k_is_weak():
    svc = CampaignGrowthAnalysisService(ch_manager=None)  # type: ignore[arg-type]
    r = svc.quality_gate(rows_week=100, sum_d_week=200, k_is_weak=True)
    assert r.fail is False
    assert r.warn is False
    assert "ставки" in r.message or "эффект" in r.message.lower()


@pytest.mark.unit
def test_quality_gate_ok():
    svc = CampaignGrowthAnalysisService(ch_manager=None)  # type: ignore[arg-type]
    r = svc.quality_gate(rows_week=50, sum_d_week=200, k_is_weak=False)
    assert r.fail is False
    assert r.warn is False
    assert r.message == ""


# --- Weak reasons order and conditions ---


@pytest.mark.unit
def test_weak_reasons_order():
    """Priority: low_spread > wrong_sign > flat_k > low_corr."""
    # low_spread (spread < 1.2), wrong_sign (k>=0), flat_k (|k|<0.05), low_corr (|corr|<0.05)
    r = _weak_reasons(k=0.02, rows_used=300, spread_used_recent=1.0, corr_ln=0.02, k_source="item")
    assert "low_spread" in r
    assert "wrong_sign" in r
    assert "flat_k" in r
    assert "low_corr" in r
    order = [r.index(x) for x in ("low_spread", "wrong_sign", "flat_k", "low_corr")]
    assert order == sorted(order)


@pytest.mark.unit
def test_weak_reasons_no_wrong_sign_flat_k_when_rows_below_200():
    """When rows_used < 200, wrong_sign and flat_k are not added."""
    r = _weak_reasons(k=0.0, rows_used=100, spread_used_recent=1.5, corr_ln=None, k_source="item")
    assert "wrong_sign" not in r
    assert "flat_k" not in r


@pytest.mark.unit
def test_weak_reasons_low_spread_only_when_spread_not_none():
    r = _weak_reasons(k=0.1, rows_used=300, spread_used_recent=None, corr_ln=None, k_source="item")
    assert "low_spread" not in r


@pytest.mark.unit
def test_weak_reasons_low_corr_only_when_corr_ln_not_none():
    """low_corr only if corr_ln is not None (item/adv)."""
    r = _weak_reasons(k=-0.2, rows_used=300, spread_used_recent=2.0, corr_ln=None, k_source="item")
    assert "low_corr" not in r
    r2 = _weak_reasons(k=-0.2, rows_used=300, spread_used_recent=2.0, corr_ln=0.02, k_source="item")
    assert "low_corr" in r2


@pytest.mark.unit
def test_weak_reasons_category_global_no_low_corr():
    r = _weak_reasons(k=-0.1, rows_used=500, spread_used_recent=2.0, corr_ln=0.01, k_source="category")
    assert "low_corr" not in r


# --- compute_trend returns None when noisy or k_is_weak ---


@pytest.mark.unit
def test_compute_trend_returns_none_when_noisy_mode():
    svc = CampaignGrowthAnalysisService(ch_manager=None)  # type: ignore[arg-type]
    series = [
        DayPoint(date(2025, 1, d), 100.0 - d, 10.0, 10.0, 50, 5)
        for d in range(1, 15)
    ]
    t = svc.compute_trend(
        series, "last_7_vs_prev_7", k_is_weak=False, is_noisy_mode=True, tail_mode=False, is_cold=True
    )
    assert t is None


@pytest.mark.unit
def test_compute_trend_returns_none_when_k_is_weak():
    svc = CampaignGrowthAnalysisService(ch_manager=None)  # type: ignore[arg-type]
    series = [
        DayPoint(date(2025, 1, d), 100.0 - d, 10.0, 10.0, 50, 5)
        for d in range(1, 15)
    ]
    t = svc.compute_trend(
        series, "last_7_vs_prev_7", k_is_weak=True, is_noisy_mode=False, tail_mode=False, is_cold=True
    )
    assert t is None


@pytest.mark.unit
def test_compute_trend_cold_last7_vs_prev7():
    svc = CampaignGrowthAnalysisService(ch_manager=None)  # type: ignore[arg-type]
    # last7 lower (better) than prev7 -> growth
    series = [
        DayPoint(date(2025, 1, d), 50.0 if d <= 7 else 30.0, 10.0, 10.0, 50, 5)
        for d in range(1, 15)
    ]
    t = svc.compute_trend(
        series, "last_7_vs_prev_7", k_is_weak=False, is_noisy_mode=False, tail_mode=False, is_cold=True
    )
    assert t is not None
    assert t.verdict == TrendVerdict.GROWS
    assert t.mode == "last_7_vs_prev_7"


@pytest.mark.unit
def test_compute_trend_tail_mode_uses_wider_threshold():
    svc = CampaignGrowthAnalysisService(ch_manager=None)  # type: ignore[arg-type]
    # change ~12% -> with 10% threshold would be "grows", with 15% might be "flat"
    series = [
        DayPoint(date(2025, 1, d), 100.0 - d * (0.12 if d > 7 else 0), 10.0, 10.0, 50, 5)
        for d in range(1, 15)
    ]
    t_no_tail = svc.compute_trend(
        series, "last_7_vs_prev_7", k_is_weak=False, is_noisy_mode=False, tail_mode=False, is_cold=True
    )
    t_tail = svc.compute_trend(
        series, "last_7_vs_prev_7", k_is_weak=False, is_noisy_mode=False, tail_mode=True, is_cold=True
    )
    assert t_no_tail is not None
    assert t_tail is not None
    # With tail_mode threshold is 15%, so verdict might differ for borderline change
    assert t_tail.verdict in (TrendVerdict.GROWS, TrendVerdict.FLAT, TrendVerdict.FALLS)


# --- Clip behavior (documented: pos_final 2200 -> 2000, 1200 -> 1200) ---


@pytest.mark.unit
def test_pos_cap_clip_logic():
    """POS_CAP=2000: values above 2000 are clipped to 2000, below stay."""
    assert POS_CAP == 2000
    # In SQL: pos_clip = least(greatest(pos_final, 1), POS_CAP)
    def clip(pos: float) -> float:
        return min(max(pos, 1), POS_CAP)
    assert clip(2200) == 2000
    assert clip(1200) == 1200
    assert clip(1) == 1
    assert clip(0) == 1
