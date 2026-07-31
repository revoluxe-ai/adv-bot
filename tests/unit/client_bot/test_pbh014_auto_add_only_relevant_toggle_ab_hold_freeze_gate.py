"""FINDING-PBH-014 RED: auto_add_only_relevant_phrase toggle must freeze under A/B Hold.

ADL ``card-ab-hold-write-path-ownership`` §3 / §8 / §15:
ordinary Telegram allowed-set / membership-classification mutators
(``toggle_auto_add_only_relevant_phrase`` → WRITE
``update(AdvSetting).values({auto_add_only_relevant_phrase})`` + commit)
are Forbidden under ``PENDING_SETUP`` / ``ACTIVE``; keyword-set /
membership-policy change is owned by WARM_UP ``keyword_edit_open`` only.
Success/menu UX on a freeze-violating path is Forbidden.

Peer writers already gate Hold:
- ``keyword_settings`` → ``is_ab_hold_structural_freeze`` before TP write
- ``set_common_bid_manual`` → ``is_ab_hold_structural_freeze``
- ``add_white_phrases`` (PBH-011) → Hold gate before ``data_manager.add_*_phrases``
- ``add_black_phrases`` (PBH-012) → Hold gate before ``update_black_phrases``
- ``add_relevant_phrase_templates`` (PBH-013) → Hold gate before template write

Regression: Hold gate before AdvSetting.auto_add_only_relevant_phrase
membership-policy write is required on
``toggle_auto_add_only_relevant_phrase`` (~:54). Asserts observable
membership-write silence under PENDING_SETUP / ACTIVE, freeze answer UX,
and forbidden success/menu UX on the freeze path.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import Message

from app.client_bot.user_interface.handlers import (
    auto_add_only_relevant_phrase_toggle,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
)

MODULE = (
    "app.client_bot.user_interface.handlers.auto_add_only_relevant_phrase_toggle"
)


def _make_callback(*, adv_id: int = 10) -> tuple[MagicMock, SimpleNamespace]:
    """Minimal CallbackQuery + ChangeAutoAddOnlyRelevantPhraseStatus-like data."""
    callback = MagicMock()
    callback.from_user = SimpleNamespace(id=777)
    # spec=Message so handler isinstance(callback.message, Message) passes.
    callback.message = MagicMock(spec=Message)
    callback.message.chat = SimpleNamespace(id=777)
    callback.message.answer = AsyncMock()
    callback.answer = AsyncMock()
    callback_data = SimpleNamespace(
        adv_id=adv_id,
        wb_user_cabinet_original_id=0,
        new_status=True,
    )
    return callback, callback_data


def _session_with_hold_adv(*, hold_mode: str, adv_id: int = 10):
    """Session mock returning AdvSetting with explicit A/B Hold mode."""
    adv = SimpleNamespace(
        id=42,
        adv_id=adv_id,
        auto_add_only_relevant_phrase=False,
        card_ab_hold_mode=hold_mode,
    )
    session = AsyncMock()
    session.get = AsyncMock(return_value=adv)
    session.commit = AsyncMock()
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
async def test_toggle_auto_add_only_relevant_phrase_blocks_membership_under_hold(
    hold_mode: str,
) -> None:
    """PENDING_SETUP / ACTIVE → AdvSetting membership-policy WRITE MUST NOT run."""
    bot = AsyncMock()
    callback, callback_data = _make_callback(adv_id=10)
    session, _adv = _session_with_hold_adv(hold_mode=hold_mode, adv_id=10)
    menu_cls = MagicMock(return_value=AsyncMock())

    with (
        _patch_sm(session),
        patch(f"{MODULE}.RelevantPhraseManagementMenuMessage", menu_cls),
    ):
        await auto_add_only_relevant_phrase_toggle.toggle_auto_add_only_relevant_phrase(
            callback, callback_data, bot
        )

    session.commit.assert_not_called()
    bot.send_message.assert_not_called()
    menu_cls.assert_not_called()
    callback.message.answer.assert_awaited()
