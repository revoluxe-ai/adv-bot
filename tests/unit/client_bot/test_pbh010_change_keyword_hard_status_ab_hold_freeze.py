"""FINDING-PBH-010 RED: change_keyword_hard_status must freeze under A/B Hold.

ADL ``card-ab-hold-write-path-ownership`` §3/§8 + OP-008 inventory gap:
Telegram ``change_keyword_hard_status`` commits ``hard_status`` +
``sync_keyword_setting_mode_for_v3`` with no ``is_ab_hold_structural_freeze``
gate, while the peer TP path in the same module already gates at ~988.

Same freeze-gate class as closed PBH-004, different mutator/path — do not
reopen PBH-004. Asserts observable refuse under PENDING_SETUP / ACTIVE
(hard_status unchanged, sync not called, commit not called).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.client_bot.user_interface.handlers.keyword_settings import (
    change_keyword_hard_status,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
)

_HANDLER = "app.client_bot.user_interface.handlers.keyword_settings"


def _keyword_setting(*, mode: str, hard_status: int = 1) -> SimpleNamespace:
    """KeywordSetting + AdvSetting stub for hard_status mutator."""
    return SimpleNamespace(
        id=42,
        hard_status=hard_status,
        relevant=True,
        strategy_mode="OFF",
        added_clicks=None,
        added_views=None,
        text="phrase",
        adv_setting=SimpleNamespace(
            adv_id=100,
            search_adv_id=None,
            bot_active=True,
            strategy=None,
            card_ab_hold_mode=mode,
        ),
    )


def _session_with_keyword(keyword: SimpleNamespace) -> AsyncMock:
    """Async session whose execute().scalar() returns keyword."""
    session = AsyncMock()
    result = MagicMock()
    result.scalar = MagicMock(return_value=keyword)
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()
    return session


def _callback(*, keyword_id: int = 42, new_hard_status: int = 2) -> MagicMock:
    """Minimal CallbackQuery + ChangeKeywordHardStatus-like callback_data."""
    callback = MagicMock()
    callback.message = MagicMock()
    callback.message.chat = MagicMock()
    callback.message.chat.id = 7
    callback.from_user = MagicMock()
    callback.from_user.id = 99
    callback.answer = AsyncMock()
    callback_data = SimpleNamespace(
        new_hard_status=new_hard_status,
        keyword_setting_original_id=keyword_id,
    )
    return callback, callback_data


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "hold_mode",
    [
        CardAbHoldMode.PENDING_SETUP.value,
        CardAbHoldMode.ACTIVE.value,
    ],
)
async def test_pbh010_change_keyword_hard_status_blocked_on_ab_hold(
    hold_mode: str,
) -> None:
    """PENDING_SETUP / ACTIVE → hard_status write + mode sync MUST NOT run."""
    keyword = _keyword_setting(mode=hold_mode, hard_status=1)
    session = _session_with_keyword(keyword)
    mock_sm = MagicMock()
    mock_sm.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_sm.return_value.__aexit__ = AsyncMock(return_value=None)

    callback, callback_data = _callback(new_hard_status=2)
    state = AsyncMock()
    state.get_data = AsyncMock(return_value={"last_keyword_setting_page": 1})
    bot = AsyncMock()

    typing_cm = MagicMock()
    typing_cm.__aenter__ = AsyncMock(return_value=None)
    typing_cm.__aexit__ = AsyncMock(return_value=None)

    sync_mock = MagicMock(return_value=False)
    keyword_msg = AsyncMock()

    with (
        patch(f"{_HANDLER}._sm", mock_sm),
        patch(f"{_HANDLER}.ChatActionSender.typing", return_value=typing_cm),
        patch(f"{_HANDLER}.sync_keyword_setting_mode_for_v3", sync_mock),
        patch(
            f"{_HANDLER}.messages.KeywordSettingMessage",
            MagicMock(return_value=keyword_msg),
        ),
    ):
        await change_keyword_hard_status(callback, callback_data, bot, state)

    assert keyword.hard_status == 1, (
        f"FINDING-PBH-010: hard_status mutated under {hold_mode}; "
        "structural freeze must refuse Telegram hard_status commit"
    )
    sync_mock.assert_not_called()
    session.commit.assert_not_called()
