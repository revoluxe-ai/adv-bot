"""FINDING-PBH-011 RED: add_white/fixed/relevant phrases must freeze under A/B Hold.

ADL ``card-ab-hold-write-path-ownership`` §3 / §8 / §15:
ordinary Telegram membership mutators (``data_manager.add_*_phrases``) are
Forbidden under ``PENDING_SETUP`` / ``ACTIVE``; keyword-set change is owned by
WARM_UP ``keyword_edit_open`` only. Success UX on a freeze-violating path is
Forbidden.

Peer writers already gate Hold:
- ``keyword_settings`` → ``is_ab_hold_structural_freeze`` before TP write
- ``set_common_bid_manual`` → ``is_ab_hold_structural_freeze``
- ``change_auto_bid`` → ``is_ab_hold_auto_bid_manual_blocked``

Regression: Hold gate before ``data_manager.add_*_phrases`` is required.
Asserts observable membership-write silence under PENDING_SETUP / ACTIVE
(not source-token wiring alone).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.client_bot.user_interface.handlers import add_white_phrases
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
)

MODULE = "app.client_bot.user_interface.handlers.add_white_phrases"


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
async def test_waiting_for_white_phrases_blocks_membership_under_hold(
    hold_mode: str,
) -> None:
    """PENDING_SETUP / ACTIVE → ``add_white_phrases`` MUST NOT run; no success UX."""
    bot = AsyncMock()
    state = _make_state(adv_setting_id=42)
    message = _make_message()
    session, _adv = _session_with_hold_adv(hold_mode=hold_mode, adv_setting_id=42)

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


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "hold_mode",
    [
        CardAbHoldMode.PENDING_SETUP.value,
        CardAbHoldMode.ACTIVE.value,
    ],
)
async def test_waiting_for_fixed_phrases_blocks_membership_under_hold(
    hold_mode: str,
) -> None:
    """PENDING_SETUP / ACTIVE → ``add_fixed_phrases`` MUST NOT run; no success UX."""
    bot = AsyncMock()
    state = _make_state(adv_setting_id=42)
    message = _make_message()
    session, _adv = _session_with_hold_adv(hold_mode=hold_mode, adv_setting_id=42)

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


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "hold_mode",
    [
        CardAbHoldMode.PENDING_SETUP.value,
        CardAbHoldMode.ACTIVE.value,
    ],
)
async def test_waiting_for_relevant_phrases_blocks_membership_under_hold(
    hold_mode: str,
) -> None:
    """PENDING_SETUP / ACTIVE → ``add_relevant_phrases`` MUST NOT run; no success UX."""
    bot = AsyncMock()
    state = _make_state(adv_setting_id=42)
    message = _make_message()
    session, _adv = _session_with_hold_adv(hold_mode=hold_mode, adv_setting_id=42)

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
