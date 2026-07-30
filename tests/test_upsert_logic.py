"""Destructive PG: upsert ``AdvSetting`` via ``MainAdvManager._create_complex_advs``.

Baseline ``wbcabinet`` id=1 / ``shop_id=test_shop_id`` comes from
``reset_postgres_test_data(restore_baseline=True)`` — do not INSERT it again
(``wbcabinet_shop_id_key`` UniqueViolation).
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.wb_api.data_classes.advs.other_classes import Balances
from app.modules.adv_creator.backend.main_manager import MainAdvManager
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet

pytestmark = [
    pytest.mark.destructive_local,
]


@pytest.fixture(name="access_mock")
def _access_mock():  # pyright: ignore[reportUnusedFunction]
    """Access mock с shop_id, совпадающим с destructive PG baseline."""
    mock = MagicMock()
    mock.wb_cabinet = MagicMock(spec=WBCabinet)
    mock.wb_cabinet.shop_id = "test_shop_id"
    return mock


@pytest.mark.asyncio()
async def test_create_complex_advs_upsert_logic(
    access_mock: Any, async_session: AsyncSession
):
    """Insert then update same AdvSetting; reuse baseline WBCabinet (no re-INSERT)."""
    nmid = 518129892
    auto_adv_id_from_wb = 29918589
    search_adv_id_from_wb = 29918598

    with patch(
        "app.modules.adv_creator.backend.main_manager.WBApi"
    ) as WBAPI_mock_class, patch(
        "app.modules.adv_creator.backend.main_manager.wb_db_manager"
    ) as wb_db_manager_mock:

        WBAPI_mock_instance = AsyncMock()
        WBAPI_mock_class.return_value = WBAPI_mock_instance

        wb_db_manager_mock.update_cards_in_db = AsyncMock()

        # Mock WBApi calls
        WBAPI_mock_instance.get_adv_balances = AsyncMock(
            return_value=Balances(data={"balance": 5000, "net": 0, "bonus": 0})
        )
        mock_card = MagicMock()
        mock_card.name = "Тестовая карточка"
        WBAPI_mock_instance.get_card_by_text = AsyncMock(return_value=mock_card)
        WBAPI_mock_instance.add_to_balance = AsyncMock(return_value=1000)
        WBAPI_mock_instance.update_cpm = AsyncMock()

        # Сначала имитируем создание auto-кампании
        WBAPI_mock_instance.create_auto_adv = AsyncMock(
            return_value=auto_adv_id_from_wb
        )
        WBAPI_mock_instance.create_search_adv = AsyncMock(
            return_value=search_adv_id_from_wb
        )

        # Мокаем sm, чтобы он возвращал объект, имитирующий асинхронный контекстный менеджер
        def mock_get_async_session_maker(read_only: bool):
            mock_session_context_manager = AsyncMock()
            mock_session_context_manager.__aenter__.return_value = async_session
            mock_session_context_manager.__aexit__.return_value = None
            return mock_session_context_manager

        # Подменяем DIManager.create, чтобы использовать тестовый хаб вместо реального
        di_manager_cm = AsyncMock()
        container = MagicMock()
        module_resources = MagicMock()
        factory_container = MagicMock()
        factory = MagicMock()
        hub_mock = MagicMock()
        hub_mock.wb_data_manager = MagicMock()
        hub_mock.wb_data_manager.products_manager = MagicMock()
        target_card = MagicMock()
        target_card.name = "Тестовая карточка"
        hub_mock.wb_data_manager.products_manager.get_card_by_nmid_for_db = AsyncMock(
            return_value=(None, target_card)
        )
        factory_container.wb_manager_hub_factory.return_value = factory
        factory.get_wb_manager_hub.return_value = hub_mock
        module_resources.wb_manager_hub_factory_container = factory_container
        container.module_resources = module_resources
        di_manager_cm.__aenter__.return_value = container
        di_manager_cm.__aexit__.return_value = None
        mock_di_create = AsyncMock(return_value=di_manager_cm)

        with patch(
            "app.modules.adv_creator.backend.main_manager.sm",
            new=mock_get_async_session_maker,
        ), patch(
            "app.modules.adv_creator.backend.main_manager.DIManager.create",
            new=mock_di_create,
        ):
            manager = MainAdvManager(access_mock, MagicMock())
            # Baseline from reset_postgres_test_data — не INSERT shop_id=test_shop_id.
            wb_cabinet_db = await async_session.get(WBCabinet, 1)
            assert wb_cabinet_db is not None, (
                "expected baseline wbcabinet id=1 from reset_postgres_test_data"
            )
            assert wb_cabinet_db.shop_id == "test_shop_id"
            access_mock.wb_cabinet.id = wb_cabinet_db.id

            # # 1. Первый запуск: кампания ещё не существует в БД
            await manager._create_complex_advs(nmid)  # type: ignore[attr-defined]

            # Проверяем, что запись была добавлена
            inserted_adv = await async_session.execute(
                select(AdvSetting).where(AdvSetting.adv_id == auto_adv_id_from_wb)
            )
            adv_from_db = inserted_adv.scalar_one_or_none()
            assert adv_from_db is not None
            assert adv_from_db.search_adv_id == search_adv_id_from_wb
            assert adv_from_db.name.startswith(
                f"{nmid} Тестовая карточка"
            )  # Имя может измениться, но должно быть на основе nmid и типа
            assert adv_from_db.active_status == "created_by_bot"
            assert adv_from_db.wb_cabinet.id == access_mock.wb_cabinet.id
            # Проверяем, что дефолтные настройки были применены
            assert adv_from_db.bidder_active is True
            assert adv_from_db.max_place == 1

            # # 2. Имитируем ситуацию, когда фоновый процесс уже добавил запись
            # (что произойдет после первого вызова MainAdvManager.__create_complex_advs)
            # В данном тесте мы не делаем явную вставку, так как первый запуск уже её сделал.
            # Теперь мы проверяем, что второй запуск обновит существующую.

            # Изменяем значения, которые должны обновиться
            new_search_adv_id_from_wb = (
                30000000  # Допустим, WB выдал новый search_adv_id при повторном запросе
            )
            WBAPI_mock_instance.create_search_adv = AsyncMock(
                return_value=new_search_adv_id_from_wb
            )

            # Сбрасываем мок для scalar_one_or_none, чтобы он теперь возвращал существующий объект
            # Это уже не нужно, так как в логике main_manager мы делаем upsert
            # sm_mock.return_value.__aenter__.return_value.execute.side_effect = [
            #     MagicMock(scalar=MagicMock(return_value=access_mock.wb_cabinet)), # Для WBCabinet
            #     MagicMock(scalar_one_or_none=MagicMock(return_value=adv_from_db)), # Для AdvSetting (чтобы имитировать, что он уже есть)
            # ]

            # Второй запуск: кампания уже существует, ожидаем UPDATE
            await manager._create_complex_advs(nmid)

            # Проверяем, что запись ОБНОВИЛАСЬ, а не создалась новая
            updated_adv = await async_session.execute(
                select(AdvSetting).where(AdvSetting.adv_id == auto_adv_id_from_wb)
            )
            updated_adv_from_db = updated_adv.scalar_one_or_none()

            assert updated_adv_from_db is not None
            await async_session.refresh(
                updated_adv_from_db
            )  # Обновляем состояние объекта из БД
            assert (
                updated_adv_from_db.id == adv_from_db.id
            )  # ID записи в БД должен остаться тем же
            assert (
                updated_adv_from_db.search_adv_id == new_search_adv_id_from_wb
            )  # Должен обновиться

            # Убеждаемся, что не было второй попытки добавить AdvSetting (если upsert сработал как update)
            # Это может быть сложно проверить через мок session.add, т.к. session.add может быть вызван
            # даже при update, если объект был detached. Главное - что нет IntegrityError.
            # Вместо этого, проверяем, что количество записей AdvSetting == 1
            count_stmt = select(func.count(AdvSetting.id)).filter(
                AdvSetting.adv_id == auto_adv_id_from_wb
            )
            count_result = await async_session.execute(count_stmt)
            assert count_result.scalar_one() == 1

