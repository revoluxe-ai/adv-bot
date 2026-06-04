"""Unit tests for rebind_adv_campaign_ids handlers."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Chat, Message, User

from app.client_bot.user_interface.handlers import rebind_adv_campaign_ids
from app.client_bot.user_interface.states import RebindCampaignIds
from app.client_bot.user_interface.views import callbacks
from app.modules.connect_existing_advs.candidates_service import (
    classify_wb_campaign_for_rebind,
)

MODULE = "app.client_bot.user_interface.handlers.rebind_adv_campaign_ids"


def _make_callback(
    callback_data: callbacks.RebindAdvCampaignIds,
    chat_id: int = 12345,
    from_user_id: int = 67890,
) -> CallbackQuery:
    cb = MagicMock(spec=CallbackQuery)
    cb.message = MagicMock()
    cb.message.chat = MagicMock(spec=Chat)
    cb.message.chat.id = chat_id
    cb.from_user = MagicMock(spec=User)
    cb.from_user.id = from_user_id
    cb.answer = AsyncMock()
    cb.bot = MagicMock()
    cb.bot.send_message = AsyncMock()
    return cb


def _make_message(
    chat_id: int = 12345,
    text: str | None = "555",
    from_user_id: int = 67890,
) -> Message:
    msg = MagicMock(spec=Message)
    msg.chat = MagicMock(spec=Chat)
    msg.chat.id = chat_id
    msg.text = text
    msg.from_user = MagicMock(spec=User)
    msg.from_user.id = from_user_id
    msg.answer = AsyncMock()
    msg.bot = MagicMock()
    msg.bot.send_message = AsyncMock()
    return msg


def _adv_mock(
    adv_setting_id: int = 1,
    adv_id: int = 100,
    search_adv_id: int | None = 200,
    shop_id: str = "shop1",
) -> MagicMock:
    adv = MagicMock()
    adv.id = adv_setting_id
    adv.adv_id = adv_id
    adv.search_adv_id = search_adv_id
    adv.wb_cabinet = MagicMock()
    adv.wb_cabinet.shop_id = shop_id
    adv.wb_cabinet_id = 1
    return adv


@pytest.mark.unit
@pytest.mark.asyncio
async def test_open_rebind_menu_sends_message() -> None:
    bot = MagicMock()
    bot.send_message = AsyncMock()
    data = callbacks.RebindAdvCampaignIds(
        action="menu",
        adv_setting_original_id=1,
        wb_user_cabinet_original_id=10,
    )
    cb = _make_callback(data)
    await rebind_adv_campaign_ids.open_rebind_menu(cb, data, bot)
    bot.send_message.assert_called_once()
    call_kw = bot.send_message.call_args
    assert call_kw[0][0] == 12345
    assert "что изменить" in call_kw[0][1].lower()
    assert call_kw[1]["reply_markup"] is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_rebind_auto_sets_state_and_prompts() -> None:
    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock(spec=FSMContext)
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    data = callbacks.RebindAdvCampaignIds(
        action="auto",
        adv_setting_original_id=7,
        wb_user_cabinet_original_id=3,
    )
    cb = _make_callback(data)
    await rebind_adv_campaign_ids.start_rebind_auto(cb, data, bot, state)

    state.update_data.assert_awaited_once_with(
        adv_setting_original_id=7,
        wb_user_cabinet_original_id=3,
    )
    state.set_state.assert_awaited_once_with(
        RebindCampaignIds.waiting_for_auto_adv_id
    )
    bot.send_message.assert_called_once()
    assert "единой ставкой" in bot.send_message.call_args[0][1]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_auto_adv_id_invalid_text() -> None:
    bot = MagicMock()
    state = MagicMock(spec=FSMContext)
    state.get_data = AsyncMock(
        return_value={
            "adv_setting_original_id": 1,
            "wb_user_cabinet_original_id": 10,
        }
    )
    msg = _make_message(text="abc")
    await rebind_adv_campaign_ids.apply_auto_adv_id(msg, bot, state)
    msg.answer.assert_called_once()
    assert "целое" in msg.answer.call_args[0][0].lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_auto_rejects_id_equal_to_search_adv() -> None:
    """Нельзя привязать тот же ID, что уже у поисковой РК."""
    bot = MagicMock()
    state = MagicMock(spec=FSMContext)
    state.get_data = AsyncMock(
        return_value={
            "adv_setting_original_id": 1,
            "wb_user_cabinet_original_id": 10,
        }
    )

    adv = _adv_mock(adv_id=100, search_adv_id=200)
    msg = _make_message(text="200")

    with patch(f"{MODULE}.sm") as mock_sm:
        session_mock = MagicMock()
        session_mock.__aenter__ = AsyncMock(return_value=session_mock)
        session_mock.__aexit__ = AsyncMock(return_value=None)
        mock_sm.return_value = session_mock

        result_read = MagicMock()
        result_read.scalar_one_or_none.return_value = adv
        session_mock.execute = AsyncMock(return_value=result_read)

        with patch(f"{MODULE}._validate_wb_campaign_kind", new_callable=AsyncMock) as v:
            await rebind_adv_campaign_ids.apply_auto_adv_id(msg, bot, state)

    v.assert_not_called()
    msg.answer.assert_called_once()
    assert "поисковой" in msg.answer.call_args[0][0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_search_rejects_id_equal_to_auto_adv() -> None:
    bot = MagicMock()
    state = MagicMock(spec=FSMContext)
    state.get_data = AsyncMock(
        return_value={
            "adv_setting_original_id": 1,
            "wb_user_cabinet_original_id": 10,
        }
    )

    adv = _adv_mock(adv_id=100, search_adv_id=200)
    msg = _make_message(text="100")

    with patch(f"{MODULE}.sm") as mock_sm:
        session_mock = MagicMock()
        session_mock.__aenter__ = AsyncMock(return_value=session_mock)
        session_mock.__aexit__ = AsyncMock(return_value=None)
        mock_sm.return_value = session_mock

        result_read = MagicMock()
        result_read.scalar_one_or_none.return_value = adv
        session_mock.execute = AsyncMock(return_value=result_read)

        with patch(f"{MODULE}._validate_wb_campaign_kind", new_callable=AsyncMock) as v:
            await rebind_adv_campaign_ids.apply_search_adv_id(msg, bot, state)

    v.assert_not_called()
    msg.answer.assert_called_once()
    assert "автокампанией" in msg.answer.call_args[0][0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_auto_wb_validation_failed() -> None:
    bot = MagicMock()
    state = MagicMock(spec=FSMContext)
    state.get_data = AsyncMock(
        return_value={
            "adv_setting_original_id": 1,
            "wb_user_cabinet_original_id": 10,
        }
    )

    adv = _adv_mock(adv_id=100, search_adv_id=200)
    msg = _make_message(text="999")

    with patch(f"{MODULE}.sm") as mock_sm:
        session_mock = MagicMock()
        session_mock.__aenter__ = AsyncMock(return_value=session_mock)
        session_mock.__aexit__ = AsyncMock(return_value=None)
        mock_sm.return_value = session_mock

        result_read = MagicMock()
        result_read.scalar_one_or_none.return_value = adv
        session_mock.execute = AsyncMock(return_value=result_read)

        with patch(
            f"{MODULE}._validate_wb_campaign_kind",
            new_callable=AsyncMock,
            return_value=(False, "ошибка wb"),
        ):
            await rebind_adv_campaign_ids.apply_auto_adv_id(msg, bot, state)

    msg.answer.assert_called_once_with("ошибка wb")


@pytest.mark.unit
def test_classify_wb_campaign_for_rebind_excluded_status() -> None:
    from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models.get_adverts_adverts_item_status import (  # noqa: E501
        GetAdvertsAdvertsItemStatus,
    )

    item = MagicMock()
    item.status = GetAdvertsAdvertsItemStatus.VALUE_NEGATIVE_1
    assert classify_wb_campaign_for_rebind(item) is None
