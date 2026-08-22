"""FINDING-PBH-004-R1 RED: Telegram set_common_bid_manual must freeze under A/B Hold.

Invariant INV/BUGCASE-PBH-004/9c69522a + writer inventory OP-008:
ordinary Search common-bid WB writes (SetCommonBids / update_search_adv_common_cpm)
are Allowed OFF only. PENDING_SETUP / ACTIVE are Forbidden for manual Telegram
``set_common_bid_manual_apply`` as for shop-runner ``update_common_bid_in_search_adv``.

Peer manual writers already gate Hold:
- keyword_settings → ``is_ab_hold_structural_freeze`` before TP write
- change_auto_bid → ``is_ab_hold_auto_bid_manual_blocked``

Regression: Hold gate before ``update_search_adv_common_cpm`` is required.
Asserts observable WB write silence under PENDING_SETUP / ACTIVE (not
source-token wiring).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.types import Chat, Message, User

from app.client_bot.user_interface.handlers import set_common_bid_manual
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
)

MODULE = "app.client_bot.user_interface.handlers.set_common_bid_manual"


def _make_message(
    chat_id: int = 111,
    text: str | None = "100",
    from_user_id: int = 67890,
) -> Message:
    """Create mock Message for apply handler."""
    msg = MagicMock(spec=Message)
    msg.chat = MagicMock(spec=Chat)
    msg.chat.id = chat_id
    msg.text = text
    msg.from_user = MagicMock(spec=User)
    msg.from_user.id = from_user_id
    msg.answer = AsyncMock()
    return msg


def _make_adv_setting(
    *,
    adv_setting_id: int = 1,
    search_adv_id: int | None = 999,
    shop_id: str = "shop123",
    nmids: list[int] | None = None,
    adv_id: int = 100,
    card_ab_hold_mode: str = CardAbHoldMode.OFF.value,
) -> MagicMock:
    """Create mock AdvSetting with explicit A/B Hold mode."""
    adv = MagicMock()
    adv.id = adv_setting_id
    adv.search_adv_id = search_adv_id
    adv.wb_cabinet = MagicMock()
    adv.wb_cabinet.shop_id = shop_id
    adv.nmids = nmids or [12345, 67890]
    adv.adv_id = adv_id
    adv.card_ab_hold_mode = card_ab_hold_mode
    adv.plan_for_sales_for_day = None
    adv.target_price_for_order = None
    adv.max_price_for_order = None
    return adv


def _make_wb_user_cabinet(cabinet_id: int = 10) -> MagicMock:
    """Create mock WBUserCabinet."""
    cabinet = MagicMock()
    cabinet.id = cabinet_id
    return cabinet


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "hold_mode",
    [
        CardAbHoldMode.PENDING_SETUP.value,
        CardAbHoldMode.ACTIVE.value,
    ],
)
async def test_set_common_bid_manual_apply_blocks_wb_write_under_hold(
    hold_mode: str,
) -> None:
    """PENDING_SETUP / ACTIVE → update_search_adv_common_cpm MUST NOT run.

    Observable freeze gate (not source-token): structural Hold forbids ordinary
    Search common-bid SetCommonBids from Telegram apply.
    """
    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock(spec=FSMContext)
    state.get_data = AsyncMock(
        return_value={
            "adv_setting_original_id": 1,
            "wb_user_cabinet_original_id": 10,
            "min_bid_search": 50,
        }
    )
    state.set_state = AsyncMock()

    message = _make_message(chat_id=111, text="100")

    adv_setting = _make_adv_setting(
        adv_setting_id=1,
        search_adv_id=999,
        card_ab_hold_mode=hold_mode,
    )
    search_adv_setting = _make_adv_setting(
        adv_setting_id=999,
        search_adv_id=None,
        card_ab_hold_mode=hold_mode,
    )
    wb_user_cabinet = _make_wb_user_cabinet(cabinet_id=10)

    with patch(f"{MODULE}.sm") as mock_sm:
        session_mock = MagicMock()
        session_mock.__aenter__ = AsyncMock(return_value=session_mock)
        session_mock.__aexit__ = AsyncMock(return_value=None)
        mock_sm.return_value = session_mock

        result_adv_1 = MagicMock()
        result_adv_1.scalar_one_or_none.return_value = adv_setting
        result_search = MagicMock()
        result_search.scalar_one_or_none.return_value = search_adv_setting
        result_cabinet = MagicMock()
        result_cabinet.scalar_one_or_none.return_value = wb_user_cabinet
        result_adv_2 = MagicMock()
        result_adv_2.scalar_one_or_none.return_value = adv_setting

        session_mock.execute = AsyncMock(
            side_effect=[result_adv_1, result_search, result_cabinet, result_adv_2]
        )

        with patch(f"{MODULE}.DIManager.create") as mock_di:
            container = MagicMock()
            factory = MagicMock()
            hub = MagicMock()
            hub.wb_modifier.update_search_adv_common_cpm = AsyncMock()
            hub.redis_client_wrapper = MagicMock()

            factory.get_wb_manager_hub.return_value = hub
            container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory.return_value = (
                factory
            )

            mock_di.return_value.__aenter__ = AsyncMock(return_value=container)
            mock_di.return_value.__aexit__ = AsyncMock(return_value=None)

            with patch(f"{MODULE}.RedisCommonBidValueManager"):
                with patch(f"{MODULE}.RedisCommonBidTimestampManager"):
                    with patch(f"{MODULE}.AdvSettingMenu") as mock_menu:
                        menu_instance = AsyncMock()
                        mock_menu.return_value = menu_instance

                        await set_common_bid_manual.set_common_bid_manual_apply(
                            message, bot, state
                        )

    hub.wb_modifier.update_search_adv_common_cpm.assert_not_called()
    answers = [
        call.args[0] if call.args else ""
        for call in message.answer.await_args_list
    ]
    assert not any("Общая ставка изменена" in text for text in answers), (
        f"FINDING-PBH-004-R1: success path still reached under {hold_mode}; "
        "ordinary Telegram Search common-bid apply must refuse structural freeze."
    )
