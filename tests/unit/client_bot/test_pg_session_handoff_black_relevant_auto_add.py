"""Mock-only regression: PG parent→child session handoff for PBH-012/013/014.

Доказывает injectable ``*_in_session`` для add_black_phrases /
add_relevant_phrase_templates / auto_add_only_relevant_phrase_toggle:
parent открывает ``sm(read_only=…)`` и передаёт session в child.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import Message

from app.client_bot.user_interface.handlers import (
    add_black_phrases,
    add_relevant_phrase_templates,
    auto_add_only_relevant_phrase_toggle,
)
from app.client_bot.user_interface.handlers.auto_add_only_relevant_phrase_toggle import (
    AutoAddOnlyRelevantToggleOutcome,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
)

_BLACK = "app.client_bot.user_interface.handlers.add_black_phrases"
_REL = "app.client_bot.user_interface.handlers.add_relevant_phrase_templates"
_TOGGLE = (
    "app.client_bot.user_interface.handlers.auto_add_only_relevant_phrase_toggle"
)


def _session_cm(session: MagicMock) -> MagicMock:
    """Async context manager yielding ``session``."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm


@pytest.mark.unit
@pytest.mark.asyncio
async def test_waiting_for_black_phrases_hands_off_read_session() -> None:
    """``waiting_for_black_phrases`` → load child + sm(read_only=True)."""
    fake_session = MagicMock(name="black_read_session")
    adv = SimpleNamespace(
        id=42, card_ab_hold_mode=CardAbHoldMode.ACTIVE.value
    )
    load_child = AsyncMock(return_value=adv)
    sm_mock = MagicMock(return_value=_session_cm(fake_session))
    message = MagicMock()
    message.text = "a\nb"
    message.answer = AsyncMock()
    message.from_user = SimpleNamespace(id=1)
    state = AsyncMock()
    state.get_data = AsyncMock(return_value={"last_adv_setting_id": 42})
    bot = AsyncMock()
    manager = MagicMock()
    manager.update_black_phrases = AsyncMock()

    with (
        patch(f"{_BLACK}.sm", sm_mock),
        patch(f"{_BLACK}.load_adv_setting_in_session", load_child),
        patch(f"{_BLACK}.RelevantPhraseManager", return_value=manager),
    ):
        await add_black_phrases.waiting_for_black_phrases(message, bot, state)

    load_child.assert_awaited_once_with(fake_session, 42)
    sm_mock.assert_called_with(read_only=True)
    manager.update_black_phrases.assert_not_called()
    message.answer.assert_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reset_black_phrases_hands_off_read_session() -> None:
    """``reset_black_phrases`` → load child + sm(read_only=True) before freeze gate."""
    fake_session = MagicMock(name="black_reset_read_session")
    adv = SimpleNamespace(
        id=10, card_ab_hold_mode=CardAbHoldMode.PENDING_SETUP.value
    )
    load_child = AsyncMock(return_value=adv)
    sm_mock = MagicMock(return_value=_session_cm(fake_session))
    callback = MagicMock()
    callback.from_user = SimpleNamespace(id=9)
    callback_data = SimpleNamespace(adv_setting_id=10)
    bot = AsyncMock()
    manager = MagicMock()
    manager.update_black_phrases = AsyncMock()

    with (
        patch(f"{_BLACK}.sm", sm_mock),
        patch(f"{_BLACK}.load_adv_setting_in_session", load_child),
        patch(f"{_BLACK}.RelevantPhraseManager", return_value=manager),
    ):
        await add_black_phrases.reset_black_phrases(callback, bot, callback_data)

    load_child.assert_awaited_once_with(fake_session, 10)
    sm_mock.assert_called_with(read_only=True)
    manager.update_black_phrases.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_waiting_for_relevant_phrase_templates_hands_off_read_session() -> None:
    """``waiting_for_relevant_phrase_templates`` → load child + sm(read_only=True)."""
    fake_session = MagicMock(name="rel_read_session")
    adv = SimpleNamespace(
        id=42, card_ab_hold_mode=CardAbHoldMode.ACTIVE.value
    )
    load_child = AsyncMock(return_value=adv)
    sm_mock = MagicMock(return_value=_session_cm(fake_session))
    message = MagicMock()
    message.text = "a\nb"
    message.answer = AsyncMock()
    message.from_user = SimpleNamespace(id=1)
    state = AsyncMock()
    state.get_data = AsyncMock(return_value={"last_adv_setting_id": 42})
    bot = AsyncMock()
    update_mock = AsyncMock()

    with (
        patch(f"{_REL}.sm", sm_mock),
        patch(f"{_REL}.load_adv_setting_in_session", load_child),
        patch(f"{_REL}.dm_update_relevant_phrases_templates", update_mock),
    ):
        await add_relevant_phrase_templates.waiting_for_relevant_phrase_templates(
            message, bot, state
        )

    load_child.assert_awaited_once_with(fake_session, 42)
    sm_mock.assert_called_with(read_only=True)
    update_mock.assert_not_called()
    message.answer.assert_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reset_relevant_phrase_templates_hands_off_read_session() -> None:
    """``reset_relevant_phrase_templates`` → load child + sm(read_only=True)."""
    fake_session = MagicMock(name="rel_reset_read_session")
    adv = SimpleNamespace(
        id=10, card_ab_hold_mode=CardAbHoldMode.PENDING_SETUP.value
    )
    load_child = AsyncMock(return_value=adv)
    sm_mock = MagicMock(return_value=_session_cm(fake_session))
    callback = MagicMock()
    callback.from_user = SimpleNamespace(id=9)
    callback.message = MagicMock()
    callback_data = SimpleNamespace(adv_setting_id=10)
    bot = AsyncMock()
    reset_mock = AsyncMock()

    with (
        patch(f"{_REL}.sm", sm_mock),
        patch(f"{_REL}.load_adv_setting_in_session", load_child),
        patch(f"{_REL}.dm_reset_relevant_phrases_templates", reset_mock),
    ):
        await add_relevant_phrase_templates.reset_relevant_phrase_templates(
            callback, bot, callback_data
        )

    load_child.assert_awaited_once_with(fake_session, 10)
    sm_mock.assert_called_with(read_only=True)
    reset_mock.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_toggle_auto_add_only_relevant_hands_off_write_session() -> None:
    """``toggle_auto_add_only_relevant_phrase`` → WRITE child + sm(read_only=False)."""
    fake_session = MagicMock(name="toggle_write_session")
    adv = SimpleNamespace(
        id=42,
        adv_id=10,
        card_ab_hold_mode=CardAbHoldMode.ACTIVE.value,
        auto_add_only_relevant_phrase=False,
    )
    child = AsyncMock(
        return_value=AutoAddOnlyRelevantToggleOutcome(
            blocked=True, mutated=False, adv=adv
        )
    )
    sm_mock = MagicMock(return_value=_session_cm(fake_session))
    callback = MagicMock()
    callback.from_user = SimpleNamespace(id=9)
    # spec=Message so handler isinstance(callback.message, Message) passes.
    callback.message = MagicMock(spec=Message)
    callback.message.chat = SimpleNamespace(id=9)
    callback.message.answer = AsyncMock()
    callback_data = SimpleNamespace(adv_id=10, new_status=True)
    bot = AsyncMock()

    with (
        patch(f"{_TOGGLE}.sm", sm_mock),
        patch(f"{_TOGGLE}.toggle_auto_add_only_relevant_phrase_in_session", child),
    ):
        await auto_add_only_relevant_phrase_toggle.toggle_auto_add_only_relevant_phrase(
            callback, callback_data, bot
        )

    child.assert_awaited_once_with(
        fake_session, adv_id=10, new_status=True
    )
    sm_mock.assert_called_with(read_only=False)
    callback.message.answer.assert_awaited()
    bot.send_message.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_toggle_auto_add_only_relevant_in_session_blocks_under_hold() -> None:
    """Child WRITE seam: structural freeze → blocked, no commit."""
    adv = SimpleNamespace(
        id=42,
        adv_id=10,
        card_ab_hold_mode=CardAbHoldMode.ACTIVE.value,
        auto_add_only_relevant_phrase=False,
    )
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=adv)
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()

    outcome = await (
        auto_add_only_relevant_phrase_toggle.toggle_auto_add_only_relevant_phrase_in_session(
            session, adv_id=10, new_status=True
        )
    )
    assert outcome.blocked is True
    assert outcome.mutated is False
    session.commit.assert_not_called()
