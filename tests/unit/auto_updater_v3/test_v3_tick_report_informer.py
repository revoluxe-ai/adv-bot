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
    assert "TIGHTEN" in text
    assert "Авто: 40" in text
    assert "Возможные:" not in text


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
    assert "LOOSEN" in text
    assert "без изменений — нет ключей для UP" in text
    assert "↑0" not in text


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
