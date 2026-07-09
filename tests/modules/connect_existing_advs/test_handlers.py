"""Unit tests for connect_existing_advs handlers."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import CallbackQuery, Chat, Message, User

from app.client_bot.user_interface.states import ConnectExistingAdvsStates
from app.client_bot.user_interface.views import callbacks
from app.core.mp.wb.api.domain_managers import ProductCardInfo
from app.modules.connect_existing_advs.candidates_service import (
    ConnectExistingCandidatesResult,
)
from app.client_bot.user_interface.handlers import connect_existing_advs

MODULE = "app.client_bot.user_interface.handlers.connect_existing_advs"


def _make_hub_with_products_manager(
    get_card_by_nmid_result: ProductCardInfo | Exception,
) -> MagicMock:
    """Create mock hub chain: container -> factory -> hub -> products_manager."""
    products_manager = MagicMock()
    if isinstance(get_card_by_nmid_result, Exception):
        products_manager.get_card_by_nmid = AsyncMock(
            side_effect=get_card_by_nmid_result
        )
    else:
        products_manager.get_card_by_nmid = AsyncMock(
            return_value=get_card_by_nmid_result
        )
    hub = MagicMock()
    hub.wb_data_manager.products_manager = products_manager
    factory = MagicMock()
    factory.get_wb_manager_hub.return_value = hub
    container = MagicMock()
    container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory.return_value = factory
    return container


def _make_callback(
    callback_data: callbacks.ConnectExistingAdvs
    | callbacks.ConnectExistingConfirmType1
    | callbacks.ConnectExistingConfirmType2
    | callbacks.ConnectExistingCreateBoth
    | callbacks.ConnectExistingContinueDespiteInvalid
    | callbacks.ConnectExistingAdvsBackToShop
    | callbacks.ConnectExistingChangeNmid,
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
    bot.send_message.assert_called_once_with(
        111, "Введите артикул WB товара — одно число, больше 0:"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_existing_advs_nmid_text_none() -> None:
    """nmid handler: message.text None -> send 'Отправьте Артикул WB товара числом.'."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(return_value={"wb_user_cabinet_original_id": 1})
    message = _make_message(chat_id=222, text=None)

    await connect_existing_advs.connect_existing_advs_nmid(message, bot, state)

    bot.send_message.assert_called_once_with(
        222, "Отправьте Артикул WB товара числом."
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_existing_advs_nmid_not_int() -> None:
    """nmid handler: non-int text -> 'Артикул WB товара должен быть целым числом'."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(return_value={"wb_user_cabinet_original_id": 1})
    message = _make_message(chat_id=222, text="abc")

    await connect_existing_advs.connect_existing_advs_nmid(message, bot, state)

    bot.send_message.assert_called_once_with(
        222, "Артикул WB товара должен быть целым числом."
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_existing_advs_nmid_zero() -> None:
    """nmid handler: 0 -> 'Артикул WB товара должен быть больше 0'."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(return_value={"wb_user_cabinet_original_id": 1})
    message = _make_message(chat_id=222, text="0")

    await connect_existing_advs.connect_existing_advs_nmid(message, bot, state)

    bot.send_message.assert_called_once_with(
        222, "Артикул WB товара  должен быть больше 0."
    )


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
            message, bot, state
        )

    bot.send_message.assert_called_once_with(222, "Кабинет не найден.")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_existing_advs_nmid_card_not_found() -> None:
    """nmid handler: CardNotFoundInWB -> message containing 'артикул не найден', keyboard with retry/shop."""
    from app.core.wb_api.mixins.excs import CardNotFoundInWB

    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(return_value={"wb_user_cabinet_original_id": 1})
    state.update_data = AsyncMock()
    message = _make_message(chat_id=222, text="12345")
    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.one_or_none.return_value = (1, "shop_1")
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_sm = MagicMock()
    mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_sm.return_value.__aexit__ = AsyncMock(return_value=None)

    container = _make_hub_with_products_manager(CardNotFoundInWB())

    class _AwaitableCtx:
        """Awaitable that returns self; async ctx yields _container for 'async with ... as container'."""

        def __init__(self, _container: MagicMock) -> None:
            self._container = _container

        def __await__(self):
            return (yield self)

        async def __aenter__(self):
            return self._container

        async def __aexit__(self, *args):
            return None

    mock_di_create = AsyncMock(return_value=_AwaitableCtx(container))

    with patch(f"{MODULE}.sm", mock_sm), patch(
        f"{MODULE}.DIManager.create", mock_di_create
    ):
        await connect_existing_advs.connect_existing_advs_nmid(
            message, bot, state
        )

    assert bot.send_message.call_count == 2  # WB_WAIT_MESSAGE, then error
    last_message = bot.send_message.call_args[0][1]
    assert "артикул не найден" in last_message.lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_existing_advs_nmid_existing_pair() -> None:
    """nmid handler: both IDs set -> rebind, shop, change nmid keyboard."""
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

    container = _make_hub_with_products_manager(
        ProductCardInfo(name="Card Name", nmid=100)
    )
    mock_di_create = AsyncMock()
    mock_acm = MagicMock()
    mock_acm.__aenter__ = AsyncMock(return_value=container)
    mock_acm.__aexit__ = AsyncMock(return_value=None)
    mock_di_create.return_value = mock_acm

    with patch(f"{MODULE}.sm", mock_sm), patch(
        f"{MODULE}.DIManager.create", mock_di_create
    ), patch(
        f"{MODULE}._get_existing_adv_row_for_connect_not_done",
        AsyncMock(return_value=(77, 100, 200)),
    ):
        await connect_existing_advs.connect_existing_advs_nmid(
            message, bot, state
        )

    state.clear.assert_called_once()
    assert bot.send_message.call_count == 2  # WB_WAIT_MESSAGE, then "уже есть подключённые"
    assert "уже есть подключённые" in bot.send_message.call_args[0][1]
    reply_markup = bot.send_message.call_args[1]["reply_markup"]
    rows = reply_markup.inline_keyboard
    assert len(rows) == 2
    row0, row1 = rows
    assert len(row0) == 2
    assert row0[0].text == "Перепривязать кампании WB"
    cb = callbacks.RebindAdvCampaignIds.unpack(row0[0].callback_data)
    assert cb is not None
    assert cb.adv_setting_original_id == 77
    assert row0[1].text == "В меню магазина"
    assert callbacks.ConnectExistingAdvsBackToShop.unpack(row0[1].callback_data) is not None
    assert len(row1) == 1
    assert row1[0].text == "Ввести другой артикул"
    cn = callbacks.ConnectExistingChangeNmid.unpack(row1[0].callback_data)
    assert cn is not None
    assert cn.wb_user_cabinet_original_id == 5


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

    container = _make_hub_with_products_manager(
        ProductCardInfo(name="Card Name", nmid=100)
    )
    mock_di_create = AsyncMock()
    mock_acm = MagicMock()
    mock_acm.__aenter__ = AsyncMock(return_value=container)
    mock_acm.__aexit__ = AsyncMock(return_value=None)
    mock_di_create.return_value = mock_acm

    with patch(f"{MODULE}.sm", mock_sm), patch(
        f"{MODULE}.DIManager.create", mock_di_create
    ), patch(
        f"{MODULE}._get_existing_adv_row_for_connect_not_done",
        AsyncMock(return_value=None),
    ), patch(
        f"{MODULE}.get_connect_existing_candidates",
        AsyncMock(return_value=empty_result),
    ):
        await connect_existing_advs.connect_existing_advs_nmid(
            message, bot, state
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
    from app.core.mp.wb.api.excs import ApiForbiddenError

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

    container = _make_hub_with_products_manager(
        ProductCardInfo(name="Card Name", nmid=100)
    )
    mock_di_create = AsyncMock()
    mock_acm = MagicMock()
    mock_acm.__aenter__ = AsyncMock(return_value=container)
    mock_acm.__aexit__ = AsyncMock(return_value=None)
    mock_di_create.return_value = mock_acm

    with patch(f"{MODULE}.sm", mock_sm), patch(
        f"{MODULE}.DIManager.create", mock_di_create
    ), patch(
        f"{MODULE}._get_existing_adv_row_for_connect_not_done",
        AsyncMock(return_value=None),
    ), patch(
        f"{MODULE}.get_connect_existing_candidates",
        AsyncMock(side_effect=ApiForbiddenError("forbidden")),
    ):
        await connect_existing_advs.connect_existing_advs_nmid(
            message, bot, state
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

    container = _make_hub_with_products_manager(
        ProductCardInfo(name="Card Name", nmid=100)
    )
    mock_di_create = AsyncMock()
    mock_acm = MagicMock()
    mock_acm.__aenter__ = AsyncMock(return_value=container)
    mock_acm.__aexit__ = AsyncMock(return_value=None)
    mock_di_create.return_value = mock_acm

    with patch(f"{MODULE}.sm", mock_sm), patch(
        f"{MODULE}.DIManager.create", mock_di_create
    ), patch(
        f"{MODULE}._get_existing_adv_row_for_connect_not_done",
        AsyncMock(return_value=None),
    ), patch(
        f"{MODULE}.get_connect_existing_candidates",
        AsyncMock(side_effect=BadRequestError("path not found")),
    ):
        await connect_existing_advs.connect_existing_advs_nmid(
            message, bot, state
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

    container = _make_hub_with_products_manager(
        ProductCardInfo(name="Card Name", nmid=100)
    )
    mock_di_create = AsyncMock()
    mock_acm = MagicMock()
    mock_acm.__aenter__ = AsyncMock(return_value=container)
    mock_acm.__aexit__ = AsyncMock(return_value=None)
    mock_di_create.return_value = mock_acm

    with patch(f"{MODULE}.sm", mock_sm), patch(
        f"{MODULE}.DIManager.create", mock_di_create
    ), patch(
        f"{MODULE}._get_existing_adv_row_for_connect_not_done",
        AsyncMock(return_value=None),
    ), patch(
        f"{MODULE}.get_connect_existing_candidates",
        AsyncMock(return_value=result_with_auction),
    ):
        await connect_existing_advs.connect_existing_advs_nmid(
            message, bot, state
        )

    state.set_state.assert_called_once_with(ConnectExistingAdvsStates.confirm_type1)
    assert bot.send_message.call_count == 2  # WB_WAIT_MESSAGE, then auction choice menu
    assert "Как подключить поисковую" in bot.send_message.call_args[0][1]
    assert "аукцион" in bot.send_message.call_args[0][1]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_existing_advs_nmid_success_auto_only() -> None:
    """nmid handler: only auto candidates -> waiting_confirm_continue_invalid, text and buttons."""
    from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models import (
        GetAdvertsAdvertsItem,
    )

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

    mock_auto = MagicMock(spec=GetAdvertsAdvertsItem)
    mock_auto.id = 55
    mock_auto.settings.name = "AutoCampaign"
    mock_auto.status.value = 9
    result_only_auto = ConnectExistingCandidatesResult(
        auction_candidates=[],
        auto_candidates=[mock_auto],
    )

    container = _make_hub_with_products_manager(
        ProductCardInfo(name="Card Name", nmid=100)
    )
    mock_di_create = AsyncMock()
    mock_acm = MagicMock()
    mock_acm.__aenter__ = AsyncMock(return_value=container)
    mock_acm.__aexit__ = AsyncMock(return_value=None)
    mock_di_create.return_value = mock_acm

    with patch(f"{MODULE}.sm", mock_sm), patch(
        f"{MODULE}.DIManager.create", mock_di_create
    ), patch(
        f"{MODULE}._get_existing_adv_row_for_connect_not_done",
        AsyncMock(return_value=None),
    ), patch(
        f"{MODULE}.get_connect_existing_candidates",
        AsyncMock(return_value=result_only_auto),
    ):
        await connect_existing_advs.connect_existing_advs_nmid(
            message, bot, state
        )

    state.set_state.assert_called_once_with(
        ConnectExistingAdvsStates.waiting_confirm_continue_invalid
    )
    assert bot.send_message.call_count == 2  # WB_WAIT_MESSAGE, then continue invalid
    text = bot.send_message.call_args[0][1]
    assert "авто-кампании без поисковой" in text
    assert "Создать поисковую РК" in text
    reply_markup = bot.send_message.call_args[1]["reply_markup"]
    buttons_texts = [
        btn.text
        for row in reply_markup.inline_keyboard
        for btn in row
    ]
    assert "Создать поисковую РК" in buttons_texts
    assert "Отмена" in buttons_texts


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_existing_advs_nmid_existing_auction_id_in_state() -> None:
    """nmid: existing row (None, None, 123) + both candidates -> confirm_type2, 'Аукционная РК уже подключена'."""
    from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models import (
        GetAdvertsAdvertsItem,
    )

    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()
    state_data = {
        "wb_user_cabinet_original_id": 1,
        "existing_auction_id": 123,
        "auto_candidates": [{"id": 456, "name": "AutoCamp"}],
    }
    state.get_data = AsyncMock(return_value=state_data)
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

    mock_auction = MagicMock(spec=GetAdvertsAdvertsItem)
    mock_auction.id = 42
    mock_auction.settings.name = "AuctionCamp"
    mock_auction.status.value = 9
    mock_auto = MagicMock(spec=GetAdvertsAdvertsItem)
    mock_auto.id = 456
    mock_auto.settings.name = "AutoCamp"
    mock_auto.status.value = 9
    result_both = ConnectExistingCandidatesResult(
        auction_candidates=[mock_auction],
        auto_candidates=[mock_auto],
    )

    container = _make_hub_with_products_manager(
        ProductCardInfo(name="Card Name", nmid=100)
    )
    mock_di_create = AsyncMock()
    mock_acm = MagicMock()
    mock_acm.__aenter__ = AsyncMock(return_value=container)
    mock_acm.__aexit__ = AsyncMock(return_value=None)
    mock_di_create.return_value = mock_acm

    with patch(f"{MODULE}.sm", mock_sm), patch(
        f"{MODULE}.DIManager.create", mock_di_create
    ), patch(
        f"{MODULE}._get_existing_adv_row_for_connect_not_done",
        AsyncMock(return_value=(None, None, 123)),
    ), patch(
        f"{MODULE}.get_connect_existing_candidates",
        AsyncMock(return_value=result_both),
    ):
        await connect_existing_advs.connect_existing_advs_nmid(
            message, bot, state
        )

    state.update_data.assert_any_call(chosen_auction_adv_id=123)
    state.set_state.assert_called_once_with(ConnectExistingAdvsStates.confirm_type2)
    assert bot.send_message.call_count == 2  # WB_WAIT_MESSAGE, then auto choice menu
    text = bot.send_message.call_args[0][1]
    assert "авто-кампанию" in text or "авто" in text
    reply_markup = bot.send_message.call_args[1]["reply_markup"]
    buttons_texts = [
        btn.text for row in reply_markup.inline_keyboard for btn in row
    ]
    assert "Создать РК" in buttons_texts
    assert "Ввести ID кампании" in buttons_texts


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

    assert bot.send_message.call_count == 2  # message + auction choice menu
    assert "Создание аукционной РК будет доступно" in bot.send_message.call_args_list[0][0][1]
    assert "Как подключить поисковую" in bot.send_message.call_args_list[1][0][1]
    state.set_state.assert_called_with(ConnectExistingAdvsStates.confirm_type1)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_existing_confirm_type1_adv_id_set() -> None:
    """confirm_type1: adv_id=123 -> state confirm_type2, show auto choice menu."""
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
    assert "Как подключить авто-кампанию" in bot.send_message.call_args[0][1]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_existing_confirm_type2_adv_id_zero_chosen_auction_none() -> None:
    """confirm_type2: adv_id=0 with chosen_auction None -> 'Сначала выберите аукционную'."""
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
    assert "Сначала выберите аукционную" in bot.send_message.call_args[0][1]


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
    """confirm_type2: full flow -> upsert by adv_id, commit, message."""
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
    mock_wb_cabinet.id = 1
    mock_session = MagicMock()
    mock_session.get = AsyncMock(return_value=mock_wb_cabinet)
    main_adv = MagicMock()
    mock_main_adv_result = MagicMock()
    mock_main_adv_result.scalar_one.return_value = main_adv
    mock_session.execute = AsyncMock(side_effect=[None, mock_main_adv_result])
    mock_session.commit = AsyncMock()
    mock_sm = MagicMock()
    mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_sm.return_value.__aexit__ = AsyncMock(return_value=None)

    with patch(f"{MODULE}.sm", mock_sm), patch(
        "app.modules.adv_creator.backend.main_manager.MainAdvManager._apply_default_settings_to_adv",
        new_callable=AsyncMock,
    ), patch(
        f"{MODULE}.ensure_search_adv_setting_for_main_adv",
        new_callable=AsyncMock,
    ):
        await connect_existing_advs.connect_existing_confirm_type2(
            callback, callback_data, bot, state
        )

    state.clear.assert_called_once()
    assert mock_session.execute.await_count == 2
    mock_session.commit.assert_called_once()
    bot.send_message.assert_called_once()
    assert "Кампании подключены" in bot.send_message.call_args[0][1]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_existing_confirm_type2_cabinet_not_found() -> None:
    """confirm_type2: session.get(WBCabinet, wb_cabinet_id) is None -> 'Кабинет не найден.', no commit."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(
        return_value={
            "nmid": 100,
            "wb_cabinet_id": 1,
            "shop_id": None,
            "card_name": "Card",
            "chosen_auction_adv_id": 10,
            "auction_candidates": [],
            "auto_candidates": [],
        }
    )
    state.clear = AsyncMock()
    callback = _make_callback(
        callbacks.ConnectExistingConfirmType2(adv_id=20), chat_id=333
    )
    callback_data = callbacks.ConnectExistingConfirmType2(adv_id=20)
    mock_session = MagicMock()
    mock_session.get = AsyncMock(return_value=None)
    mock_session.commit = AsyncMock()
    mock_sm = MagicMock()
    mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_sm.return_value.__aexit__ = AsyncMock(return_value=None)

    with patch(f"{MODULE}.sm", mock_sm):
        await connect_existing_advs.connect_existing_confirm_type2(
            callback, callback_data, bot, state
        )

    bot.send_message.assert_called_once_with(333, "Кабинет не найден.")
    mock_session.commit.assert_not_called()
    state.clear.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_existing_confirm_type2_rename_exception_still_upserts() -> None:
    """confirm_type2: rename_campaign raises -> message about rename, upsert and commit still run."""
    from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet

    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()
    # Names differ from get_name_for_adv(100, "Card", ...) so need_rename is True
    state.get_data = AsyncMock(
        return_value={
            "nmid": 100,
            "wb_cabinet_id": 1,
            "shop_id": "shop_1",
            "card_name": "Card",
            "chosen_auction_adv_id": 10,
            "chosen_auto_adv_id": 20,
            "auction_candidates": [{"id": 10, "name": "OldAuctionName"}],
            "auto_candidates": [{"id": 20, "name": "OldAutoName"}],
        }
    )
    state.clear = AsyncMock()
    callback = _make_callback(
        callbacks.ConnectExistingConfirmType2(adv_id=20), chat_id=333
    )
    callback_data = callbacks.ConnectExistingConfirmType2(adv_id=20)
    mock_wb_cabinet = MagicMock(spec=WBCabinet)
    mock_wb_cabinet.id = 1
    mock_session = MagicMock()
    mock_session.get = AsyncMock(return_value=mock_wb_cabinet)
    main_adv = MagicMock()
    mock_main_adv_result = MagicMock()
    mock_main_adv_result.scalar_one.return_value = main_adv
    mock_session.execute = AsyncMock(side_effect=[None, mock_main_adv_result])
    mock_session.commit = AsyncMock()
    mock_sm = MagicMock()
    mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_sm.return_value.__aexit__ = AsyncMock(return_value=None)
    mock_pm = MagicMock()
    mock_pm.rename_campaign = AsyncMock(side_effect=Exception("rename failed"))
    mock_hub = MagicMock()
    mock_hub.wb_data_manager.promotion_manager = mock_pm
    mock_factory = MagicMock()
    mock_factory.get_wb_manager_hub.return_value = mock_hub
    mock_container = MagicMock()
    mock_container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory.return_value = mock_factory
    mock_acm = MagicMock()
    mock_acm.__aenter__ = AsyncMock(return_value=mock_container)
    mock_acm.__aexit__ = AsyncMock(return_value=None)
    mock_di_create = AsyncMock(return_value=mock_acm)

    with patch(f"{MODULE}.sm", mock_sm), patch(
        f"{MODULE}.DIManager.create", mock_di_create
    ), patch(
        "app.modules.adv_creator.backend.main_manager.MainAdvManager._apply_default_settings_to_adv",
        new_callable=AsyncMock,
    ), patch(
        f"{MODULE}.ensure_search_adv_setting_for_main_adv",
        new_callable=AsyncMock,
    ):
        await connect_existing_advs.connect_existing_confirm_type2(
            callback, callback_data, bot, state
        )

    rename_msg = next(
        (c[0][1] for c in bot.send_message.call_args_list if "переименование" in c[0][1]),
        None,
    )
    assert rename_msg is not None
    assert "переименование на WB не удалось" in rename_msg
    assert mock_session.execute.await_count == 2
    mock_session.commit.assert_called_once()
    state.clear.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_existing_create_both_cancel() -> None:
    """create_both: action cancel (no cabinet in data) -> state.clear, 'Отменено'."""
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
async def test_connect_existing_create_both_cancel_with_cabinet() -> None:
    """create_both: cancel with wb_user_cabinet_original_id in data -> state.clear, ShopMenu, no 'Отменено'."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(return_value={"wb_user_cabinet_original_id": 7})
    state.clear = AsyncMock()
    callback = _make_callback(
        callbacks.ConnectExistingCreateBoth(action="cancel"), chat_id=333
    )
    callback_data = callbacks.ConnectExistingCreateBoth(action="cancel")
    mock_shop_menu = MagicMock()
    mock_shop_menu.return_value = AsyncMock()

    with patch(f"{MODULE}.ShopMenu", mock_shop_menu):
        await connect_existing_advs.connect_existing_create_both(
            callback, callback_data, bot, state
        )

    state.clear.assert_called_once()
    mock_shop_menu.assert_called_once_with(bot, 333, state, 7)
    mock_shop_menu.return_value.assert_called_once()
    send_calls = [c[0][1] for c in bot.send_message.call_args_list]
    assert "Отменено" not in send_calls


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
async def test_connect_existing_continue_despite_invalid_confirm_enqueue() -> None:
    """continue_despite_invalid: confirm enqueues create_search_only with existing_auto_adv_id."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(
        return_value={
            "nmid": 100,
            "shop_id": "shop_1",
            "auto_candidates": [{"id": 5001, "name": "Auto campaign"}],
        }
    )
    state.clear = AsyncMock()
    callback = _make_callback(
        callbacks.ConnectExistingContinueDespiteInvalid(action="confirm"),
        chat_id=333,
        from_user_id=999,
    )
    callback_data = callbacks.ConnectExistingContinueDespiteInvalid(action="confirm")
    mock_pool = MagicMock()
    mock_pool.enqueue_job = AsyncMock()

    with patch("arq.create_pool", AsyncMock(return_value=mock_pool)), patch(
        "app.arq_workers.arq_redis_settings.arq_redis_settings",
    ):
        await connect_existing_advs.connect_existing_continue_despite_invalid(
            callback, callback_data, bot, state
        )

    mock_pool.enqueue_job.assert_called_once_with(
        "create_search_only", 100, "shop_1", 5001, 999
    )
    state.clear.assert_called_once()
    bot.send_message.assert_called_once()
    assert "добавлена в очередь" in bot.send_message.call_args[0][1]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_existing_continue_despite_invalid_cancel_with_cabinet() -> None:
    """continue_despite_invalid: cancel with wb_user_cabinet_original_id -> state.clear, ShopMenu, no 'Отменено'."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(return_value={"wb_user_cabinet_original_id": 7})
    state.clear = AsyncMock()
    callback = _make_callback(
        callbacks.ConnectExistingContinueDespiteInvalid(action="cancel"),
        chat_id=333,
    )
    callback_data = callbacks.ConnectExistingContinueDespiteInvalid(action="cancel")
    mock_shop_menu = MagicMock()
    mock_shop_menu.return_value = AsyncMock()

    with patch(f"{MODULE}.ShopMenu", mock_shop_menu):
        await connect_existing_advs.connect_existing_continue_despite_invalid(
            callback, callback_data, bot, state
        )

    state.clear.assert_called_once()
    mock_shop_menu.assert_called_once_with(bot, 333, state, 7)
    mock_shop_menu.return_value.assert_called_once()
    send_calls = [c[0][1] for c in bot.send_message.call_args_list]
    assert "Отменено" not in send_calls


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_existing_continue_despite_invalid_confirm_empty_auto_candidates() -> None:
    """continue_despite_invalid: confirm with empty auto_candidates -> message, no enqueue."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(
        return_value={"nmid": 100, "shop_id": "shop_1", "auto_candidates": []}
    )
    state.clear = AsyncMock()
    callback = _make_callback(
        callbacks.ConnectExistingContinueDespiteInvalid(action="confirm"),
        chat_id=333,
    )
    callback_data = callbacks.ConnectExistingContinueDespiteInvalid(action="confirm")

    with patch("arq.create_pool", AsyncMock()) as mock_create_pool:
        await connect_existing_advs.connect_existing_continue_despite_invalid(
            callback, callback_data, bot, state
        )

    bot.send_message.assert_called_once_with(333, "Нет данных об авто-кампании.")
    mock_create_pool.assert_not_called()
    state.clear.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_existing_confirm_type2_adv_id_zero_enqueues_create_auto_only() -> None:
    """confirm_type2 with adv_id=0: enqueue create_auto_only, state.clear, queue message; ShopMenu not shown."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(
        return_value={
            "nmid": 200,
            "shop_id": "shop_2",
            "chosen_auction_adv_id": 7001,
            "wb_user_cabinet_original_id": 42,
        }
    )
    state.clear = AsyncMock()
    callback = _make_callback(
        callbacks.ConnectExistingConfirmType2(adv_id=0),
        chat_id=333,
        from_user_id=999,
    )
    callback_data = callbacks.ConnectExistingConfirmType2(adv_id=0)
    mock_pool = MagicMock()
    mock_pool.enqueue_job = AsyncMock()
    mock_shop_menu = MagicMock()
    mock_shop_menu.return_value = AsyncMock()

    with patch("arq.create_pool", AsyncMock(return_value=mock_pool)), patch(
        "app.arq_workers.arq_redis_settings.arq_redis_settings",
    ), patch(f"{MODULE}.ShopMenu", mock_shop_menu):
        await connect_existing_advs.connect_existing_confirm_type2(
            callback, callback_data, bot, state
        )

    mock_pool.enqueue_job.assert_called_once_with(
        "create_auto_only", 200, "shop_2", 7001, 999
    )
    state.clear.assert_called_once()
    bot.send_message.assert_called_once()
    assert "добавлена в очередь" in bot.send_message.call_args[0][1]
    mock_shop_menu.assert_not_called()


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


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_existing_change_nmid() -> None:
    """change_nmid: clear, set waiting_nmid, prompt for new nmid."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock()
    state.clear = AsyncMock()
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    callback = _make_callback(
        callbacks.ConnectExistingChangeNmid(wb_user_cabinet_original_id=7),
        chat_id=444,
    )
    callback_data = callbacks.ConnectExistingChangeNmid(
        wb_user_cabinet_original_id=7
    )

    await connect_existing_advs.connect_existing_change_nmid(
        callback, callback_data, bot, state
    )

    state.clear.assert_called_once()
    state.update_data.assert_called_once_with(wb_user_cabinet_original_id=7)
    state.set_state.assert_called_once_with(ConnectExistingAdvsStates.waiting_nmid)
    bot.send_message.assert_called_once()
    assert "артикул" in bot.send_message.call_args[0][1]
