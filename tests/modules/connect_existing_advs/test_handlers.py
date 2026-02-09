"""Unit tests for connect_existing_advs handlers."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import CallbackQuery, Chat, Message, User

from app.client_bot.user_interface.states import ConnectExistingAdvsStates
from app.client_bot.user_interface.views import callbacks
from app.modules.connect_existing_advs.candidates_service import (
    ConnectExistingCandidatesResult,
)
from app.client_bot.user_interface.handlers import connect_existing_advs

MODULE = "app.client_bot.user_interface.handlers.connect_existing_advs"


def _make_callback(
    callback_data: callbacks.ConnectExistingAdvs
    | callbacks.ConnectExistingConfirmType1
    | callbacks.ConnectExistingConfirmType2
    | callbacks.ConnectExistingCreateBoth
    | callbacks.ConnectExistingAdvsBackToShop,
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
    return cb


def _make_message(chat_id: int = 12345, text: str | None = "12345") -> Message:
    msg = MagicMock(spec=Message)
    msg.chat = MagicMock(spec=Chat)
    msg.chat.id = chat_id
    msg.text = text
    return msg


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_existing_advs_start() -> None:
    """Start: state clear, update_data, set_state waiting_nmid, send_message."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()
    state.clear = AsyncMock()
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    callback = _make_callback(
        callbacks.ConnectExistingAdvs(wb_user_cabinet_original_id=10),
        chat_id=111,
    )
    callback_data = callbacks.ConnectExistingAdvs(wb_user_cabinet_original_id=10)

    await connect_existing_advs.connect_existing_advs_start(
        callback, callback_data, bot, state
    )

    state.clear.assert_called_once()
    state.update_data.assert_called_once_with(wb_user_cabinet_original_id=10)
    state.set_state.assert_called_once_with(ConnectExistingAdvsStates.waiting_nmid)
    bot.send_message.assert_called_once()
    call_args = bot.send_message.call_args
    assert call_args[0][0] == 111
    assert "NM-id" in call_args[0][1] and "число" in call_args[0][1]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_existing_advs_nmid_text_none() -> None:
    """nmid handler: message.text None -> send 'Отправьте NM-id числом.'."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(return_value={"wb_user_cabinet_original_id": 1})
    message = _make_message(chat_id=222, text=None)

    await connect_existing_advs.connect_existing_advs_nmid(
        message, bot, state, client_session=MagicMock()
    )

    bot.send_message.assert_called_once_with(222, "Отправьте NM-id числом.")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_existing_advs_nmid_not_int() -> None:
    """nmid handler: non-int text -> 'NM-id должен быть целым числом'."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(return_value={"wb_user_cabinet_original_id": 1})
    message = _make_message(chat_id=222, text="abc")

    await connect_existing_advs.connect_existing_advs_nmid(
        message, bot, state, client_session=MagicMock()
    )

    bot.send_message.assert_called_once_with(222, "NM-id должен быть целым числом.")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_existing_advs_nmid_zero() -> None:
    """nmid handler: 0 -> 'NM-id должен быть больше 0'."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(return_value={"wb_user_cabinet_original_id": 1})
    message = _make_message(chat_id=222, text="0")

    await connect_existing_advs.connect_existing_advs_nmid(
        message, bot, state, client_session=MagicMock()
    )

    bot.send_message.assert_called_once_with(222, "NM-id должен быть больше 0.")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_existing_advs_nmid_cabinet_not_found() -> None:
    """nmid handler: cabinet not found (row None) -> 'Кабинет не найден'."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(return_value={"wb_user_cabinet_original_id": 999})
    message = _make_message(chat_id=222, text="12345")
    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_sm = MagicMock()
    mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_sm.return_value.__aexit__ = AsyncMock(return_value=None)

    with patch(f"{MODULE}.sm", mock_sm):
        await connect_existing_advs.connect_existing_advs_nmid(
            message, bot, state, client_session=MagicMock()
        )

    bot.send_message.assert_called_once_with(222, "Кабинет не найден.")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_existing_advs_nmid_card_not_found() -> None:
    """nmid handler: CardNotFoundInWB -> 'Артикул не найден на Wildberries'."""
    from app.core.wb_api.mixins.excs import CardNotFoundInWB

    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(return_value={"wb_user_cabinet_original_id": 1})
    message = _make_message(chat_id=222, text="12345")
    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.one_or_none.return_value = (1, "shop_1")
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_sm = MagicMock()
    mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_sm.return_value.__aexit__ = AsyncMock(return_value=None)

    with patch(f"{MODULE}.sm", mock_sm), patch(
        f"{MODULE}.super_cabinet_manager.get_access_for_wb_cabinet",
        AsyncMock(),
    ), patch(f"{MODULE}.WBApi") as mock_wb_api_cls:
        mock_wb_api = MagicMock()
        mock_wb_api.get_card_by_text = AsyncMock(side_effect=CardNotFoundInWB())
        mock_wb_api_cls.return_value = mock_wb_api
        await connect_existing_advs.connect_existing_advs_nmid(
            message, bot, state, client_session=MagicMock()
        )

    assert bot.send_message.call_count == 2  # WB_WAIT_MESSAGE, then error
    assert "Артикул не найден" in bot.send_message.call_args[0][1]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_existing_advs_nmid_existing_pair() -> None:
    """nmid handler: existing_pair not None -> message and keyboard BackToShop."""
    from app.client_bot.user_interface.views.callbacks import (
        ConnectExistingAdvsBackToShop,
    )

    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(return_value={"wb_user_cabinet_original_id": 5})
    state.clear = AsyncMock()
    message = _make_message(chat_id=222, text="100")
    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.one_or_none.return_value = (1, "shop_1")
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_sm = MagicMock()
    mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_sm.return_value.__aexit__ = AsyncMock(return_value=None)

    with patch(f"{MODULE}.sm", mock_sm), patch(
        f"{MODULE}.super_cabinet_manager.get_access_for_wb_cabinet",
        AsyncMock(),
    ), patch(f"{MODULE}.WBApi") as mock_wb_api_cls, patch(
        f"{MODULE}._get_existing_adv_pair_not_done",
        AsyncMock(return_value=(100, 200)),
    ):
        mock_wb_api = MagicMock()
        mock_wb_api.get_card_by_text = AsyncMock()
        mock_wb_api_cls.return_value = mock_wb_api
        await connect_existing_advs.connect_existing_advs_nmid(
            message, bot, state, client_session=MagicMock()
        )

    state.clear.assert_called_once()
    assert bot.send_message.call_count == 2  # WB_WAIT_MESSAGE, then "уже есть подключённые"
    assert "уже есть подключённые" in bot.send_message.call_args[0][1]
    reply_markup = bot.send_message.call_args[1]["reply_markup"]
    btn = reply_markup.inline_keyboard[0][0]
    assert btn.text == "В меню магазина"
    assert ConnectExistingAdvsBackToShop.unpack(btn.callback_data) is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_existing_advs_nmid_success_both_empty() -> None:
    """nmid handler: candidates empty -> waiting_confirm_create_both, create both message."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(return_value={"wb_user_cabinet_original_id": 1})
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    message = _make_message(chat_id=222, text="100")
    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.one_or_none.return_value = (1, "shop_1")
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_sm = MagicMock()
    mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_sm.return_value.__aexit__ = AsyncMock(return_value=None)
    empty_result = ConnectExistingCandidatesResult(
        auction_candidates=[],
        auto_candidates=[],
    )

    with patch(f"{MODULE}.sm", mock_sm), patch(
        f"{MODULE}.super_cabinet_manager.get_access_for_wb_cabinet",
        AsyncMock(),
    ), patch(f"{MODULE}.WBApi") as mock_wb_api_cls, patch(
        f"{MODULE}._get_existing_adv_pair_not_done",
        AsyncMock(return_value=None),
    ), patch(
        f"{MODULE}.get_connect_existing_candidates",
        AsyncMock(return_value=empty_result),
    ):
        mock_wb_api = MagicMock()
        mock_wb_api.get_card_by_text = AsyncMock()
        mock_wb_api_cls.return_value = mock_wb_api
        await connect_existing_advs.connect_existing_advs_nmid(
            message, bot, state, client_session=MagicMock()
        )

    state.set_state.assert_called_once_with(
        ConnectExistingAdvsStates.waiting_confirm_create_both
    )
    assert bot.send_message.call_count == 2  # WB_WAIT_MESSAGE, then "Создать обе"
    assert "Создать обе" in bot.send_message.call_args[0][1]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_existing_advs_nmid_get_candidates_api_forbidden() -> None:
    """nmid handler: get_connect_existing_candidates raises ApiForbiddenError -> send no access."""
    from app.core.wb_api.exceptions import ApiForbiddenError

    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(return_value={"wb_user_cabinet_original_id": 1})
    message = _make_message(chat_id=222, text="100")
    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.one_or_none.return_value = (1, "shop_1")
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_sm = MagicMock()
    mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_sm.return_value.__aexit__ = AsyncMock(return_value=None)

    with patch(f"{MODULE}.sm", mock_sm), patch(
        f"{MODULE}.super_cabinet_manager.get_access_for_wb_cabinet",
        AsyncMock(),
    ), patch(f"{MODULE}.WBApi") as mock_wb_api_cls, patch(
        f"{MODULE}._get_existing_adv_pair_not_done",
        AsyncMock(return_value=None),
    ), patch(
        f"{MODULE}.get_connect_existing_candidates",
        AsyncMock(side_effect=ApiForbiddenError("forbidden")),
    ):
        mock_wb_api = MagicMock()
        mock_wb_api.get_card_by_text = AsyncMock()
        mock_wb_api_cls.return_value = mock_wb_api
        await connect_existing_advs.connect_existing_advs_nmid(
            message, bot, state, client_session=MagicMock()
        )

    assert bot.send_message.call_count == 2  # WB_WAIT_MESSAGE, then API error
    assert "Нет доступа к API WB" in bot.send_message.call_args[0][1]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_existing_advs_nmid_bad_request_path_not_found() -> None:
    """nmid handler: BadRequestError path not found -> empty candidates, waiting_confirm_create_both."""
    from app.core.mp.wb.api.excs import BadRequestError

    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(return_value={"wb_user_cabinet_original_id": 1})
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    message = _make_message(chat_id=222, text="100")
    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.one_or_none.return_value = (1, "shop_1")
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_sm = MagicMock()
    mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_sm.return_value.__aexit__ = AsyncMock(return_value=None)

    with patch(f"{MODULE}.sm", mock_sm), patch(
        f"{MODULE}.super_cabinet_manager.get_access_for_wb_cabinet",
        AsyncMock(),
    ), patch(f"{MODULE}.WBApi") as mock_wb_api_cls, patch(
        f"{MODULE}._get_existing_adv_pair_not_done",
        AsyncMock(return_value=None),
    ), patch(
        f"{MODULE}.get_connect_existing_candidates",
        AsyncMock(side_effect=BadRequestError("path not found")),
    ):
        mock_wb_api = MagicMock()
        mock_wb_api.get_card_by_text = AsyncMock()
        mock_wb_api_cls.return_value = mock_wb_api
        await connect_existing_advs.connect_existing_advs_nmid(
            message, bot, state, client_session=MagicMock()
        )

    state.set_state.assert_called_once_with(
        ConnectExistingAdvsStates.waiting_confirm_create_both
    )
    assert "Создать обе" in bot.send_message.call_args[0][1]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_existing_advs_nmid_success_auction_only() -> None:
    """nmid handler: only auction candidates -> confirm_type1, auction message."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(return_value={"wb_user_cabinet_original_id": 1})
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    message = _make_message(chat_id=222, text="100")
    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.one_or_none.return_value = (1, "shop_1")
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_sm = MagicMock()
    mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_sm.return_value.__aexit__ = AsyncMock(return_value=None)
    from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models import (
        GetAdvertsAdvertsItem,
    )

    mock_auction = MagicMock(spec=GetAdvertsAdvertsItem)
    mock_auction.id = 42
    mock_auction.settings.name = "AuctionCampaign"
    result_with_auction = ConnectExistingCandidatesResult(
        auction_candidates=[mock_auction],
        auto_candidates=[],
    )

    with patch(f"{MODULE}.sm", mock_sm), patch(
        f"{MODULE}.super_cabinet_manager.get_access_for_wb_cabinet",
        AsyncMock(),
    ), patch(f"{MODULE}.WBApi") as mock_wb_api_cls, patch(
        f"{MODULE}._get_existing_adv_pair_not_done",
        AsyncMock(return_value=None),
    ), patch(
        f"{MODULE}.get_connect_existing_candidates",
        AsyncMock(return_value=result_with_auction),
    ):
        mock_wb_api = MagicMock()
        mock_wb_api.get_card_by_text = AsyncMock()
        mock_wb_api_cls.return_value = mock_wb_api
        await connect_existing_advs.connect_existing_advs_nmid(
            message, bot, state, client_session=MagicMock()
        )

    state.set_state.assert_called_once_with(ConnectExistingAdvsStates.confirm_type1)
    assert bot.send_message.call_count == 2  # WB_WAIT_MESSAGE, then auction message
    assert "AuctionCampaign" in bot.send_message.call_args[0][1]
    assert "42" in bot.send_message.call_args[0][1]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_existing_confirm_type1_adv_id_zero() -> None:
    """confirm_type1: adv_id=0 -> message about next update, no confirm_type2."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(return_value={"auto_candidates": []})
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    callback = _make_callback(
        callbacks.ConnectExistingConfirmType1(adv_id=0), chat_id=333
    )
    callback_data = callbacks.ConnectExistingConfirmType1(adv_id=0)

    await connect_existing_advs.connect_existing_confirm_type1(
        callback, callback_data, bot, state
    )

    bot.send_message.assert_called_once()
    assert "Создание аукционной РК будет доступно" in bot.send_message.call_args[0][1]
    state.set_state.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_existing_confirm_type1_adv_id_set() -> None:
    """confirm_type1: adv_id=123 -> state confirm_type2, message with auto candidate."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(
        return_value={
            "auto_candidates": [{"id": 456, "name": "AutoCamp"}],
        }
    )
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    callback = _make_callback(
        callbacks.ConnectExistingConfirmType1(adv_id=123), chat_id=333
    )
    callback_data = callbacks.ConnectExistingConfirmType1(adv_id=123)

    await connect_existing_advs.connect_existing_confirm_type1(
        callback, callback_data, bot, state
    )

    state.update_data.assert_called_once_with(chosen_auction_adv_id=123)
    state.set_state.assert_called_once_with(ConnectExistingAdvsStates.confirm_type2)
    bot.send_message.assert_called_once()
    assert "AutoCamp" in bot.send_message.call_args[0][1]
    assert "456" in bot.send_message.call_args[0][1]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_existing_confirm_type2_adv_id_zero() -> None:
    """confirm_type2: adv_id=0 -> message about auto РК next update."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(return_value={})
    callback = _make_callback(
        callbacks.ConnectExistingConfirmType2(adv_id=0), chat_id=333
    )
    callback_data = callbacks.ConnectExistingConfirmType2(adv_id=0)

    await connect_existing_advs.connect_existing_confirm_type2(
        callback, callback_data, bot, state
    )

    bot.send_message.assert_called_once()
    assert "Создание авто-РК будет доступно" in bot.send_message.call_args[0][1]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_existing_confirm_type2_chosen_auction_none() -> None:
    """confirm_type2: chosen_auction_adv_id None -> 'Сначала выберите или создайте'."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(
        return_value={
            "nmid": 100,
            "wb_cabinet_id": 1,
            "chosen_auction_adv_id": None,
        }
    )
    callback = _make_callback(
        callbacks.ConnectExistingConfirmType2(adv_id=50), chat_id=333
    )
    callback_data = callbacks.ConnectExistingConfirmType2(adv_id=50)

    await connect_existing_advs.connect_existing_confirm_type2(
        callback, callback_data, bot, state
    )

    bot.send_message.assert_called_once()
    assert "Сначала выберите или создайте аукционную" in bot.send_message.call_args[0][1]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_existing_confirm_type2_creates_adv_setting() -> None:
    """confirm_type2: full flow, no existing AdvSetting -> create new, commit, message."""
    from app.modules.common_slaves.wildberries.models import AdvSetting
    from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet

    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(
        return_value={
            "nmid": 100,
            "wb_cabinet_id": 1,
            "chosen_auction_adv_id": 10,
        }
    )
    state.clear = AsyncMock()
    callback = _make_callback(
        callbacks.ConnectExistingConfirmType2(adv_id=20), chat_id=333
    )
    callback_data = callbacks.ConnectExistingConfirmType2(adv_id=20)
    mock_wb_cabinet = MagicMock(spec=WBCabinet)
    mock_session = MagicMock()
    mock_session.get = AsyncMock(return_value=mock_wb_cabinet)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_sm = MagicMock()
    mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_sm.return_value.__aexit__ = AsyncMock(return_value=None)

    with patch(f"{MODULE}.sm", mock_sm), patch(
        "app.client_bot.modules.default_settings.apply_defaults_to_adv_setting",
    ):
        await connect_existing_advs.connect_existing_confirm_type2(
            callback, callback_data, bot, state
        )

    state.clear.assert_called_once()
    mock_session.add.assert_called_once()
    added = mock_session.add.call_args[0][0]
    assert isinstance(added, AdvSetting)
    assert added.adv_id == 20
    assert added._search_adv_id == 10
    # name follows template: nmid + card_name (fallback str(nmid) when no card_name in state)
    assert added.name == "100 100"
    assert added.nmids == [100]
    mock_session.commit.assert_called_once()
    bot.send_message.assert_called_once()
    assert "Кампании подключены" in bot.send_message.call_args[0][1]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_existing_create_both_cancel() -> None:
    """create_both: action cancel -> state.clear, 'Отменено'."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(return_value={})
    state.clear = AsyncMock()
    callback = _make_callback(
        callbacks.ConnectExistingCreateBoth(action="cancel"), chat_id=333
    )
    callback_data = callbacks.ConnectExistingCreateBoth(action="cancel")

    await connect_existing_advs.connect_existing_create_both(
        callback, callback_data, bot, state
    )

    state.clear.assert_called_once()
    bot.send_message.assert_called_once_with(333, "Отменено.")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_existing_create_both_confirm_missing_data() -> None:
    """create_both: confirm but no nmid/shop_id -> 'Данные сессии потеряны'."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(return_value={})
    state.clear = AsyncMock()
    callback = _make_callback(
        callbacks.ConnectExistingCreateBoth(action="confirm"), chat_id=333
    )
    callback_data = callbacks.ConnectExistingCreateBoth(action="confirm")

    await connect_existing_advs.connect_existing_create_both(
        callback, callback_data, bot, state
    )

    bot.send_message.assert_called_once()
    assert "Данные сессии потеряны" in bot.send_message.call_args[0][1]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_existing_create_both_confirm_enqueue() -> None:
    """create_both: confirm with data -> enqueue_job, state.clear, success message."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(
        return_value={"nmid": 100, "shop_id": "shop_1"}
    )
    state.clear = AsyncMock()
    callback = _make_callback(
        callbacks.ConnectExistingCreateBoth(action="confirm"),
        chat_id=333,
        from_user_id=999,
    )
    callback_data = callbacks.ConnectExistingCreateBoth(action="confirm")
    mock_pool = MagicMock()
    mock_pool.enqueue_job = AsyncMock()

    with patch("arq.create_pool", AsyncMock(return_value=mock_pool)), patch(
        "app.arq_workers.arq_redis_settings.arq_redis_settings",
    ):
        await connect_existing_advs.connect_existing_create_both(
            callback, callback_data, bot, state
        )

    mock_pool.enqueue_job.assert_called_once_with(
        "create_complex_advs", 100, "shop_1", False, 999
    )
    state.clear.assert_called_once()
    bot.send_message.assert_called_once()
    assert "добавлена в очередь" in bot.send_message.call_args[0][1]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_existing_advs_back_to_shop() -> None:
    """back_to_shop: state.clear, ShopMenu called with correct args."""
    bot = MagicMock()
    state = MagicMock()
    state.clear = AsyncMock()
    callback = _make_callback(
        callbacks.ConnectExistingAdvsBackToShop(wb_user_cabinet_original_id=7),
        chat_id=444,
    )
    callback_data = callbacks.ConnectExistingAdvsBackToShop(
        wb_user_cabinet_original_id=7
    )
    mock_shop_menu = MagicMock()
    mock_shop_menu.return_value = AsyncMock()
    with patch(f"{MODULE}.ShopMenu", mock_shop_menu):
        await connect_existing_advs.connect_existing_advs_back_to_shop(
            callback, callback_data, bot, state
        )

    state.clear.assert_called_once()
    mock_shop_menu.assert_called_once_with(bot, 444, state, 7)
    mock_shop_menu.return_value.assert_called_once()
