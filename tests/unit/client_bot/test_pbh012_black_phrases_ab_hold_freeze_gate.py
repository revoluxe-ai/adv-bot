"""FINDING-PBH-012 RED: add/reset black phrases must freeze under A/B Hold.

ADL ``card-ab-hold-write-path-ownership`` §3 / §8 / §15:
ordinary Telegram membership mutators (``RelevantPhraseManager.update_black_phrases``)
are Forbidden under ``PENDING_SETUP`` / ``ACTIVE``; keyword-set / NRF-template
change is owned by WARM_UP ``keyword_edit_open`` only. Success/menu UX on a
freeze-violating path is Forbidden.

Peer writers already gate Hold:
- ``keyword_settings`` → ``is_ab_hold_structural_freeze`` before TP write
- ``set_common_bid_manual`` → ``is_ab_hold_structural_freeze``
- ``add_white_phrases`` (PBH-011) → Hold gate before ``data_manager.add_*_phrases``

Regression: Hold gate before ``update_black_phrases`` is required on both
``waiting_for_black_phrases`` (add) and ``reset_black_phrases`` (reset).
Asserts observable membership-write silence under PENDING_SETUP / ACTIVE
and forbidden success UX on the freeze path.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.client_bot.user_interface.handlers import add_black_phrases
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
)

MODULE = "app.client_bot.user_interface.handlers.add_black_phrases"


def _make_message(*, text: str = "phrase one\nphrase two") -> MagicMock:
    """Create mock Telegram message with black-phrase list text."""
    message = MagicMock()
    message.text = text
    message.from_user = SimpleNamespace(id=777)
    message.chat = SimpleNamespace(id=777)
    message.answer = AsyncMock()
    return message


def _make_state(*, adv_setting_id: int = 42) -> AsyncMock:
    """Create FSM state carrying last_adv_setting_id for black-phrase handlers."""
    state = AsyncMock()
    state.get_data = AsyncMock(return_value={"last_adv_setting_id": adv_setting_id})
    state.set_state = AsyncMock()
    return state


def _make_callback(*, adv_setting_id: int = 42) -> tuple[MagicMock, SimpleNamespace]:
    """Minimal CallbackQuery + ResetBlackPhrases-like callback_data."""
    callback = MagicMock()
    callback.from_user = SimpleNamespace(id=777)
    callback.message = MagicMock()
    callback.message.answer = AsyncMock()
    callback.answer = AsyncMock()
    callback_data = SimpleNamespace(adv_setting_id=adv_setting_id)
    return callback, callback_data


def _session_with_hold_adv(*, hold_mode: str, adv_setting_id: int = 42):
    """Session mock returning AdvSetting with explicit A/B Hold mode."""
    adv = SimpleNamespace(id=adv_setting_id, card_ab_hold_mode=hold_mode)
    session = AsyncMock()
    session.get = AsyncMock(return_value=adv)
    result = MagicMock()
    result.scalar_one_or_none.return_value = adv
    result.scalar.return_value = adv
    session.execute = AsyncMock(return_value=result)
    return session, adv


def _patch_sm(session: AsyncMock):
    """Patch handler session maker to yield ``session``."""
    mock_sm = MagicMock()
    mock_sm.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_sm.return_value.__aexit__ = AsyncMock(return_value=None)
    return patch(f"{MODULE}.sm", mock_sm)


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "hold_mode",
    [
        CardAbHoldMode.PENDING_SETUP.value,
        CardAbHoldMode.ACTIVE.value,
    ],
)
async def test_waiting_for_black_phrases_blocks_membership_under_hold(
    hold_mode: str,
) -> None:
    """PENDING_SETUP / ACTIVE → ``update_black_phrases`` MUST NOT run; no success UX."""
    bot = AsyncMock()
    state = _make_state(adv_setting_id=42)
    message = _make_message()
    session, _adv = _session_with_hold_adv(hold_mode=hold_mode, adv_setting_id=42)

    update_mock = AsyncMock()
    success_cls = MagicMock(return_value=AsyncMock())
    manager_instance = MagicMock()
    manager_instance.update_black_phrases = update_mock

    with (
        _patch_sm(session),
        patch(f"{MODULE}.RelevantPhraseManager", return_value=manager_instance),
        patch(f"{MODULE}.messages.WaitingForBlackPhrases", success_cls),
    ):
        await add_black_phrases.waiting_for_black_phrases(message, bot, state)

    update_mock.assert_not_called()
    success_cls.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "hold_mode",
    [
        CardAbHoldMode.PENDING_SETUP.value,
        CardAbHoldMode.ACTIVE.value,
    ],
)
async def test_reset_black_phrases_blocks_membership_under_hold(
    hold_mode: str,
) -> None:
    """PENDING_SETUP / ACTIVE → reset ``update_black_phrases([])`` MUST NOT run."""
    bot = AsyncMock()
    callback, callback_data = _make_callback(adv_setting_id=42)
    session, _adv = _session_with_hold_adv(hold_mode=hold_mode, adv_setting_id=42)

    update_mock = AsyncMock()
    success_cls = MagicMock(return_value=AsyncMock())
    manager_instance = MagicMock()
    manager_instance.update_black_phrases = update_mock

    with (
        _patch_sm(session),
        patch(f"{MODULE}.RelevantPhraseManager", return_value=manager_instance),
        patch(f"{MODULE}.messages.WaitingForBlackPhrases", success_cls),
    ):
        await add_black_phrases.reset_black_phrases(callback, bot, callback_data)

    update_mock.assert_not_called()
    success_cls.assert_not_called()
