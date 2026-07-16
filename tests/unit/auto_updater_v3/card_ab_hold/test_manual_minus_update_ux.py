"""§10: honest UX после freeze no-op на «Обновить минус-слова».

Spec scenario Manual bot minus update does not report success during freeze.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.minus_freeze import (
    AB_HOLD_MANUAL_MINUS_UPDATE_BLOCKED_MSG,
    MINUS_PHRASES_UPDATED_SUCCESS_MSG,
    user_message_after_ordinary_minus_update,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
)
from app.modules.shop_runner.service_manager.services.minus_phrase_manager.minus_phrase_manager import (
    MinusPhraseManager,
)


@pytest.mark.unit
def test_user_message_after_ordinary_minus_update_paired() -> None:
    """10.1: OFF/applied → success; freeze skip → non-success + отключите A/B Hold."""
    assert (
        user_message_after_ordinary_minus_update(applied=True)
        == MINUS_PHRASES_UPDATED_SUCCESS_MSG
    )
    blocked = user_message_after_ordinary_minus_update(applied=False)
    assert blocked == AB_HOLD_MANUAL_MINUS_UPDATE_BLOCKED_MSG
    assert "не обновлены" in blocked
    assert "отключите A/B Hold" in blocked
    assert blocked != MINUS_PHRASES_UPDATED_SUCCESS_MSG


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_minus_phrases_returns_false_on_freeze_without_inner() -> None:
    """10.1/10.2: ACTIVE/PENDING → False + no ordinary write path."""
    mgr = MinusPhraseManager(
        wb_api_manager_hub=AsyncMock(),
        click_house_manager=AsyncMock(),
        update_redis_timestamp_manager=AsyncMock(),
    )
    mgr._update_minus_phrases = AsyncMock()  # type: ignore[method-assign]

    for mode in (CardAbHoldMode.ACTIVE.value, CardAbHoldMode.PENDING_SETUP.value):
        mgr._update_minus_phrases.reset_mock()
        adv = SimpleNamespace(
            card_ab_hold_mode=mode,
            shop_id=1,
            adv_id=2,
        )
        applied = await mgr.update_minus_phrases(adv)  # type: ignore[arg-type]
        assert applied is False
        mgr._update_minus_phrases.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_minus_phrases_returns_true_when_off() -> None:
    """10.1 allowed: mode OFF → applied True и ordinary path вызывается."""
    mgr = MinusPhraseManager(
        wb_api_manager_hub=AsyncMock(),
        click_house_manager=AsyncMock(),
        update_redis_timestamp_manager=AsyncMock(),
    )
    mgr._update_minus_phrases = AsyncMock()  # type: ignore[method-assign]
    adv = SimpleNamespace(
        card_ab_hold_mode=CardAbHoldMode.OFF.value,
        shop_id=1,
        adv_id=2,
    )
    applied = await mgr.update_minus_phrases(adv)  # type: ignore[arg-type]
    assert applied is True
    mgr._update_minus_phrases.assert_awaited_once()


@pytest.mark.unit
def test_wb_update_minus_keywords_wires_applied_message() -> None:
    """10.2 wiring: handler MUST map manager bool → user_message helper."""
    src = Path(
        "app/client_bot/user_interface/handlers/adv_setting/adv_setting.py"
    ).read_text(encoding="utf-8")
    assert "user_message_after_ordinary_minus_update" in src
    assert "applied =" in src or "applied=" in src
    # Forbidden: always success after await without status
    assert 'await bot.send_message(chat_id, "Минус-слова обновлены.")' not in src
