"""Launch-validity soft-gate: campaign-level proxy Σ keyword views (§2c).

Spec ``card-ab-hold-mode`` — Requirement «Enable warns when campaign recent
keyword impressions are too low». Decision §2c: soft-gate; calendar-day MV
cover last-24h wall-clock; CH-error → distinct reason.

Класс: unit. Boundary вокруг порога + CH error vs measured zero.
"""

from __future__ import annotations

from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold import (
    launch_validity_gate as gate,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.launch_validity_gate import (
    AB_HOLD_MIN_TOTAL_VIEWS_24H,
    LaunchViewVolumeOutcome,
)


@pytest.mark.unit
def test_threshold_constant_is_1000() -> None:
    """13.1: порог зафиксирован (decision §2c)."""
    assert AB_HOLD_MIN_TOTAL_VIEWS_24H == 1000


@pytest.mark.unit
@pytest.mark.parametrize(
    ("total_views", "expected_low"),
    [
        (0, True),
        (999, True),
        (1000, False),
        (1001, False),
        (50_000, False),
    ],
)
def test_low_recent_impressions_boundary(
    total_views: int, expected_low: bool
) -> None:
    """13.1: граница порога — равенство 1000 уже достаточно (>= → не low)."""
    assert gate.is_low_recent_impressions(total_views) is expected_low


@pytest.mark.unit
def test_sum_recent_keyword_views_sums_days() -> None:
    """Сумма посуточного CH-агрегата за calendar-day cover."""
    views_by_day: dict[date, int] = {
        date(2026, 7, 14): 400,
        date(2026, 7, 15): 600,
    }
    assert gate.sum_recent_keyword_views(views_by_day) == 1000
    assert gate.sum_recent_keyword_views({}) == 0


@pytest.mark.unit
def test_candidate_adv_ids_includes_search_and_dedups() -> None:
    """Campaign-level proxy: adv + парный search, без дублей."""
    adv = SimpleNamespace(adv_id=100, search_adv_id=200)
    assert gate.candidate_views_adv_ids(adv) == [100, 200]
    only_main = SimpleNamespace(adv_id=100, search_adv_id=None)
    assert gate.candidate_views_adv_ids(only_main) == [100]
    same = SimpleNamespace(adv_id=100, search_adv_id=100)
    assert gate.candidate_views_adv_ids(same) == [100]
    none_at_all = SimpleNamespace(adv_id=None, search_adv_id=None)
    assert gate.candidate_views_adv_ids(none_at_all) == []


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("daily_views", "expected_total", "expected_outcome"),
    [
        ({date(2026, 7, 14): 400, date(2026, 7, 15): 599}, 999, LaunchViewVolumeOutcome.LOW),
        ({date(2026, 7, 14): 400, date(2026, 7, 15): 600}, 1000, LaunchViewVolumeOutcome.SUFFICIENT),
        ({date(2026, 7, 14): 400, date(2026, 7, 15): 601}, 1001, LaunchViewVolumeOutcome.SUFFICIENT),
    ],
)
async def test_evaluate_launch_view_volume_boundary(
    daily_views: dict[date, int],
    expected_total: int,
    expected_outcome: LaunchViewVolumeOutcome,
) -> None:
    """13.1: measured aggregate за calendar-day cover → boundary вокруг 1000."""
    adv = SimpleNamespace(adv_id=100, search_adv_id=None)
    with patch.object(
        gate.full_wb_adv_stat,
        "get_keywords_views_by_days",
        new=AsyncMock(return_value=daily_views),
    ) as ch_call:
        result = await gate.evaluate_ab_hold_launch_view_volume(
            adv, now=datetime(2026, 7, 15, 12, 0, 0)
        )
    assert result.total_views == expected_total
    assert result.outcome == expected_outcome
    ch_call.assert_awaited_once()
    called_ids = ch_call.await_args.args[0]
    assert called_ids == [100]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_measured_zero_views_is_low_not_unavailable() -> None:
    """17.1 paired: CH success с нулевыми сутками → LOW, не UNAVAILABLE."""
    adv = SimpleNamespace(adv_id=100, search_adv_id=None)
    zero_days = {date(2026, 7, 14): 0, date(2026, 7, 15): 0}
    with patch.object(
        gate.full_wb_adv_stat,
        "get_keywords_views_by_days",
        new=AsyncMock(return_value=zero_days),
    ):
        result = await gate.evaluate_ab_hold_launch_view_volume(
            adv, now=datetime(2026, 7, 15, 12, 0, 0)
        )
    assert result.outcome == LaunchViewVolumeOutcome.LOW
    assert result.total_views == 0
    assert not result.is_unavailable


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ch_error_marks_unavailable_not_low() -> None:
    """17.1: CH error (пустой dict при adv_id) → UNAVAILABLE, не LOW."""
    adv = SimpleNamespace(adv_id=100, search_adv_id=None)
    with patch.object(
        gate.full_wb_adv_stat,
        "get_keywords_views_by_days",
        new=AsyncMock(return_value={}),
    ):
        result = await gate.evaluate_ab_hold_launch_view_volume(
            adv, now=datetime(2026, 7, 15, 12, 0, 0)
        )
    assert result.outcome == LaunchViewVolumeOutcome.UNAVAILABLE
    assert result.is_unavailable
    assert not result.is_sufficient


@pytest.mark.unit
@pytest.mark.asyncio
async def test_aggregate_returns_zero_without_adv_ids() -> None:
    """Нет adv_id → measured 0 без обращения к CH."""
    adv = SimpleNamespace(adv_id=None, search_adv_id=None)
    with patch.object(
        gate.full_wb_adv_stat,
        "get_keywords_views_by_days",
        new=AsyncMock(return_value={}),
    ) as ch_call:
        total = await gate.aggregate_candidate_views_24h(adv)
    assert total == 0
    ch_call.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_aggregate_returns_none_on_ch_error() -> None:
    """17.1: CH error → None (не 0)."""
    adv = SimpleNamespace(adv_id=100, search_adv_id=None)
    with patch.object(
        gate.full_wb_adv_stat,
        "get_keywords_views_by_days",
        new=AsyncMock(return_value={}),
    ):
        total = await gate.aggregate_candidate_views_24h(adv)
    assert total is None


@pytest.mark.unit
def test_low_views_warning_message_has_reason_recommendation_and_choice() -> None:
    """13.2: сообщение содержит причину, рекомендацию (max CPO) и выбор."""
    msg = gate.build_ab_hold_low_views_warning_message(300)
    assert "Мало показов" in msg
    assert "300" in msg
    assert "1000" in msg
    assert "max CPO" in msg
    assert "календарные сутки MV" in msg
    assert "запустить" in msg.lower()
    assert "отмен" in msg.lower()
    assert "{" not in msg and "}" not in msg


@pytest.mark.unit
def test_views_unavailable_message_is_distinct_from_low_warning() -> None:
    """17.1: CH-error copy не содержит low-impressions framing."""
    msg = gate.build_ab_hold_views_unavailable_message()
    alert = gate.build_ab_hold_views_unavailable_alert()
    low_msg = gate.build_ab_hold_low_views_warning_message(0)
    assert "временно недоступна" in msg
    assert "Мало показов" not in msg
    assert "Мало показов" in low_msg
    assert "недоступна" in alert
    assert len(alert) <= 200
