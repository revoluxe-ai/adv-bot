"""Тесты экрана «Почему бот так решил?» (MVP, read-only audit)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.client_bot.user_interface.views.keyword_v3_profile_ui import (
    NON_V3_DECISION_TRACE_MESSAGE,
    format_keyword_v3_decision_trace_screen,
    keyword_v3_decision_trace_button_label,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_keyword_changes_report.models import (
    V3KeywordChangeEntry,
    V3KeywordChangesSnapshot,
    V3KeywordStepRecord,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
)


@pytest.mark.unit
def test_button_label_good_vs_bad() -> None:
    assert keyword_v3_decision_trace_button_label(KeywordStatus.GOOD) == (
        "🔎 Почему бот включил?"
    )
    assert keyword_v3_decision_trace_button_label(KeywordStatus.BAD) == (
        "🔎 Почему бот не включил?"
    )
    assert keyword_v3_decision_trace_button_label(
        KeywordStatus.VIEWS_IS_NOT_ENOUGH
    ) == "🔎 Почему бот не включил?"


@pytest.mark.unit
def test_screen_shows_executor_and_reason() -> None:
    tick_at = datetime(2026, 6, 2, 17, 59, tzinfo=timezone.utc)
    snapshot = V3KeywordChangesSnapshot(
        tick_at=tick_at,
        adv_id=519358830,
        keyword_entries=[
            V3KeywordChangeEntry(
                keyword_setting_id=42,
                keyword_text="туалетный столик с зеркалом",
                stored_mode="OFF",
                current_mode="MIN_CPA",
                steps=[
                    V3KeywordStepRecord(
                        executor_name="RaiseStateToTargetCpoExecutor",
                        from_mode="OFF",
                        to_mode="MIN_CPA",
                        action="UP",
                    ),
                ],
            ),
        ],
    )
    text = format_keyword_v3_decision_trace_screen(
        nmid="519358830",
        keyword_text="туалетный столик с зеркалом",
        display_status=KeywordStatus.BAD,
        keyword_setting_id=42,
        keyword_changes=snapshot,
    )
    assert "🔎" in text
    assert "519358830" in text
    assert "туалетный столик с зеркалом" in text
    assert "bad" in text
    assert "RaiseStateToTargetCpoExecutor" in text
    assert "Решение:" in text
    assert "UP" in text
    assert "Причина:" in text
    assert "OFF" in text and "MIN_CPA" in text
    assert "нет изменяющего executor" not in text


@pytest.mark.unit
def test_screen_fallback_without_entry() -> None:
    snapshot = V3KeywordChangesSnapshot(
        tick_at=datetime.now(timezone.utc),
        adv_id=1,
        keyword_entries=[],
    )
    text = format_keyword_v3_decision_trace_screen(
        nmid="123",
        keyword_text="test kw",
        display_status=KeywordStatus.BAD,
        keyword_setting_id=99,
        keyword_changes=snapshot,
    )
    assert "нет записанного решения" in text
    assert "нет изменений" in text
    assert "Причина не зафиксирована" in text
    assert "нет изменяющего executor" in text
    assert "Полный каскад SKIP/APPLY" in text


@pytest.mark.unit
def test_screen_fallback_without_snapshot() -> None:
    text = format_keyword_v3_decision_trace_screen(
        nmid="123",
        keyword_text="off kw",
        display_status=KeywordStatus.GOOD,
        keyword_setting_id=1,
        keyword_changes=None,
    )
    assert "нет записанного решения" in text
    assert "Причина не зафиксирована" in text
    assert "нет изменяющего executor" in text


@pytest.mark.unit
def test_screen_fallback_all_noop_steps() -> None:
    snapshot = V3KeywordChangesSnapshot(
        tick_at=datetime.now(timezone.utc),
        adv_id=1,
        keyword_entries=[
            V3KeywordChangeEntry(
                keyword_setting_id=1,
                keyword_text="noop",
                stored_mode="MIN_CPA",
                current_mode="MIN_CPA",
                steps=[
                    V3KeywordStepRecord(
                        executor_name="ShelfCleanupExecutor",
                        from_mode="MIN_CPA",
                        to_mode="MIN_CPA",
                        action="NOOP",
                    ),
                ],
            ),
        ],
    )
    text = format_keyword_v3_decision_trace_screen(
        nmid="1",
        keyword_text="noop",
        display_status=KeywordStatus.GOOD,
        keyword_setting_id=1,
        keyword_changes=snapshot,
    )
    assert "нет записанного решения" in text
    assert "нет изменяющего executor" in text


@pytest.mark.unit
def test_screen_excludes_ladder_cpm_ch_data() -> None:
    snapshot = V3KeywordChangesSnapshot(
        tick_at=datetime.now(timezone.utc),
        adv_id=1,
        keyword_entries=[
            V3KeywordChangeEntry(
                keyword_setting_id=5,
                keyword_text="kw",
                stored_mode="MIN_CPA",
                current_mode="OPTIMUM",
                steps=[
                    V3KeywordStepRecord(
                        executor_name="ResolveCalibrationExecutor",
                        from_mode="MIN_CPA",
                        to_mode="OPTIMUM",
                        action="UP",
                    ),
                ],
            ),
        ],
    )
    text = format_keyword_v3_decision_trace_screen(
        nmid="99",
        keyword_text="kw",
        display_status=KeywordStatus.GOOD,
        keyword_setting_id=5,
        keyword_changes=snapshot,
    )
    forbidden = (
        "CPM",
        "pay_for_order",
        "CH матрица",
        "Профиль ключа",
        "CPO=",
        "лестниц",
    )
    for token in forbidden:
        assert token not in text


@pytest.mark.unit
def test_non_v3_message_constant() -> None:
    assert NON_V3_DECISION_TRACE_MESSAGE == (
        "Разбор решений доступен только для V3-управления."
    )
