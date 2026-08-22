"""WARMS2 / ROOT-001: S1→S2→S3 write-moment for WARM_UP timer.

Regression pack for corrected UX/decision contract:

* S1 keyword confirm → durable keywords + WARM_UP config; ``warmup_started_at`` NULL
* S2 duration confirm → persist hours + set ``warmup_started_at`` (timer start)
* S1b mid-WARM_UP keyword confirm → clear timer, return to S2; no immediate restart

Causal boundary: ``epoch_write.confirm_keyword_set_and_start_warmup`` /
``epoch_write.set_warmup_duration`` (Telegram handlers only trigger these writes).
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.sql.dml import Update

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_lifecycle import (
    DEFAULT_WARMUP_HOURS,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_write import (
    confirm_keyword_set_and_start_warmup,
    set_warmup_duration,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldPhase,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_keyboards import (
    build_s2_keyboard,
    build_s3_keyboard,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_screens import (
    build_s2_text,
    build_s3_text,
)


def _update_values(stmt: object) -> dict[str, Any]:
    """Извлечь column→value из SQLAlchemy ``Update`` (без compile-зависимостей)."""
    assert isinstance(stmt, Update)
    out: dict[str, Any] = {}
    raw = getattr(stmt, "_values", None) or {}
    for col, val in raw.items():
        key = getattr(col, "key", None) or str(col)
        if hasattr(val, "value"):
            out[key] = val.value
        else:
            out[key] = val
    return out


def _last_update_values(mock_session: AsyncMock) -> dict[str, Any]:
    """Последний ``UPDATE`` statement из ``session.execute``."""
    for call in reversed(mock_session.execute.call_args_list):
        stmt = call.args[0]
        if isinstance(stmt, Update):
            return _update_values(stmt)
    raise AssertionError("no Update statement executed")


def _mock_sm_with_adv(adv: SimpleNamespace) -> tuple[MagicMock, AsyncMock]:
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = adv
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=None)
    return mock_cm, mock_session


# ---------------------------------------------------------------------------
# CASE-W1 — S1 keyword confirmation enters S2 without starting timer
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_warms2_case_w1_s1_keyword_confirm_leaves_warmup_started_at_null() -> None:
    """CASE-W1: first keyword-set confirm MUST NOT set ``warmup_started_at``.

    Invariant: S1 → WARM_UP duration-configuration (S2); timer stays unset so
    duration UI remains reachable before S3.
    """
    adv = SimpleNamespace(
        id=101,
        card_ab_hold_phase=CardAbHoldPhase.AWAITING_KEYWORD_CONFIRM.value,
        card_ab_hold_confirmed_keywords_json=None,
        card_ab_hold_warmup_started_at=None,
        card_ab_hold_warmup_duration_hours=None,
    )
    mock_cm, mock_session = _mock_sm_with_adv(adv)
    keywords = ["kw-a", "kw-b"]

    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_write.sm",
        return_value=mock_cm,
    ):
        await confirm_keyword_set_and_start_warmup(
            101, keywords, duration_hours=DEFAULT_WARMUP_HOURS
        )

    values = _last_update_values(mock_session)
    assert values.get("card_ab_hold_confirmed_keywords_json") == keywords
    assert values.get("card_ab_hold_phase") == CardAbHoldPhase.WARM_UP.value
    assert values.get("card_ab_hold_warmup_started_at") is None, (
        "S1 keyword confirm MUST leave warmup_started_at NULL (S2 config); "
        f"got {values.get('card_ab_hold_warmup_started_at')!r}"
    )
    mock_session.commit.assert_called_once()


@pytest.mark.unit
def test_warms2_case_w1_render_s2_when_started_at_null_with_keywords() -> None:
    """CASE-W1 (render gate): started_at NULL + confirmed keywords → S2 UX.

    Documents the renderer contract that makes duration presets reachable.
    """
    text = build_s2_text(duration_hours=24)
    kb = build_s2_keyboard(adv_id=101, revision=1)
    button_texts = [btn.text for row in kb.inline_keyboard for btn in row]
    assert "Подтвердить длительность" in button_texts
    assert "24ч (по умолчанию)" in button_texts
    assert "Увеличить: +24ч" in button_texts
    assert "Обновить статус" not in button_texts
    assert "длительн" in text.lower() or "прогрев" in text.lower() or "час" in text.lower()


# ---------------------------------------------------------------------------
# CASE-W2 — S2 duration confirmation starts timer and enters S3
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_warms2_case_w2_duration_confirm_sets_warmup_started_at() -> None:
    """CASE-W2: ``set_warmup_duration`` MUST set ``warmup_started_at`` (timer start).

    Invariant: S2 ``warmup_duration_confirm`` owns the complete timer-start
    transition (hours + started_at), not keyword confirm.
    """
    adv = SimpleNamespace(
        id=202,
        card_ab_hold_phase=CardAbHoldPhase.WARM_UP.value,
        card_ab_hold_confirmed_keywords_json=["kw-a"],
        card_ab_hold_warmup_started_at=None,
        card_ab_hold_warmup_duration_hours=None,
    )
    mock_cm, mock_session = _mock_sm_with_adv(adv)

    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_write.sm",
        return_value=mock_cm,
    ):
        applied = await set_warmup_duration(202, 48)

    assert applied == 48
    values = _last_update_values(mock_session)
    assert values.get("card_ab_hold_warmup_duration_hours") == 48
    started = values.get("card_ab_hold_warmup_started_at")
    assert started is not None, (
        "S2 duration confirm MUST set warmup_started_at (timer start → S3); "
        "update omitted the field"
    )
    assert "card_ab_hold_warmup_started_at" in values
    mock_session.commit.assert_called_once()


@pytest.mark.unit
def test_warms2_case_w2_render_s3_requires_started_at() -> None:
    """CASE-W2 (render gate): S3 progress UX requires a started timer."""
    started = datetime(2026, 7, 27, 12, 0, tzinfo=timezone.utc)
    text = build_s3_text(started_at=started, duration_hours=48)
    kb = build_s3_keyboard(adv_id=202, revision=1)
    button_texts = [btn.text for row in kb.inline_keyboard for btn in row]
    assert "Обновить статус" in button_texts
    assert "Изменить набор ключей" in button_texts
    assert "Подтвердить длительность" not in button_texts
    assert text


# ---------------------------------------------------------------------------
# CASE-W3 — S1b ends timer and returns to S2 without immediate restart
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_warms2_case_w3_s1b_clears_timer_without_immediate_restart() -> None:
    """CASE-W3: S1b keyword confirm clears ``warmup_started_at``; no new start.

    Invariant: mid-WARM_UP keyword edit confirm ends the running timer and
    returns to S2; restart happens only on subsequent duration confirm.
    """
    prior_started = datetime(2026, 7, 27, 10, 0, tzinfo=timezone.utc)
    adv = SimpleNamespace(
        id=303,
        card_ab_hold_phase=CardAbHoldPhase.WARM_UP.value,
        card_ab_hold_confirmed_keywords_json=["kw-old"],
        card_ab_hold_warmup_started_at=prior_started,
        card_ab_hold_warmup_duration_hours=24,
    )
    mock_cm, mock_session = _mock_sm_with_adv(adv)
    new_keywords = ["kw-old", "kw-new"]

    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_write.sm",
        return_value=mock_cm,
    ):
        await confirm_keyword_set_and_start_warmup(
            303, new_keywords, duration_hours=24
        )

    values = _last_update_values(mock_session)
    assert values.get("card_ab_hold_confirmed_keywords_json") == new_keywords
    assert values.get("card_ab_hold_phase") == CardAbHoldPhase.WARM_UP.value
    started = values.get("card_ab_hold_warmup_started_at")
    assert started is None, (
        "S1b MUST clear warmup_started_at (return to S2) and MUST NOT "
        f"immediately restart the timer; got {started!r}"
    )
    mock_session.commit.assert_called_once()
