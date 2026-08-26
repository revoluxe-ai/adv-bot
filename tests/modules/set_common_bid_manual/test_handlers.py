"""Unit tests for set_common_bid_manual handlers."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import CallbackQuery, Chat, Message, User
from aiogram.fsm.context import FSMContext

from app.client_bot.user_interface.states import SetCommonBidManual
from app.client_bot.user_interface.views import callbacks
from app.client_bot.user_interface.handlers import set_common_bid_manual

MODULE = "app.client_bot.user_interface.handlers.set_common_bid_manual"


def _make_callback(
    callback_data: callbacks.SetCommonBidManual,
    chat_id: int = 12345,
    from_user_id: int = 67890,
) -> CallbackQuery:
    """Create mock CallbackQuery."""
    cb = MagicMock(spec=CallbackQuery)
    cb.message = MagicMock()
    cb.message.chat = MagicMock(spec=Chat)
    cb.message.chat.id = chat_id
    cb.from_user = MagicMock(spec=User)
    cb.from_user.id = from_user_id
    cb.answer = AsyncMock()
    return cb


def _make_message(
    chat_id: int = 12345,
    text: str | None = "100",
    from_user_id: int = 67890,
) -> Message:
    """Create mock Message."""
    msg = MagicMock(spec=Message)
    msg.chat = MagicMock(spec=Chat)
    msg.chat.id = chat_id
    msg.text = text
    msg.from_user = MagicMock(spec=User)
    msg.from_user.id = from_user_id
    msg.answer = AsyncMock()
    return msg


def _make_adv_setting(
    adv_setting_id: int = 1,
    search_adv_id: int | None = 999,
    shop_id: str = "shop123",
    nmids: list[int] | None = None,
    adv_id: int = 100,
) -> MagicMock:
    """Create mock AdvSetting."""
    adv = MagicMock()
    adv.id = adv_setting_id
    adv.search_adv_id = search_adv_id
    adv.wb_cabinet = MagicMock()
    adv.wb_cabinet.shop_id = shop_id
    adv.nmids = nmids or [12345, 67890]
    adv.adv_id = adv_id
    adv.plan_for_sales_for_day = None
    adv.target_price_for_order = None
    adv.max_price_for_order = None
    adv.wb_bid_type = None
    adv.wb_placement_search = None
    adv.wb_placement_recommendations = None
    return adv


def _make_wb_user_cabinet(cabinet_id: int = 10) -> MagicMock:
    """Create mock WBUserCabinet."""
    cabinet = MagicMock()
    cabinet.id = cabinet_id
    return cabinet


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_common_bid_manual_start_success() -> None:
    """Test successful start: get min bids, save to state, set waiting state."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock(spec=FSMContext)
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()

    adv_setting = _make_adv_setting(adv_setting_id=1, search_adv_id=999)
    search_adv_setting = _make_adv_setting(adv_setting_id=999, adv_id=999)

    callback_data = callbacks.SetCommonBidManual(
        adv_setting_original_id=1,
        wb_user_cabinet_original_id=10,
    )
    callback = _make_callback(callback_data, chat_id=111)

    min_bids_mock = MagicMock()
    min_bids_mock.search = {12345: 50, 67890: 75}

    with patch(f"{MODULE}.sm") as mock_sm:
        session_mock = MagicMock()
        session_mock.__aenter__ = AsyncMock(return_value=session_mock)
        session_mock.__aexit__ = AsyncMock(return_value=None)
        mock_sm.return_value = session_mock

        # First query for adv_setting
        result_mock_1 = MagicMock()
        result_mock_1.scalar_one_or_none.return_value = adv_setting
        # Second query for search_adv_setting
        result_mock_2 = MagicMock()
        result_mock_2.scalar_one_or_none.return_value = search_adv_setting

        session_mock.execute = AsyncMock(side_effect=[result_mock_1, result_mock_2])

        with patch(f"{MODULE}.DIManager.create") as mock_di:
            container = MagicMock()
            factory = MagicMock()
            hub = MagicMock()
            hub.wb_manager.get_min_bids_cache_only = AsyncMock(
                return_value=min_bids_mock
            )

            factory.get_wb_manager_hub.return_value = hub
            container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory.return_value = factory

            mock_di.return_value.__aenter__ = AsyncMock(return_value=container)
            mock_di.return_value.__aexit__ = AsyncMock(return_value=None)

            await set_common_bid_manual.set_common_bid_manual_start(
                callback, callback_data, bot, state
            )

    # Verify state updates
    state.update_data.assert_called_once_with(
        adv_setting_original_id=1,
        wb_user_cabinet_original_id=10,
        min_bid_search=75,  # max of [50, 75]
    )
    state.set_state.assert_called_once_with(SetCommonBidManual.waiting_for_bid)

    # Verify message sent
    bot.send_message.assert_called_once()
    call_args = bot.send_message.call_args
    assert call_args[0][0] == 111
    assert "75 р." in call_args[0][1]
    assert "Минимальная ставка для аукциона" in call_args[0][1]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_common_bid_manual_start_empty_search_min_bids() -> None:
    """Test start when cache response has no search bids."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock(spec=FSMContext)
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()

    adv_setting = _make_adv_setting(adv_setting_id=1, search_adv_id=999)
    search_adv_setting = _make_adv_setting(adv_setting_id=999, adv_id=999)

    callback_data = callbacks.SetCommonBidManual(
        adv_setting_original_id=1,
        wb_user_cabinet_original_id=10,
    )
    callback = _make_callback(callback_data, chat_id=111)

    min_bids_mock = MagicMock()
    min_bids_mock.search = {}

    with patch(f"{MODULE}.sm") as mock_sm:
        session_mock = MagicMock()
        session_mock.__aenter__ = AsyncMock(return_value=session_mock)
        session_mock.__aexit__ = AsyncMock(return_value=None)
        mock_sm.return_value = session_mock

        result_mock_1 = MagicMock()
        result_mock_1.scalar_one_or_none.return_value = adv_setting
        result_mock_2 = MagicMock()
        result_mock_2.scalar_one_or_none.return_value = search_adv_setting
        session_mock.execute = AsyncMock(side_effect=[result_mock_1, result_mock_2])

        with patch(f"{MODULE}.DIManager.create") as mock_di:
            container = MagicMock()
            factory = MagicMock()
            hub = MagicMock()
            hub.wb_manager.get_min_bids_cache_only = AsyncMock(
                return_value=min_bids_mock
            )

            factory.get_wb_manager_hub.return_value = hub
            container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory.return_value = factory

            mock_di.return_value.__aenter__ = AsyncMock(return_value=container)
            mock_di.return_value.__aexit__ = AsyncMock(return_value=None)

            await set_common_bid_manual.set_common_bid_manual_start(
                callback, callback_data, bot, state
            )

    state.update_data.assert_not_called()
    state.set_state.assert_not_called()
    bot.send_message.assert_called_once_with(
        111,
        "Нет минимальных ставок в кеше для аукциона. Дождитесь обновления кеша.",
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_common_bid_manual_start_no_search_adv() -> None:
    """Test start when campaign has no search_adv_id."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock(spec=FSMContext)

    adv_setting = _make_adv_setting(adv_setting_id=1, search_adv_id=None)

    callback_data = callbacks.SetCommonBidManual(
        adv_setting_original_id=1,
        wb_user_cabinet_original_id=10,
    )
    callback = _make_callback(callback_data, chat_id=111)

    with patch(f"{MODULE}.sm") as mock_sm:
        session_mock = MagicMock()
        session_mock.__aenter__ = AsyncMock(return_value=session_mock)
        session_mock.__aexit__ = AsyncMock(return_value=None)
        mock_sm.return_value = session_mock

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = adv_setting
        session_mock.execute = AsyncMock(return_value=result_mock)

        await set_common_bid_manual.set_common_bid_manual_start(
            callback, callback_data, bot, state
        )

    # Verify error message
    bot.send_message.assert_called_once_with(
        111,
        "У этой кампании нет поисковой (аукционной) РК.",
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_common_bid_manual_start_blocks_non_search_campaign() -> None:
    """Known non-search campaign meta should block the manual search bid tool."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock(spec=FSMContext)
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()

    adv_setting = _make_adv_setting(adv_setting_id=1, search_adv_id=999)
    search_adv_setting = _make_adv_setting(adv_setting_id=999, adv_id=999)
    search_adv_setting.wb_bid_type = "manual"
    search_adv_setting.wb_placement_search = False
    search_adv_setting.wb_placement_recommendations = True

    callback_data = callbacks.SetCommonBidManual(
        adv_setting_original_id=1,
        wb_user_cabinet_original_id=10,
    )
    callback = _make_callback(callback_data, chat_id=111)

    with patch(f"{MODULE}.sm") as mock_sm:
        session_mock = MagicMock()
        session_mock.__aenter__ = AsyncMock(return_value=session_mock)
        session_mock.__aexit__ = AsyncMock(return_value=None)
        mock_sm.return_value = session_mock

        result_mock_1 = MagicMock()
        result_mock_1.scalar_one_or_none.return_value = adv_setting
        result_mock_2 = MagicMock()
        result_mock_2.scalar_one_or_none.return_value = search_adv_setting
        session_mock.execute = AsyncMock(side_effect=[result_mock_1, result_mock_2])

        await set_common_bid_manual.set_common_bid_manual_start(
            callback, callback_data, bot, state
        )

    bot.send_message.assert_called_once_with(
        111, "Эта кнопка доступна только для Поисковых РК."
    )
    state.update_data.assert_not_called()
    state.set_state.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_common_bid_manual_apply_missing_state_data() -> None:
    """Test apply with missing FSM state data: show error, wait 1s, reload menu."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock(spec=FSMContext)
    state.get_data = AsyncMock(return_value={})  # Empty state - missing keys
    state.set_state = AsyncMock()

    message = _make_message(chat_id=111, text="100")

    wb_user_cabinet = _make_wb_user_cabinet(cabinet_id=10)
    adv_setting = _make_adv_setting(adv_setting_id=1)

    with patch(f"{MODULE}.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        with patch(f"{MODULE}.sm") as mock_sm:
            session_mock = MagicMock()
            session_mock.__aenter__ = AsyncMock(return_value=session_mock)
            session_mock.__aexit__ = AsyncMock(return_value=None)
            mock_sm.return_value = session_mock

            # Mock DB queries for reload
            result_cabinet = MagicMock()
            result_cabinet.scalar_one_or_none.return_value = wb_user_cabinet
            result_adv = MagicMock()
            result_adv.scalar_one_or_none.return_value = adv_setting

            session_mock.execute = AsyncMock(side_effect=[result_cabinet, result_adv])

            with patch(f"{MODULE}.AdvSettingMenu") as mock_menu:
                menu_instance = MagicMock()
                menu_instance.return_value = AsyncMock()
                mock_menu.return_value = menu_instance

                await set_common_bid_manual.set_common_bid_manual_apply(
                    message, bot, state
                )

    # Verify error message
    message.answer.assert_called_once()
    call_args = message.answer.call_args[0][0]
    assert "не найдены сохраненные данные" in call_args
    assert "Начните заново" in call_args
    assert "поддержку" in call_args

    # Verify state cleared
    state.set_state.assert_called_once_with(None)

    # Verify sleep called (1 second pause)
    mock_sleep.assert_called_once_with(1)

    # Verify menu NOT reloaded (because state data was empty)
    mock_menu.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_common_bid_manual_apply_partial_state_reload_menu() -> None:
    """Test apply with partial state data available: reload menu after error."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    state = MagicMock(spec=FSMContext)
    # Partial state: has IDs but missing min_bid
    state.get_data = AsyncMock(
        return_value={
            "adv_setting_original_id": 1,
            "wb_user_cabinet_original_id": 10,
            # "min_bid_search" is missing
        }
    )
    state.set_state = AsyncMock()

    message = _make_message(chat_id=111, text="100")

    wb_user_cabinet = _make_wb_user_cabinet(cabinet_id=10)
    adv_setting = _make_adv_setting(adv_setting_id=1)

    with patch(f"{MODULE}.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        with patch(f"{MODULE}.sm") as mock_sm:
            session_mock = MagicMock()
            session_mock.__aenter__ = AsyncMock(return_value=session_mock)
            session_mock.__aexit__ = AsyncMock(return_value=None)
            mock_sm.return_value = session_mock

            # Mock DB queries for reload
            result_cabinet = MagicMock()
            result_cabinet.scalar_one_or_none.return_value = wb_user_cabinet
            result_adv = MagicMock()
            result_adv.scalar_one_or_none.return_value = adv_setting

            session_mock.execute = AsyncMock(side_effect=[result_cabinet, result_adv])

            with patch(f"{MODULE}.AdvSettingMenu") as mock_menu:
                # AdvSettingMenu() returns instance, instance() is async
                menu_instance = AsyncMock()
                mock_menu.return_value = menu_instance

                await set_common_bid_manual.set_common_bid_manual_apply(
                    message, bot, state
                )

    # Verify error message
    message.answer.assert_called_once()

    # Verify state cleared
    state.set_state.assert_called_once_with(None)

    # Verify sleep called
    mock_sleep.assert_called_once_with(1)

    # Verify menu reloaded (because IDs were available)
    mock_menu.assert_called_once_with(bot, 111, wb_user_cabinet, adv_setting)
    menu_instance.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_common_bid_manual_apply_success() -> None:
    """Test successful bid update: common bid + all search keyword bids."""
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

    adv_setting = _make_adv_setting(adv_setting_id=1, search_adv_id=999)
    search_adv_setting = _make_adv_setting(adv_setting_id=999, adv_id=999)
    wb_user_cabinet = _make_wb_user_cabinet(cabinet_id=10)

    with patch(f"{MODULE}.sm") as mock_sm:
        session_mock = MagicMock()
        session_mock.__aenter__ = AsyncMock(return_value=session_mock)
        session_mock.__aexit__ = AsyncMock(return_value=None)
        mock_sm.return_value = session_mock

        # Mock multiple DB queries
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
            hub.wb_modifier.set_normquery_bids = AsyncMock()
            hub.wb_data_manager.get_current_bids_for_advs = AsyncMock(
                return_value=[
                    SimpleNamespace(advert_id=999, nm_id=12345, norm_query="купить платье"),
                    SimpleNamespace(advert_id=999, nm_id=67890, norm_query="сарафан"),
                ]
            )
            hub.redis_client_wrapper = MagicMock()

            factory.get_wb_manager_hub.return_value = hub
            container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory.return_value = factory

            mock_di.return_value.__aenter__ = AsyncMock(return_value=container)
            mock_di.return_value.__aexit__ = AsyncMock(return_value=None)

            with patch(f"{MODULE}.RedisCommonBidValueManager") as mock_redis_value:
                with patch(f"{MODULE}.RedisCommonBidTimestampManager") as mock_redis_ts:
                    redis_value_instance = MagicMock()
                    redis_value_instance.set_bids = AsyncMock()
                    mock_redis_value.return_value = redis_value_instance

                    redis_ts_instance = MagicMock()
                    redis_ts_instance.set = AsyncMock()
                    mock_redis_ts.return_value = redis_ts_instance

                    with patch(f"{MODULE}.RedisClusterBidsTimestampManager") as mock_cluster_ts:
                        cluster_ts_instance = MagicMock()
                        cluster_ts_instance.set = AsyncMock()
                        mock_cluster_ts.return_value = cluster_ts_instance

                        with patch(f"{MODULE}.AdvSettingMenu") as mock_menu:
                            # AdvSettingMenu() returns instance, instance() is async
                            menu_instance = AsyncMock()
                            mock_menu.return_value = menu_instance

                            await set_common_bid_manual.set_common_bid_manual_apply(
                                message, bot, state
                            )

    # Verify progress + success messages
    assert message.answer.await_count == 2
    progress_text = message.answer.await_args_list[0].args[0]
    success_text = message.answer.await_args_list[1].args[0]
    assert "Отправляю новую ставку в WB" in progress_text
    assert "Общая ставка поисковой РК установлена: 100 ₽" in success_text
    assert "Такая же ставка поставлена всем ключам кампании" in success_text

    # Verify state cleared
    state.set_state.assert_called_once_with(None)

    # Verify WB update called
    hub.wb_modifier.update_search_adv_common_cpm.assert_called_once()
    assert hub.wb_modifier.set_normquery_bids.await_count == 2

    # Verify Redis updates
    redis_value_instance.set_bids.assert_called_once()
    redis_ts_instance.set.assert_called_once()
    # Cluster timestamp must be stamped when any keyword bids were sent.
    cluster_ts_instance.set.assert_awaited_once_with(adv_setting)

    # Verify menu reloaded
    mock_menu.assert_called_once_with(bot, 111, wb_user_cabinet, adv_setting)
    menu_instance.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_common_bid_manual_apply_invalid_input() -> None:
    """Test apply with non-numeric input: show error, stay in state."""
    bot = MagicMock()
    state = MagicMock(spec=FSMContext)
    state.get_data = AsyncMock(
        return_value={
            "adv_setting_original_id": 1,
            "wb_user_cabinet_original_id": 10,
            "min_bid_search": 50,
        }
    )

    message = _make_message(chat_id=111, text="not a number")

    await set_common_bid_manual.set_common_bid_manual_apply(message, bot, state)

    # Verify error message about format
    message.answer.assert_called_once()
    assert "Введите целое число" in message.answer.call_args[0][0]
    assert "50 р." in message.answer.call_args[0][0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_common_bid_manual_apply_invalid_input_does_not_call_wb_write() -> None:
    """Invalid input must stop before any WB write paths are called."""
    bot = MagicMock()
    state = MagicMock(spec=FSMContext)
    state.get_data = AsyncMock(
        return_value={
            "adv_setting_original_id": 1,
            "wb_user_cabinet_original_id": 10,
            "min_bid_search": 50,
        }
    )
    message = _make_message(chat_id=111, text="abc")

    with patch(f"{MODULE}.DIManager.create") as mock_di:
        await set_common_bid_manual.set_common_bid_manual_apply(message, bot, state)

    mock_di.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_common_bid_manual_apply_partial_keyword_update_reported() -> None:
    """Partial normquery failures should return a partial success report."""
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

    adv_setting = _make_adv_setting(adv_setting_id=1, search_adv_id=999)
    search_adv_setting = _make_adv_setting(adv_setting_id=999, adv_id=999)
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
            hub.wb_modifier.set_normquery_bids = AsyncMock(
                side_effect=[None, RuntimeError("wb cluster error")]
            )
            hub.wb_data_manager.get_current_bids_for_advs = AsyncMock(
                return_value=[
                    SimpleNamespace(advert_id=999, nm_id=12345, norm_query="купить платье"),
                    SimpleNamespace(advert_id=999, nm_id=67890, norm_query="сарафан"),
                ]
            )
            hub.redis_client_wrapper = MagicMock()
            factory.get_wb_manager_hub.return_value = hub
            container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory.return_value = factory
            mock_di.return_value.__aenter__ = AsyncMock(return_value=container)
            mock_di.return_value.__aexit__ = AsyncMock(return_value=None)

            with patch(f"{MODULE}.RedisCommonBidValueManager") as mock_redis_value:
                with patch(f"{MODULE}.RedisCommonBidTimestampManager") as mock_redis_ts:
                    redis_value_instance = MagicMock()
                    redis_value_instance.set_bids = AsyncMock()
                    mock_redis_value.return_value = redis_value_instance

                    redis_ts_instance = MagicMock()
                    redis_ts_instance.set = AsyncMock()
                    mock_redis_ts.return_value = redis_ts_instance

                    with patch(f"{MODULE}.RedisClusterBidsTimestampManager") as mock_cluster_ts:
                        cluster_ts_instance = MagicMock()
                        cluster_ts_instance.set = AsyncMock()
                        mock_cluster_ts.return_value = cluster_ts_instance

                        with patch(f"{MODULE}.AdvSettingMenu") as mock_menu:
                            menu_instance = AsyncMock()
                            mock_menu.return_value = menu_instance

                            await set_common_bid_manual.set_common_bid_manual_apply(
                                message, bot, state
                            )

    reply_text = message.answer.call_args[0][0]
    assert "Общая ставка установлена: 100 ₽." in reply_text
    assert "По ключам обновлено: 1 из 2." in reply_text
    assert "сарафан" in reply_text
    # Partial keyword success still stamps cluster bids timestamp.
    cluster_ts_instance.set.assert_awaited_once_with(adv_setting)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_common_bid_manual_apply_bid_below_minimum() -> None:
    """Test apply with bid below minimum: show error, stay in state."""
    bot = MagicMock()
    state = MagicMock(spec=FSMContext)
    state.get_data = AsyncMock(
        return_value={
            "adv_setting_original_id": 1,
            "wb_user_cabinet_original_id": 10,
            "min_bid_search": 50,
        }
    )

    message = _make_message(chat_id=111, text="30")

    await set_common_bid_manual.set_common_bid_manual_apply(message, bot, state)

    # Verify error message about minimum
    message.answer.assert_called_once()
    assert "не может быть меньше минимальной" in message.answer.call_args[0][0]
    assert "50 р." in message.answer.call_args[0][0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_common_bid_manual_apply_bid_above_maximum() -> None:
    """Test apply with bid above system max: show error, stay in state."""
    bot = MagicMock()
    state = MagicMock(spec=FSMContext)
    state.get_data = AsyncMock(
        return_value={
            "adv_setting_original_id": 1,
            "wb_user_cabinet_original_id": 10,
            "min_bid_search": 50,
        }
    )

    message = _make_message(chat_id=111, text="5000")  # Above MAX_BID_RUB=3000

    await set_common_bid_manual.set_common_bid_manual_apply(message, bot, state)

    # Verify error message about maximum
    message.answer.assert_called_once()
    assert "Системное ограничение" in message.answer.call_args[0][0]
    assert "3000 р." in message.answer.call_args[0][0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reload_adv_setting_menu_success() -> None:
    """Test _reload_adv_setting_menu helper: loads data and calls AdvSettingMenu."""
    bot = MagicMock()
    chat_id = 111
    wb_user_cabinet_original_id = 10
    adv_setting_original_id = 1

    wb_user_cabinet = _make_wb_user_cabinet(cabinet_id=10)
    adv_setting = _make_adv_setting(adv_setting_id=1)

    with patch(f"{MODULE}.sm") as mock_sm:
        session_mock = MagicMock()
        session_mock.__aenter__ = AsyncMock(return_value=session_mock)
        session_mock.__aexit__ = AsyncMock(return_value=None)
        mock_sm.return_value = session_mock

        result_cabinet = MagicMock()
        result_cabinet.scalar_one_or_none.return_value = wb_user_cabinet
        result_adv = MagicMock()
        result_adv.scalar_one_or_none.return_value = adv_setting

        session_mock.execute = AsyncMock(side_effect=[result_cabinet, result_adv])

        with patch(f"{MODULE}.AdvSettingMenu") as mock_menu:
            # AdvSettingMenu() returns instance, instance() is async
            menu_instance = AsyncMock()
            mock_menu.return_value = menu_instance

            await set_common_bid_manual._reload_adv_setting_menu(
                bot, chat_id, wb_user_cabinet_original_id, adv_setting_original_id
            )

    # Verify menu created and called
    mock_menu.assert_called_once_with(bot, chat_id, wb_user_cabinet, adv_setting)
    menu_instance.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reload_adv_setting_menu_missing_data() -> None:
    """Test _reload_adv_setting_menu with missing data: don't call menu."""
    bot = MagicMock()
    chat_id = 111
    wb_user_cabinet_original_id = 10
    adv_setting_original_id = 1

    with patch(f"{MODULE}.sm") as mock_sm:
        session_mock = MagicMock()
        session_mock.__aenter__ = AsyncMock(return_value=session_mock)
        session_mock.__aexit__ = AsyncMock(return_value=None)
        mock_sm.return_value = session_mock

        # Return None for both queries (data not found)
        result_none = MagicMock()
        result_none.scalar_one_or_none.return_value = None

        session_mock.execute = AsyncMock(side_effect=[result_none, result_none])

        with patch(f"{MODULE}.AdvSettingMenu") as mock_menu:
            await set_common_bid_manual._reload_adv_setting_menu(
                bot, chat_id, wb_user_cabinet_original_id, adv_setting_original_id
            )

    # Verify menu NOT called (data not found)
    mock_menu.assert_not_called()
