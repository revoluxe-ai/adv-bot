"""Mock-only regression: client_bot PG parent→child session handoff seams.

Доказывает injectable ``*_in_session`` для add_white_phrases / keyword_settings:
parent открывает ``sm(read_only=…)`` и передаёт session в child.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.client_bot.user_interface.handlers import add_white_phrases, keyword_settings
from app.client_bot.user_interface.handlers.add_white_phrases import (
    HardStatusResetOutcome,
)
from app.client_bot.user_interface.handlers.keyword_settings import (
    KeywordHardStatusChangeOutcome,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
)

_ADD = "app.client_bot.user_interface.handlers.add_white_phrases"
_KS = "app.client_bot.user_interface.handlers.keyword_settings"


def _session_cm(session: MagicMock) -> MagicMock:
    """Async context manager yielding ``session``."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm


@pytest.mark.unit
@pytest.mark.asyncio
async def test_waiting_for_white_phrases_hands_off_read_session() -> None:
    """``waiting_for_white_phrases`` → load mode child + sm(read_only=True)."""
    fake_session = MagicMock(name="add_read_session")
    load_child = AsyncMock(return_value=CardAbHoldMode.ACTIVE.value)
    sm_mock = MagicMock(return_value=_session_cm(fake_session))
    message = MagicMock()
    message.text = "a\nb"
    message.answer = AsyncMock()
    message.from_user = SimpleNamespace(id=1)
    state = AsyncMock()
    state.get_data = AsyncMock(return_value={"last_adv_setting_id": 42})
    bot = AsyncMock()

    with (
        patch(f"{_ADD}.sm", sm_mock),
        patch(f"{_ADD}.load_adv_card_ab_hold_mode_in_session", load_child),
        patch(f"{_ADD}.data_manager.add_white_phrases", AsyncMock()) as add_mock,
    ):
        await add_white_phrases.waiting_for_white_phrases(message, bot, state)

    load_child.assert_awaited_once_with(fake_session, 42)
    sm_mock.assert_called_with(read_only=True)
    add_mock.assert_not_called()
    message.answer.assert_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reset_white_list_hands_off_write_session() -> None:
    """``reset_white_list`` → ``reset_white_list_in_session`` + sm(read_only=False)."""
    fake_session = MagicMock(name="reset_write_session")
    child = AsyncMock(
        return_value=HardStatusResetOutcome(blocked=True, mutated=False)
    )
    sm_mock = MagicMock(return_value=_session_cm(fake_session))
    callback = MagicMock()
    callback.from_user = SimpleNamespace(id=9)
    callback_data = SimpleNamespace(adv_setting_original_id=10)
    bot = AsyncMock()
    state = AsyncMock()

    with (
        patch(f"{_ADD}.sm", sm_mock),
        patch(f"{_ADD}.reset_white_list_in_session", child),
    ):
        await add_white_phrases.reset_white_list(
            callback, bot, state, callback_data
        )

    child.assert_awaited_once_with(fake_session, adv_setting_id=10)
    sm_mock.assert_called_with(read_only=False)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_change_keyword_hard_status_hands_off_write_session() -> None:
    """``change_keyword_hard_status`` → ``*_in_session`` + _sm(read_only=False)."""
    fake_session = MagicMock(name="hs_write_session")
    child = AsyncMock(
        return_value=KeywordHardStatusChangeOutcome(kind="blocked")
    )
    sm_mock = MagicMock(return_value=_session_cm(fake_session))
    callback = MagicMock()
    callback.message = MagicMock()
    callback.message.chat = MagicMock()
    callback.message.chat.id = 7
    callback.from_user = MagicMock()
    callback.from_user.id = 99
    callback_data = SimpleNamespace(
        new_hard_status=2, keyword_setting_original_id=42
    )
    state = AsyncMock()
    state.get_data = AsyncMock(return_value={"last_keyword_setting_page": 1})
    bot = AsyncMock()
    typing_cm = MagicMock()
    typing_cm.__aenter__ = AsyncMock(return_value=None)
    typing_cm.__aexit__ = AsyncMock(return_value=None)

    with (
        patch(f"{_KS}._sm", sm_mock),
        patch(f"{_KS}.change_keyword_hard_status_in_session", child),
        patch(f"{_KS}.ChatActionSender.typing", return_value=typing_cm),
    ):
        await keyword_settings.change_keyword_hard_status(
            callback, callback_data, bot, state
        )

    child.assert_awaited_once_with(
        fake_session,
        keyword_setting_original_id=42,
        new_hard_status=2,
    )
    sm_mock.assert_called_with(read_only=False)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_change_keyword_hard_status_in_session_blocks_under_hold() -> None:
    """Child seam: structural freeze → kind=blocked, no commit."""
    keyword = SimpleNamespace(
        id=42,
        hard_status=1,
        relevant=True,
        adv_setting=SimpleNamespace(
            bot_active=True,
            strategy=None,
            card_ab_hold_mode=CardAbHoldMode.ACTIVE.value,
        ),
    )
    result = MagicMock()
    result.scalar = MagicMock(return_value=keyword)
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()

    outcome = await keyword_settings.change_keyword_hard_status_in_session(
        session,
        keyword_setting_original_id=42,
        new_hard_status=2,
    )
    assert outcome.kind == "blocked"
    assert keyword.hard_status == 1
    session.commit.assert_not_called()
