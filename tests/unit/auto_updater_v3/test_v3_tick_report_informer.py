"""Unit: форматирование текста отчёта V3-тика для Telegram."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.client_bot.user_interface.views.messages.v3_tick_report_informer import (
    format_v3_tick_report_text,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_tick_report import (
    V3PhaseStats,
    V3TickReportSnapshot,
    WhiteListCostLeader,
)


@pytest.mark.unit
def test_format_empty_snapshot() -> None:
    text = format_v3_tick_report_text(None)
    assert "Нет данных" in text


@pytest.mark.unit
def test_format_normal_snapshot_contains_sections() -> None:
    snap = V3TickReportSnapshot(
        tick_at=datetime(2026, 6, 3, 14, 32, 5, tzinfo=UTC),
        adv_id=1,
        adv_name="Крем",
        campaign_mode="NORMAL",
        sales_state="STABLE",
        total_keywords=100,
        operable_keywords=80,
        fact_cpa=85.0,
        resolve=92.0,
        max_pay_for_order=100.0,
        phases=[
            V3PhaseStats(
                phase_id="filter",
                title_ru="0 · Фильтр",
                extra={"total": 100, "operable": 80},
            ),
            V3PhaseStats(
                phase_id="max_cpa_guard",
                title_ru="G",
                possible_actions_ru="DOWN, OFF",
                executed=False,
                skip_reason="fact_le_max",
            ),
            V3PhaseStats(
                phase_id="resolve_calibration",
                title_ru="calibration",
                possible_actions_ru="UP, DOWN",
                up=0,
                down=3,
                extra={
                    "calibration_direct": "tighten",
                    "effective_steps": 2,
                    "applied_steps": 2,
                    "prev_effective_steps": 1,
                },
            ),
        ],
        hard_status_counts={"Авто": 40, "Белый список": 40},
        aggression_score_before=100,
        aggression_score_after=107,
        aggression_delta=7,
        net_up=5,
        net_down=3,
        net_force_off=0,
    )
    text = format_v3_tick_report_text(snap)
    assert "Последний тик V3" in text
    assert "Крем" in text
    assert "ИТОГ тика" in text
    assert "+7" in text
    assert "пропуск" in text
    assert "DOWN" in text
    assert "шаг 2 (было 1)" in text
    assert "Авто: 40" in text
    assert "Возможные:" not in text
    assert "on:0  ↓3  off:0" in text
    assert "on:0  −3↓  off:0" in text


@pytest.mark.unit
def test_format_phase_counters_up_on_down_off_order() -> None:
    snap = V3TickReportSnapshot(
        tick_at=datetime(2026, 6, 3, 14, 32, 5, tzinfo=UTC),
        adv_id=1,
        adv_name="Крем",
        campaign_mode="NORMAL",
        phases=[
            V3PhaseStats(
                phase_id="shelf_cleanup",
                title_ru="6 · S · shelf cleanup",
                up=14,
                down=0,
                force_off=14,
                ended_off=14,
                ended_on=0,
            ),
            V3PhaseStats(
                phase_id="pay_for_order_gap_enable",
                title_ru="9 · enable · gap",
                up=1,
                ended_on=1,
            ),
        ],
        net_up=19,
        net_down=2,
        net_force_off=28,
        net_on=1,
    )
    text = format_v3_tick_report_text(snap)
    assert "↑14  on:0  ↓14  off:14" in text
    assert "↑1  on:1  ↓0  off:0" in text
    assert "Применено: +19↑  on:1  −2↓  off:28" in text


@pytest.mark.unit
def test_format_zero_calibration_shows_outcome_note_not_counters() -> None:
    snap = V3TickReportSnapshot(
        tick_at=datetime(2026, 6, 3, 14, 32, 5, tzinfo=UTC),
        adv_id=1,
        adv_name="Крем",
        campaign_mode="NORMAL",
        phases=[
            V3PhaseStats(
                phase_id="resolve_calibration",
                title_ru="8 · calibration",
                executed=True,
                outcome_note="нет ключей для UP: 200 operable — потолок режима",
                extra={"calibration_direct": "loosen", "effective_steps": 1},
            ),
        ],
    )
    text = format_v3_tick_report_text(snap)
    assert "UP" in text
    assert "без изменений —" in text
    assert "LOOSEN" not in text
    assert "↑0" not in text


@pytest.mark.unit
def test_format_skipped_calibration_shows_none_as_no() -> None:
    """Если applied step отсутствует, UI должен показать «нет», а не техничное None."""
    snap = V3TickReportSnapshot(
        tick_at=datetime(2026, 6, 3, 14, 32, 5, tzinfo=UTC),
        adv_id=1,
        adv_name="Крем",
        campaign_mode="NORMAL",
        calibration_direct="tighten",
        calibration_prev_effective_steps=2,
    )
    text = format_v3_tick_report_text(snap)
    assert "Калибровка: DOWN · нет" in text
    assert "шаг None" not in text


@pytest.mark.unit
def test_format_phase_skipped_calibration_does_not_fallback_to_zero() -> None:
    """Стадия calibration без applied_steps не должна печатать «шаг 0»."""
    phase = V3PhaseStats(
        phase_id="resolve_calibration",
        title_ru="10 · calibration",
        executed=True,
        outcome_note="нет ключей для UP",
        extra={"calibration_direct": "tighten", "effective_steps": 0},
    )
    text = format_v3_tick_report_text(
        V3TickReportSnapshot(
            tick_at=datetime(2026, 6, 3, 14, 32, 5, tzinfo=UTC),
            adv_id=1,
            adv_name="Крем",
            campaign_mode="NORMAL",
            phases=[phase],
        )
    )
    assert "шаг 0" not in text
    assert "Калибровка:" not in text


@pytest.mark.unit
def test_format_shows_calibration_adaptive_and_white_list_leader() -> None:
    snap = V3TickReportSnapshot(
        tick_at=datetime(2026, 6, 3, 14, 32, 5, tzinfo=UTC),
        adv_id=1,
        adv_name="Крем",
        campaign_mode="NORMAL",
        calibration_effective_steps=4,
        calibration_applied_steps=4,
        calibration_direct="up",
        calibration_prev_effective_steps=2,
        white_list_cost_leader=WhiteListCostLeader(
            keyword_text="крем антивозрастной",
            keyword_setting_id=10,
            data_tier="keyword_pfo",
            strategy_mode="OPTIMUM",
            cost_source="pfo",
            decision_cpo=420.0,
            state_cpo=380.0,
            pfo_cpo=420.0,
        ),
    )
    text = format_v3_tick_report_text(snap)
    assert "Калибровка: UP" in text
    assert "шаг 4 (было 2)" in text
    assert "adaptive" not in text.lower()
    assert "БС max (PFO" in text
    assert "420" in text
    assert "крем антивозрастной" in text


@pytest.mark.unit
def test_format_truncates_long_text() -> None:
    phases = [
        V3PhaseStats(
            phase_id=f"p{i}",
            title_ru="x" * 200,
            possible_actions_ru="UP",
        )
        for i in range(50)
    ]
    snap = V3TickReportSnapshot(
        tick_at=datetime(2026, 6, 3, tzinfo=UTC),
        adv_id=1,
        campaign_mode="NORMAL",
        phases=phases,
    )
    text = format_v3_tick_report_text(snap)
    assert len(text) <= 4096
    assert "обрезано" in text
