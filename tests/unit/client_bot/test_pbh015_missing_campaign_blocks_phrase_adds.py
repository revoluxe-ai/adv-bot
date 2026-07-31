"""FINDING-PBH-015 RED: missing AdvSetting must block white/fixed/relevant adds.

ADL ``card-ab-hold-write-path-ownership`` residual after closed PBH-011:
``waiting_for_white_phrases`` / ``waiting_for_fixed_phrases`` /
``waiting_for_relevant_phrases`` gate only when
``load_adv_card_ab_hold_mode_in_session`` returns non-None mode AND
``is_ab_hold_structural_freeze(mode)``. When AdvSetting is missing
(``session.get`` → ``None`` → mode ``None``), handlers still call
``data_manager.add_*_phrases``, bypassing both Hold freeze and the
campaign-not-found stop used by peer handlers
(``add_black_phrases`` / ``add_relevant_phrase_templates`` →
``Кампания не найдена.``).

Regression: missing campaign → no membership write + campaign-not-found stop.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.client_bot.user_interface.handlers import add_white_phrases

MODULE = "app.client_bot.user_interface.handlers.add_white_phrases"
CAMPAIGN_NOT_FOUND_MSG = "Кампания не найдена."


def _make_message(*, text: str = "phrase one\nphrase two") -> MagicMock:
    """Create mock Telegram message with phrase list text."""
    message = MagicMock()
    message.text = text
    message.from_user = SimpleNamespace(id=777)
    message.chat = SimpleNamespace(id=777)
    message.answer = AsyncMock()
    return message


def _make_state(*, adv_setting_id: int = 42) -> AsyncMock:
    """Create FSM state carrying last_adv_setting_id for phrase handlers."""
    state = AsyncMock()
    state.get_data = AsyncMock(return_value={"last_adv_setting_id": adv_setting_id})
    state.set_state = AsyncMock()
    return state


def _session_missing_adv() -> AsyncMock:
    """Session mock where AdvSetting is absent (``session.get`` → ``None``)."""
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    result.scalar.return_value = None
    session.execute = AsyncMock(return_value=result)
    return session


def _patch_sm(session: AsyncMock):
    """Patch handler session maker to yield ``session``."""
    mock_sm = MagicMock()
    mock_sm.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_sm.return_value.__aexit__ = AsyncMock(return_value=None)
    return patch(f"{MODULE}.sm", mock_sm)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_waiting_for_white_phrases_blocks_when_campaign_missing() -> None:
    """Missing AdvSetting → ``add_white_phrases`` MUST NOT run; campaign-not-found."""
    bot = AsyncMock()
    state = _make_state(adv_setting_id=42)
    message = _make_message()
    session = _session_missing_adv()

    add_mock = AsyncMock()
    success_cls = MagicMock(return_value=AsyncMock())

    with (
        _patch_sm(session),
        patch(f"{MODULE}.data_manager.add_white_phrases", add_mock),
        patch(f"{MODULE}.messages.WhitePhrasesAdded", success_cls),
    ):
        await add_white_phrases.waiting_for_white_phrases(message, bot, state)

    add_mock.assert_not_called()
    success_cls.assert_not_called()
    message.answer.assert_awaited_with(CAMPAIGN_NOT_FOUND_MSG)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_waiting_for_fixed_phrases_blocks_when_campaign_missing() -> None:
    """Missing AdvSetting → ``add_fixed_phrases`` MUST NOT run; campaign-not-found."""
    bot = AsyncMock()
    state = _make_state(adv_setting_id=42)
    message = _make_message()
    session = _session_missing_adv()

    add_mock = AsyncMock()
    success_cls = MagicMock(return_value=AsyncMock())

    with (
        _patch_sm(session),
        patch(f"{MODULE}.data_manager.add_fixed_phrases", add_mock),
        patch(f"{MODULE}.messages.FixedPhrasesAdded", success_cls),
    ):
        await add_white_phrases.waiting_for_fixed_phrases(message, bot, state)

    add_mock.assert_not_called()
    success_cls.assert_not_called()
    message.answer.assert_awaited_with(CAMPAIGN_NOT_FOUND_MSG)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_waiting_for_relevant_phrases_blocks_when_campaign_missing() -> None:
    """Missing AdvSetting → ``add_relevant_phrases`` MUST NOT run; campaign-not-found."""
    bot = AsyncMock()
    state = _make_state(adv_setting_id=42)
    message = _make_message()
    session = _session_missing_adv()

    add_mock = AsyncMock()
    success_cls = MagicMock(return_value=AsyncMock())
    long_op = MagicMock(return_value=AsyncMock())

    with (
        _patch_sm(session),
        patch(f"{MODULE}.data_manager.add_relevant_phrases", add_mock),
        patch(f"{MODULE}.messages.RelevantPhrasesAdded", success_cls),
        patch(f"{MODULE}.messages.LongTimeOperation", long_op),
    ):
        await add_white_phrases.waiting_for_relevant_phrases(message, bot, state)

    add_mock.assert_not_called()
    success_cls.assert_not_called()
    long_op.assert_not_called()
    message.answer.assert_awaited_with(CAMPAIGN_NOT_FOUND_MSG)
