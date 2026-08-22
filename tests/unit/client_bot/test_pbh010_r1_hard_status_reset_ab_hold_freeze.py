"""FINDING-PBH-010-R1: hard_status reset mutators must freeze under A/B Hold.

Same freeze-gate class as FINDING-PBH-010 ``change_keyword_hard_status``:
``reset_white_list``, ``reset_non_relevant_phrases``, and shop
``update_keywords`` must refuse / skip PENDING_SETUP / ACTIVE before
hard_status mutation (ADL OP-008 / §3).

Do not reopen CLOSED PBH-004 / EPOCHCAPDEG / SA-ZLPR. Distinct from
PBH-011 add_* membership and PBH-009 hold_guards TP.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.client_bot.user_interface.handlers.add_white_phrases import (
    AB_HOLD_HARD_STATUS_RESET_BLOCKED_MSG,
    reset_non_relevant_phrases,
    reset_white_list,
)
from app.client_bot.user_interface.handlers.adv_setting.utils import keyword_updater
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
)

_ADD = "app.client_bot.user_interface.handlers.add_white_phrases"


@pytest.mark.unit
def test_pbh010_r1_update_keywords_filter_excludes_structural_freeze_modes() -> None:
    """``_non_frozen_adv_setting_filter`` must exclude PENDING_SETUP/ACTIVE."""
    clause = keyword_updater._non_frozen_adv_setting_filter()
    compiled = str(clause.compile(compile_kwargs={"literal_binds": True}))
    assert CardAbHoldMode.PENDING_SETUP.value in compiled
    assert CardAbHoldMode.ACTIVE.value in compiled


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "hold_mode",
    [
        CardAbHoldMode.PENDING_SETUP.value,
        CardAbHoldMode.ACTIVE.value,
    ],
)
async def test_pbh010_r1_reset_white_list_blocked_on_ab_hold(hold_mode: str) -> None:
    """PENDING_SETUP / ACTIVE → reset_white_list MUST NOT mutate hard_status."""
    adv = SimpleNamespace(
        id=10,
        bot_active=True,
        strategy=None,
        card_ab_hold_mode=hold_mode,
    )
    keyword = SimpleNamespace(hard_status=2)
    session = AsyncMock()
    session.get = AsyncMock(return_value=adv)
    result = MagicMock()
    result.scalars = MagicMock(
        return_value=MagicMock(all=MagicMock(return_value=[keyword]))
    )
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()

    mock_sm = MagicMock()
    mock_sm.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_sm.return_value.__aexit__ = AsyncMock(return_value=None)

    callback = MagicMock()
    callback.from_user = SimpleNamespace(id=99)
    callback_data = SimpleNamespace(adv_setting_original_id=10)
    bot = AsyncMock()
    state = AsyncMock()
    sync_mock = MagicMock(return_value=False)

    with (
        patch(f"{_ADD}.sm", mock_sm),
        patch(f"{_ADD}.sync_keyword_setting_mode_for_v3", sync_mock),
    ):
        await reset_white_list(callback, bot, state, callback_data)

    assert keyword.hard_status == 2
    sync_mock.assert_not_called()
    session.commit.assert_not_called()
    assert any(
        AB_HOLD_HARD_STATUS_RESET_BLOCKED_MSG in str(c)
        for c in bot.send_message.call_args_list
    )


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "hold_mode",
    [
        CardAbHoldMode.PENDING_SETUP.value,
        CardAbHoldMode.ACTIVE.value,
    ],
)
async def test_pbh010_r1_reset_non_relevant_phrases_blocked_on_ab_hold(
    hold_mode: str,
) -> None:
    """PENDING_SETUP / ACTIVE → reset_non_relevant_phrases MUST NOT execute UPDATE."""
    adv = SimpleNamespace(
        id=10,
        bot_active=True,
        strategy=None,
        card_ab_hold_mode=hold_mode,
    )
    session = AsyncMock()
    session.get = AsyncMock(return_value=adv)
    session.execute = AsyncMock()
    session.commit = AsyncMock()

    mock_sm = MagicMock()
    mock_sm.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_sm.return_value.__aexit__ = AsyncMock(return_value=None)

    callback = MagicMock()
    callback.from_user = SimpleNamespace(id=99)
    callback_data = SimpleNamespace(adv_setting_original_id=10)
    bot = AsyncMock()
    state = AsyncMock()

    with patch(f"{_ADD}.sm", mock_sm):
        await reset_non_relevant_phrases(callback, bot, state, callback_data)

    session.execute.assert_not_called()
    session.commit.assert_not_called()
    assert any(
        AB_HOLD_HARD_STATUS_RESET_BLOCKED_MSG in str(c)
        for c in bot.send_message.call_args_list
    )

