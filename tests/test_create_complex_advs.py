from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.mp.wb.api.domain_managers import ProductCardInfo
from app.core.wb_api.data_classes.advs.base_adv import Adv
from app.core.wb_api.data_classes.advs.other_classes import Balances
from app.modules.adv_creator.backend import MainAdvManager
from app.modules.adv_creator.backend.exc import (
    AdvExistsForNmidError,
)
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet

pytestmark = pytest.mark.destructive_local
@pytest.fixture
def bot_mock():
    bot_mock = MagicMock(spec=Bot)
    return bot_mock


@pytest.fixture
async def client_session_mock():
    session = AsyncMock(return_value=None)
    session.close = AsyncMock(return_value=None)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    return session


@pytest.mark.parametrize(
    "hard_mode, exist_adv_ids_rows, should_raise",
    [
        [True, [(25040169, 25040170), (876868, 9789700)], False],
        [
            False,
            [(25040169, 25040170), (876868, 9789700)],
            True,
        ],  # hard_mode=False + существующие РК = ошибка
        [True, [], False],
        [False, [], False],
        [True, [(25040169, None), (876868, 9789700)], False],
        [
            False,
            [(25040169, None), (876868, 9789700)],
            True,
        ],  # hard_mode=False + существующие РК = ошибка
    ],
)
@pytest.mark.asyncio
async def test_create_complex_advs(
    access_mock,
    bot_mock,
    client_session_mock,
    hard_mode: bool,
    exist_adv_ids_rows,
    should_raise: bool,
    async_session: AsyncSession,
):
    user_telegram_id = 122334
    nmid = 112333

    card_from_wb_mock = MagicMock()
    card_from_wb_mock.name = "Test Card"

    products_manager_mock = MagicMock()
    products_manager_mock.get_card_by_nmid_for_db = AsyncMock(
        return_value=(
            ProductCardInfo(name="Test Card", nmid=nmid),
            card_from_wb_mock,
        )
    )
    hub_mock = MagicMock()
    hub_mock.wb_data_manager.products_manager = products_manager_mock
    factory_mock = MagicMock()
    factory_mock.get_wb_manager_hub.return_value = hub_mock
    container_mock = MagicMock()
    container_mock.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory.return_value = factory_mock

    mock_di_create = AsyncMock()
    mock_acm = MagicMock()
    mock_acm.__aenter__ = AsyncMock(return_value=container_mock)
    mock_acm.__aexit__ = AsyncMock(return_value=None)
    mock_di_create.return_value = mock_acm

    with patch(
        "app.modules.adv_creator.backend.main_manager.DIManager.create",
        mock_di_create,
    ), patch(
        "app.modules.adv_creator.backend.main_manager.WBApi"
    ) as WBAPI_mock_class, patch(
        "app.modules.adv_creator.backend.main_manager.wb_db_manager"
    ) as wb_db_manager_mock, patch(
        "app.modules.adv_creator.backend.main_manager.sm"
    ) as sm_mock:
        WBAPI_mock_instance = AsyncMock(return_value=None)
        WBAPI_mock_class.return_value = WBAPI_mock_instance
        wb_db_manager_mock.update_cards_in_db = AsyncMock(return_value=None)

        # Mock the session maker
        session_mock = AsyncMock()
        session_mock.__aenter__ = AsyncMock(return_value=session_mock)
        session_mock.__aexit__ = AsyncMock(return_value=None)

        # Mock the result of execute().scalar()
        wb_cabinet_obj = WBCabinet()
        wb_cabinet_obj.id = 1
        wb_cabinet_obj.shop_id = "test_shop"
        result_mock = MagicMock()
        result_mock.scalar = MagicMock(return_value=wb_cabinet_obj)
        execute_mock = AsyncMock(return_value=result_mock)
        session_mock.execute = execute_mock
        session_mock.commit = AsyncMock()
        sm_mock.return_value = session_mock

        all_adv_ids = {row[0] for row in exist_adv_ids_rows}
        MainAdvManager.get_all_adv_ids_for_nmid = AsyncMock(
            return_value=all_adv_ids
        )
        MainAdvManager.__turn_off_advs = AsyncMock(return_value=None)
        manager = MainAdvManager(access_mock, client_session_mock)

        # Mock the WBApi instance methods with AsyncMock
        WBAPI_mock_instance.get_adv_balances = AsyncMock(
            return_value=Balances(data={"balance": 5000, "net": 0, "bonus": 0})
        )
        WBAPI_mock_instance.create_auto_adv = AsyncMock(return_value=111111)
        WBAPI_mock_instance.add_to_balance = AsyncMock(return_value=4000)
        WBAPI_mock_instance.create_search_adv = AsyncMock(return_value=222222)
        WBAPI_mock_instance.update_cpm = AsyncMock(return_value=None)

        adv_from_wb_mock_1 = MagicMock(spec=Adv)
        adv_from_wb_mock_2 = MagicMock(spec=Adv)

        WBAPI_mock_instance.get_advs = AsyncMock(
            return_value=[adv_from_wb_mock_1, adv_from_wb_mock_2]
        )

        if should_raise:
            with pytest.raises(AdvExistsForNmidError):
                await manager.create_complex_advs(
                    bot_mock, user_telegram_id, nmid, hard_mode=hard_mode
                )
        else:
            result = await manager.create_complex_advs(
                bot_mock, user_telegram_id, nmid, hard_mode=hard_mode
            )
            assert result == (111111, 222222)
            mock_di_create.assert_awaited()
            WBAPI_mock_instance.get_adv_balances.assert_awaited()
            WBAPI_mock_instance.create_auto_adv.assert_awaited()
            WBAPI_mock_instance.create_search_adv.assert_awaited()
            wb_db_manager_mock.update_cards_in_db.assert_awaited()
            assert WBAPI_mock_instance.add_to_balance.await_count >= 2


@pytest.mark.asyncio
async def test_create_complex_advs_when_exists(
    access_mock,
    adv_setting_mock,
    bot_mock,
    client_session_mock,
    async_session: AsyncSession,
):
    """Тест проверяет, что при существующей РК выбрасывается AdvExistsForNmidError"""
    nmid = 112333
    user_telegram_id = 122334
    adv_setting_mock.active_status = "started"  # РК активна
    adv_setting_mock.adv_id = 25040169
    adv_setting_mock.search_adv_id = 25040170

    with patch(
        "app.modules.adv_creator.backend.main_manager.WBApi"
    ) as WBAPI_mock_class:
        WBAPI_mock_instance = AsyncMock(return_value=None) # noqa
        WBAPI_mock_class.return_value = WBAPI_mock_instance

        manager = MainAdvManager(access_mock, client_session_mock)
        manager.get_all_adv_ids_for_nmid = AsyncMock(
            return_value={25040169}
        )

        with pytest.raises(AdvExistsForNmidError):
            await manager.create_complex_advs(
                bot_mock, user_telegram_id, nmid, hard_mode=False
            )






