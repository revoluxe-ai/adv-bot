"""Tests for billing per-cabinet daily charge logic."""

import asyncio
import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.engine import Result
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing.billing import (
    get_active_cabinets_with_data,
    get_count_advs_for_wb_cabinet,
    process_payment_for_advs,
)
from app.modules.billing.pricer import Pricer
from app.modules.billing.redis_manager import RedisManager
from app.modules.common_slaves.wildberries.models import AdvSetting


@pytest.fixture
def mock_adv_setting():
    adv_setting = MagicMock(spec=AdvSetting)
    adv_setting.id = 1
    adv_setting.adv_id = "test_adv_id_1"
    adv_setting.bot_active = True
    adv_setting.auto_update_white_list = True
    adv_setting.auto_update_target_place = True
    adv_setting.payments = []
    adv_setting.wb_cabinet_id = 100  # Устанавливаем wb_cabinet_id для соответствия WBCabinet
    return adv_setting


@pytest.fixture
def mock_adv_setting_inactive():
    adv_setting = MagicMock(spec=AdvSetting)
    adv_setting.id = 2
    adv_setting.adv_id = "test_adv_id_2"
    adv_setting.bot_active = False
    adv_setting.auto_update_white_list = False
    adv_setting.auto_update_target_place = False
    adv_setting.payments = []
    adv_setting.wb_cabinet_id = 100
    return adv_setting


@pytest.fixture
def mock_wb_cabinet():
    wb_cabinet = MagicMock()
    wb_cabinet.id = 100
    wb_cabinet.shop_id = 123
    wb_cabinet.calculated_bonus = 100.0
    wb_cabinet.calculated_balance = 50.0
    wb_cabinet.balance_payments = []
    wb_cabinet.bonus_payments = []
    wb_cabinet.adv_settings = []  # Добавляем для загрузки связей
    return wb_cabinet


@pytest.fixture
def mock_wb_cabinet_2():
    wb_cabinet = MagicMock()
    wb_cabinet.id = 200
    wb_cabinet.shop_id = 456
    wb_cabinet.calculated_bonus = 200.0
    wb_cabinet.calculated_balance = 100.0
    wb_cabinet.balance_payments = []
    wb_cabinet.bonus_payments = []
    wb_cabinet.adv_settings = []  # Добавляем для загрузки связей
    return wb_cabinet


@pytest.fixture
def mock_pricer():
    pricer = AsyncMock(spec=Pricer)
    pricer.get_price_for_day_for_shop.return_value = 100.0
    return pricer


@pytest.fixture
def mock_session():
    session = AsyncMock(spec=AsyncSession)
    # Имитируем поведение session.execute().unique().scalars().all()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_unique = MagicMock()
    mock_unique.scalars.return_value = mock_scalars
    mock_result = MagicMock(spec=Result)  # Указываем spec=Result
    mock_result.unique.return_value = mock_unique
    mock_result.scalar.return_value = None  # Для scalar() вызовов

    session.execute.return_value = mock_result
    return session


@pytest.fixture
def mock_redis_manager():
    redis_manager = AsyncMock(spec=RedisManager)
    redis_manager.get_billing_process_for_day.return_value = False
    redis_manager.set_billing_process_for_day.return_value = None
    return redis_manager


def test_get_count_advs_for_wb_cabinet(mock_adv_setting, mock_wb_cabinet):
    mock_adv_setting.wb_cabinet_id = mock_wb_cabinet.id

    # Тест: один adv_setting для кабинета
    adv_settings = [mock_adv_setting]
    result = get_count_advs_for_wb_cabinet(mock_wb_cabinet, adv_settings)
    assert result == 1

    # Тест: несколько adv_settings, некоторые принадлежат другому кабинету
    adv_setting_2 = MagicMock(spec=AdvSetting)
    adv_setting_2.wb_cabinet_id = 101  # Другой кабинет

    adv_setting_3 = MagicMock(spec=AdvSetting)
    adv_setting_3.wb_cabinet_id = mock_wb_cabinet.id  # Этот относится к тому же кабинету

    adv_settings = [mock_adv_setting, adv_setting_2, adv_setting_3]
    result = get_count_advs_for_wb_cabinet(mock_wb_cabinet, adv_settings)
    assert result == 2  # mock_adv_setting и adv_setting_3

    # Тест: пустой список adv_settings
    result = get_count_advs_for_wb_cabinet(mock_wb_cabinet, [])
    assert result == 0

    # Тест: ни один adv_setting не принадлежит кабинету
    adv_setting_4 = MagicMock(spec=AdvSetting)
    adv_setting_4.wb_cabinet_id = 102
    adv_settings = [adv_setting_4, adv_setting_2]
    result = get_count_advs_for_wb_cabinet(mock_wb_cabinet, adv_settings)
    assert result == 0


@pytest.mark.asyncio
async def test_get_active_cabinets_with_data(
    mock_session, mock_wb_cabinet, mock_adv_setting, mock_adv_setting_inactive
):
    # Настраиваем wb_cabinet
    mock_wb_cabinet.adv_settings = [mock_adv_setting, mock_adv_setting_inactive]

    # Имитируем возвращаемое значение execute().unique().scalars().all()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [mock_wb_cabinet]
    mock_unique = MagicMock()
    mock_unique.scalars.return_value = mock_scalars
    mock_result = MagicMock(spec=Result)
    mock_result.unique.return_value = mock_unique

    mock_session.execute.return_value = mock_result

    cabinets = await get_active_cabinets_with_data(mock_session)
    assert len(cabinets) == 1
    assert cabinets[0].id == mock_wb_cabinet.id
    # Проверяем, что AdvSetting также загружены
    assert len(cabinets[0].adv_settings) == 2  # Должны быть оба AdvSetting, активные и неактивные


@pytest.mark.asyncio
@patch("app.modules.billing.billing.sm", new_callable=MagicMock)
async def test_process_payment_for_advs_success_bonus(
    mock_sm, mock_adv_setting, mock_wb_cabinet, mock_pricer, mock_redis_manager
):
    current_date = datetime.date(2023, 1, 1)
    mock_session = AsyncMock(spec=AsyncSession)
    # Get the mocked sm instance that was patched by the decorator
    mock_sm.return_value.__aenter__.return_value = mock_session
    mock_sm.return_value.__aexit__.return_value = False  # Убеждаемся, что aexit не вызывает исключение

    # Настраиваем кабинет и кампании
    mock_adv_setting.wb_cabinet_id = mock_wb_cabinet.id
    mock_adv_setting.bot_active = True
    mock_wb_cabinet.adv_settings = [mock_adv_setting]
    mock_wb_cabinet.calculated_bonus = 100.0
    mock_pricer.get_price_for_day_for_shop.return_value = 75.0  # Цена меньше бонусов

    # Мокируем get_active_cabinets_with_data
    with patch(
        "app.modules.billing.billing.get_active_cabinets_with_data",
        new_callable=AsyncMock,
    ) as mock_get_active_cabinets_with_data:
        mock_get_active_cabinets_with_data.return_value = [mock_wb_cabinet]

        # Мокируем RedisManager
        with patch("app.modules.billing.billing.redis_manager", new=mock_redis_manager):
            # Мокируем scalar() для проверки существующих платежей (DB)
            mock_session.execute.side_effect = [
                MagicMock(scalar=MagicMock(return_value=0)),  # Для advisory lock
                MagicMock(scalar=MagicMock(return_value=0)),  # Для bonus_cnt_res
                MagicMock(scalar=MagicMock(return_value=0)),  # Для balance_cnt_res
                MagicMock(scalar_one_or_none=MagicMock(return_value=None)),  # Для AdvPayment
                MagicMock(scalar=MagicMock(return_value=None)),  # Для unlock
            ]

            await process_payment_for_advs(current_date=current_date, pricer=mock_pricer)

            mock_get_active_cabinets_with_data.assert_called_once_with(mock_session)
            mock_pricer.get_price_for_day_for_shop.assert_called_once_with(str(mock_wb_cabinet.shop_id))

            # Проверяем, что были добавлены правильные платежи
            # Извлекаем объект WBBonusPayment и проверяем его атрибуты
            added_bonus_payment = mock_session.add.call_args_list[0].args[0]
            assert added_bonus_payment.wb_cabinet_id == mock_wb_cabinet.id
            assert added_bonus_payment.amount == pytest.approx(-75.0, abs=1e-2)
            assert added_bonus_payment.description == f"Ежедневное списание за 1 кампаний, дата: {current_date}"
            assert added_bonus_payment.operation_type == "auto_subtract"
            assert isinstance(added_bonus_payment.transaction_date_time, datetime.datetime)

            # Проверяем AdvPayment
            added_adv_payment = mock_session.add.call_args_list[1].args[0]
            assert added_adv_payment.date == current_date
            assert added_adv_payment.amount == 75.0
            assert added_adv_payment.adv_setting_id == mock_adv_setting.id
            assert mock_session.add.call_count == 2  # Должно быть два добавления

            mock_session.commit.assert_called_once()
            mock_session.rollback.assert_not_called()
            mock_redis_manager.set_billing_process_for_day.assert_called_once_with(mock_wb_cabinet.id, current_date)


@pytest.mark.asyncio
@patch("app.modules.billing.billing.sm", new_callable=MagicMock)
async def test_process_payment_for_advs_success_balance(
    mock_sm, mock_adv_setting, mock_wb_cabinet, mock_pricer, mock_redis_manager
):
    current_date = datetime.date(2023, 1, 1)
    mock_session = AsyncMock(spec=AsyncSession)
    # Get the mocked sm instance that was patched by the decorator
    mock_sm.return_value.__aenter__.return_value = mock_session
    mock_sm.return_value.__aexit__.return_value = False

    # Настраиваем кабинет и кампании
    mock_adv_setting.wb_cabinet_id = mock_wb_cabinet.id
    mock_adv_setting.bot_active = True
    mock_wb_cabinet.adv_settings = [mock_adv_setting]
    mock_wb_cabinet.calculated_bonus = 0.0
    mock_wb_cabinet.calculated_balance = 100.0
    mock_pricer.get_price_for_day_for_shop.return_value = 75.0

    # Мокируем get_active_cabinets_with_data
    with patch(
        "app.modules.billing.billing.get_active_cabinets_with_data",
        new_callable=AsyncMock,
    ) as mock_get_active_cabinets_with_data:
        mock_get_active_cabinets_with_data.return_value = [mock_wb_cabinet]

        # Мокируем RedisManager
        with patch("app.modules.billing.billing.redis_manager", new=mock_redis_manager):
            mock_session.execute.side_effect = [
                MagicMock(scalar=MagicMock(return_value=0)),  # Для advisory lock
                MagicMock(scalar=MagicMock(return_value=0)),  # Для bonus_cnt_res
                MagicMock(scalar=MagicMock(return_value=0)),  # Для balance_cnt_res
                MagicMock(scalar_one_or_none=MagicMock(return_value=None)),  # Для AdvPayment
                MagicMock(scalar=MagicMock(return_value=None)),  # Для unlock
            ]

            await process_payment_for_advs(current_date=current_date, pricer=mock_pricer)

            mock_get_active_cabinets_with_data.assert_called_once_with(mock_session)
            mock_pricer.get_price_for_day_for_shop.assert_called_once_with(str(mock_wb_cabinet.shop_id))

            # Проверяем, что были добавлены правильные платежи
            # Извлекаем объект WBBalancePayment и проверяем его атрибуты
            added_balance_payment = mock_session.add.call_args_list[0].args[0]
            assert added_balance_payment.wb_cabinet_id == mock_wb_cabinet.id
            assert added_balance_payment.amount == pytest.approx(-75.0, abs=1e-2)
            assert added_balance_payment.description == f"Ежедневное списание за 1 кампаний, дата: {current_date}"
            assert added_balance_payment.operation_type == "auto_subtract"
            assert isinstance(added_balance_payment.transaction_date_time, datetime.datetime)

            # Проверяем второй вызов add (AdvPayment)
            added_adv_payment = mock_session.add.call_args_list[1].args[0]
            assert added_adv_payment.date == current_date
            assert added_adv_payment.amount == 75.0
            assert added_adv_payment.adv_setting_id == mock_adv_setting.id
            assert mock_session.add.call_count == 2

            mock_session.commit.assert_called_once()
            mock_session.rollback.assert_not_called()
            mock_redis_manager.set_billing_process_for_day.assert_called_once_with(mock_wb_cabinet.id, current_date)


@pytest.mark.asyncio
@patch("app.modules.billing.billing.sm", new_callable=MagicMock)
async def test_process_payment_for_advs_insufficient_funds(
    mock_sm, mock_adv_setting, mock_wb_cabinet, mock_pricer, mock_redis_manager
):
    current_date = datetime.date(2023, 1, 1)
    mock_session = AsyncMock(spec=AsyncSession)
    # Get the mocked sm instance that was patched by the decorator
    mock_sm.return_value.__aenter__.return_value = mock_session
    mock_sm.return_value.__aexit__.return_value = False

    # Настраиваем кабинет и кампании
    mock_adv_setting.wb_cabinet_id = mock_wb_cabinet.id
    mock_adv_setting.bot_active = True
    mock_wb_cabinet.adv_settings = [mock_adv_setting]
    mock_wb_cabinet.calculated_bonus = 0.0
    mock_wb_cabinet.calculated_balance = 0.0
    mock_pricer.get_price_for_day_for_shop.return_value = 75.0

    # Мокируем get_active_cabinets_with_data
    with patch(
        "app.modules.billing.billing.get_active_cabinets_with_data",
        new_callable=AsyncMock,
    ) as mock_get_active_cabinets_with_data:
        mock_get_active_cabinets_with_data.return_value = [mock_wb_cabinet]

        # Мокируем RedisManager
        with patch("app.modules.billing.billing.redis_manager", new=mock_redis_manager):
            mock_session.execute.side_effect = [
                MagicMock(scalar=MagicMock(return_value=0)),  # Для advisory lock
                MagicMock(scalar=MagicMock(return_value=0)),  # Для bonus_cnt_res
                MagicMock(scalar=MagicMock(return_value=0)),  # Для balance_cnt_res
                MagicMock(scalar_one_or_none=MagicMock(return_value=None)),  # Для AdvPayment
                MagicMock(scalar=MagicMock(return_value=None)),  # Для unlock
            ]

            await process_payment_for_advs(current_date=current_date, pricer=mock_pricer)

            mock_get_active_cabinets_with_data.assert_called_once_with(mock_session)
            mock_pricer.get_price_for_day_for_shop.assert_called_once_with(str(mock_wb_cabinet.shop_id))

            # Проверяем, что кампании были деактивированы
            assert mock_adv_setting.bot_active is False
            assert mock_adv_setting.auto_update_white_list is False
            assert mock_adv_setting.auto_update_target_place is False

            # Проверяем, что AdvPayment был создан (история)
            mock_session.add.assert_called_once()
            added_adv_payment = mock_session.add.call_args[0][0]
            assert added_adv_payment.date == current_date
            assert added_adv_payment.amount == 75.0
            assert added_adv_payment.adv_setting_id == mock_adv_setting.id

            mock_session.commit.assert_called_once()
            mock_session.rollback.assert_not_called()
            mock_redis_manager.set_billing_process_for_day.assert_called_once_with(mock_wb_cabinet.id, current_date)


@pytest.mark.asyncio
@patch("app.modules.billing.billing.sm", new_callable=MagicMock)
async def test_process_payment_for_advs_no_active_cabinets(mock_sm, mock_pricer, mock_redis_manager):
    current_date = datetime.date(2023, 1, 1)
    mock_session = AsyncMock(spec=AsyncSession)
    # Get the mocked sm instance that was patched by the decorator
    mock_sm.return_value.__aenter__.return_value = mock_session
    mock_sm.return_value.__aexit__.return_value = False

    with patch(
        "app.modules.billing.billing.get_active_cabinets_with_data",
        new_callable=AsyncMock,
    ) as mock_get_active_cabinets_with_data:
        mock_get_active_cabinets_with_data.return_value = []  # Нет активных кабинетов

        with patch("app.modules.billing.billing.redis_manager", new=mock_redis_manager):
            await process_payment_for_advs(current_date=current_date, pricer=mock_pricer)

            mock_get_active_cabinets_with_data.assert_called_once_with(mock_session)
            mock_pricer.get_price_for_day_for_shop.assert_not_called()  # Не должен вызываться
            mock_session.add.assert_not_called()
            mock_session.commit.assert_not_called()
            mock_session.rollback.assert_not_called()
            mock_redis_manager.get_billing_process_for_day.assert_not_called()
            mock_redis_manager.set_billing_process_for_day.assert_not_called()


@pytest.mark.asyncio
@patch("app.modules.billing.billing.sm", new_callable=MagicMock)
async def test_process_payment_for_advs_cabinet_already_processed_redis(
    mock_sm, mock_adv_setting, mock_wb_cabinet, mock_pricer, mock_redis_manager
):
    current_date = datetime.date(2023, 1, 1)
    mock_session = AsyncMock(spec=AsyncSession)
    # Get the mocked sm instance that was patched by the decorator
    mock_sm.return_value.__aenter__.return_value = mock_session
    mock_sm.return_value.__aexit__.return_value = False

    mock_adv_setting.wb_cabinet_id = mock_wb_cabinet.id
    mock_adv_setting.bot_active = True
    mock_wb_cabinet.adv_settings = [mock_adv_setting]

    with patch(
        "app.modules.billing.billing.get_active_cabinets_with_data",
        new_callable=AsyncMock,
    ) as mock_get_active_cabinets_with_data:
        mock_get_active_cabinets_with_data.return_value = [mock_wb_cabinet]

        with patch("app.modules.billing.billing.redis_manager", new=mock_redis_manager):
            mock_redis_manager.get_billing_process_for_day.return_value = True  # Уже обработан

            # Для advisory lock, который все равно будет вызван
            mock_session.execute.return_value = MagicMock(scalar=MagicMock(return_value=0))

            await process_payment_for_advs(current_date=current_date, pricer=mock_pricer)

            mock_get_active_cabinets_with_data.assert_called_once_with(mock_session)
            mock_redis_manager.get_billing_process_for_day.assert_called_once_with(mock_wb_cabinet.id, current_date)
            mock_pricer.get_price_for_day_for_shop.assert_not_called()
            mock_session.add.assert_not_called()
            mock_session.commit.assert_called_once()  # commit все равно будет вызван в конце process_payment_for_advs
            mock_session.rollback.assert_not_called()
            mock_redis_manager.set_billing_process_for_day.assert_not_called()


@pytest.mark.asyncio
@patch("app.modules.billing.billing.sm", new_callable=MagicMock)
async def test_process_payment_for_advs_cabinet_already_processed_db(
    mock_sm, mock_adv_setting, mock_wb_cabinet, mock_pricer, mock_redis_manager
):
    current_date = datetime.date(2023, 1, 1)
    mock_session = AsyncMock(spec=AsyncSession)
    # Get the mocked sm instance that was patched by the decorator
    mock_sm.return_value.__aenter__.return_value = mock_session
    mock_sm.return_value.__aexit__.return_value = False

    mock_adv_setting.wb_cabinet_id = mock_wb_cabinet.id
    mock_adv_setting.bot_active = True
    mock_wb_cabinet.adv_settings = [mock_adv_setting]

    with patch(
        "app.modules.billing.billing.get_active_cabinets_with_data",
        new_callable=AsyncMock,
    ) as mock_get_active_cabinets_with_data:
        mock_get_active_cabinets_with_data.return_value = [mock_wb_cabinet]

        with patch("app.modules.billing.billing.redis_manager", new=mock_redis_manager):
            mock_redis_manager.get_billing_process_for_day.return_value = False  # Не обработан в Redis

            # Имитируем, что платеж уже есть в БД
            mock_session.execute.side_effect = [
                MagicMock(scalar=MagicMock(return_value=0)),  # Для advisory lock
                MagicMock(scalar=MagicMock(return_value=1)),  # Для bonus_cnt_res (уже есть платеж)
                MagicMock(scalar=MagicMock(return_value=0)),  # Для balance_cnt_res
                MagicMock(scalar=MagicMock(return_value=None)),  # Для unlock
            ]

            await process_payment_for_advs(current_date=current_date, pricer=mock_pricer)

            mock_get_active_cabinets_with_data.assert_called_once_with(mock_session)
            mock_redis_manager.get_billing_process_for_day.assert_called_once_with(mock_wb_cabinet.id, current_date)
            mock_pricer.get_price_for_day_for_shop.assert_not_called()
            mock_session.add.assert_not_called()
            mock_session.commit.assert_called_once()  # commit все равно будет вызван в конце process_payment_for_advs
            mock_session.rollback.assert_not_called()
            mock_redis_manager.set_billing_process_for_day.assert_not_called()


@pytest.mark.asyncio
@patch("app.modules.billing.billing.sm", new_callable=MagicMock)
async def test_process_payment_for_advs_zero_daily_price(
    mock_sm, mock_adv_setting, mock_wb_cabinet, mock_pricer, mock_redis_manager
):
    current_date = datetime.date(2023, 1, 1)
    mock_session = AsyncMock(spec=AsyncSession)
    # Get the mocked sm instance that was patched by the decorator
    mock_sm.return_value.__aenter__.return_value = mock_session
    mock_sm.return_value.__aexit__.return_value = False

    mock_adv_setting.wb_cabinet_id = mock_wb_cabinet.id
    mock_adv_setting.bot_active = True
    mock_wb_cabinet.adv_settings = [mock_adv_setting]
    mock_pricer.get_price_for_day_for_shop.return_value = 0.0  # Нулевая цена

    with patch(
        "app.modules.billing.billing.get_active_cabinets_with_data",
        new_callable=AsyncMock,
    ) as mock_get_active_cabinets_with_data:
        mock_get_active_cabinets_with_data.return_value = [mock_wb_cabinet]

        with patch("app.modules.billing.billing.redis_manager", new=mock_redis_manager):
            mock_session.execute.side_effect = [
                MagicMock(scalar=MagicMock(return_value=0)),  # Для advisory lock
                MagicMock(scalar=MagicMock(return_value=0)),  # Для bonus_cnt_res
                MagicMock(scalar=MagicMock(return_value=0)),  # Для balance_cnt_res
                MagicMock(scalar=MagicMock(return_value=None)),  # Для unlock
            ]

            await process_payment_for_advs(current_date=current_date, pricer=mock_pricer)

            mock_get_active_cabinets_with_data.assert_called_once_with(mock_session)
            mock_pricer.get_price_for_day_for_shop.assert_called_once_with(str(mock_wb_cabinet.shop_id))
            mock_session.add.assert_not_called()
            mock_session.commit.assert_called_once()  # commit все равно будет вызван в конце process_payment_for_advs
            mock_session.rollback.assert_not_called()
            mock_redis_manager.set_billing_process_for_day.assert_not_called()


@pytest.mark.asyncio
@patch("app.modules.billing.billing.sm", new_callable=MagicMock)
async def test_process_payment_for_advs_exception_during_processing(
    mock_sm, mock_adv_setting, mock_wb_cabinet, mock_pricer, mock_redis_manager
):
    current_date = datetime.date(2023, 1, 1)
    mock_session = AsyncMock(spec=AsyncSession)
    # Get the mocked sm instance that was patched by the decorator
    mock_sm.return_value.__aenter__.return_value = mock_session
    mock_sm.return_value.__aexit__.return_value = False

    mock_adv_setting.wb_cabinet_id = mock_wb_cabinet.id
    mock_adv_setting.bot_active = True
    mock_wb_cabinet.adv_settings = [mock_adv_setting]
    mock_pricer.get_price_for_day_for_shop.return_value = 75.0

    with patch(
        "app.modules.billing.billing.get_active_cabinets_with_data",
        new_callable=AsyncMock,
    ) as mock_get_active_cabinets_with_data:
        mock_get_active_cabinets_with_data.return_value = [mock_wb_cabinet]

        with patch("app.modules.billing.billing.redis_manager", new=mock_redis_manager):
            # Мокируем, что get_price_for_day_for_shop вызывает исключение
            mock_pricer.get_price_for_day_for_shop.side_effect = Exception("Pricer Error")

            mock_session.execute.side_effect = [
                MagicMock(scalar=MagicMock(return_value=0)),  # Для advisory lock
                MagicMock(scalar=MagicMock(return_value=0)),  # Для bonus_cnt_res
                MagicMock(scalar=MagicMock(return_value=0)),  # Для balance_cnt_res
                MagicMock(scalar=MagicMock(return_value=None)),  # Для unlock (вызывается в finally)
            ]

            with pytest.raises(Exception, match="Pricer Error"):
                await process_payment_for_advs(current_date=current_date, pricer=mock_pricer)

            mock_session.rollback.assert_called_once()
            mock_session.commit.assert_not_called()
            mock_redis_manager.set_billing_process_for_day.assert_not_called()


@pytest.mark.asyncio
@patch("app.modules.billing.billing.sm", new_callable=MagicMock)
async def test_process_payment_for_advs_no_active_campaigns_in_cabinet(
    mock_sm, mock_wb_cabinet, mock_adv_setting_inactive, mock_pricer, mock_redis_manager
):
    current_date = datetime.date(2023, 1, 1)
    mock_session = AsyncMock(spec=AsyncSession)
    # Get the mocked sm instance that was patched by the decorator
    mock_sm.return_value.__aenter__.return_value = mock_session
    mock_sm.return_value.__aexit__.return_value = False

    mock_wb_cabinet.adv_settings = [mock_adv_setting_inactive]  # Только неактивная кампания

    with patch(
        "app.modules.billing.billing.get_active_cabinets_with_data",
        new_callable=AsyncMock,
    ) as mock_get_active_cabinets_with_data:
        mock_get_active_cabinets_with_data.return_value = [mock_wb_cabinet]

        with patch("app.modules.billing.billing.redis_manager", new=mock_redis_manager):
            # Только advisory lock, остальное не должно вызываться
            mock_session.execute.return_value = MagicMock(scalar=MagicMock(return_value=0))  # Для advisory lock

            await process_payment_for_advs(current_date=current_date, pricer=mock_pricer)

            mock_get_active_cabinets_with_data.assert_called_once_with(mock_session)
            mock_redis_manager.get_billing_process_for_day.assert_not_called()
            mock_pricer.get_price_for_day_for_shop.assert_not_called()
            mock_session.add.assert_not_called()
            mock_session.commit.assert_called_once()  # commit все равно будет вызван в конце process_payment_for_advs
            mock_session.rollback.assert_not_called()
            mock_redis_manager.set_billing_process_for_day.assert_not_called()


@pytest.mark.asyncio
@patch("app.modules.billing.billing.sm", new_callable=MagicMock)
async def test_process_payment_for_advs_multiple_cabinets(
    mock_sm,
    mock_adv_setting,
    mock_adv_setting_inactive,
    mock_wb_cabinet,
    mock_wb_cabinet_2,
    mock_pricer,
    mock_redis_manager,
):
    current_date = datetime.date(2023, 1, 1)
    mock_session = AsyncMock(spec=AsyncSession)
    mock_sm.return_value.__aenter__.return_value = mock_session
    mock_sm.return_value.__aexit__.return_value = False

    # Настраиваем первый кабинет
    mock_adv_setting.wb_cabinet_id = mock_wb_cabinet.id
    mock_adv_setting.bot_active = True
    mock_wb_cabinet.adv_settings = [mock_adv_setting]
    mock_wb_cabinet.calculated_bonus = 100.0

    # Настраиваем второй кабинет
    adv_setting_2 = MagicMock(spec=AdvSetting)
    adv_setting_2.id = 3
    adv_setting_2.adv_id = "test_adv_id_3"
    adv_setting_2.bot_active = True
    adv_setting_2.wb_cabinet_id = mock_wb_cabinet_2.id

    mock_wb_cabinet_2.adv_settings = [adv_setting_2]
    mock_wb_cabinet_2.calculated_balance = 100.0

    # Мокируем get_active_cabinets_with_data
    with patch(
        "app.modules.billing.billing.get_active_cabinets_with_data",
        new_callable=AsyncMock,
    ) as mock_get_active_cabinets_with_data:
        mock_get_active_cabinets_with_data.return_value = [
            mock_wb_cabinet,
            mock_wb_cabinet_2,
        ]

        # Мокируем RedisManager
        with patch("app.modules.billing.billing.redis_manager", new=mock_redis_manager):
            # Последовательность side_effect для mock_session.execute
            mock_session.execute.side_effect = [
                # Для первого кабинета
                MagicMock(scalar=MagicMock(return_value=0)),  # lock 1
                MagicMock(scalar=MagicMock(return_value=0)),  # bonus_cnt 1
                MagicMock(scalar=MagicMock(return_value=0)),  # balance_cnt 1
                MagicMock(scalar_one_or_none=MagicMock(return_value=None)),  # AdvPayment 1
                MagicMock(scalar=MagicMock(return_value=None)),  # unlock 1
                # Для второго кабинета
                MagicMock(scalar=MagicMock(return_value=0)),  # lock 2
                MagicMock(scalar=MagicMock(return_value=0)),  # bonus_cnt 2
                MagicMock(scalar=MagicMock(return_value=0)),  # balance_cnt 2
                MagicMock(scalar_one_or_none=MagicMock(return_value=None)),  # AdvPayment 2
                MagicMock(scalar=MagicMock(return_value=None)),  # unlock 2
            ]

            # Настраиваем pricer для каждого кабинета
            mock_pricer.get_price_for_day_for_shop.side_effect = [75.0, 80.0]

            await process_payment_for_advs(current_date=current_date, pricer=mock_pricer)

            mock_get_active_cabinets_with_data.assert_called_once_with(mock_session)
            assert mock_pricer.get_price_for_day_for_shop.call_count == 2
            mock_pricer.get_price_for_day_for_shop.assert_any_call(str(mock_wb_cabinet.shop_id))
            mock_pricer.get_price_for_day_for_shop.assert_any_call(str(mock_wb_cabinet_2.shop_id))

            # Проверяем добавления для первого кабинета (бонусы)
            added_bonus_payment = mock_session.add.call_args_list[0].args[0]
            assert added_bonus_payment.wb_cabinet_id == mock_wb_cabinet.id
            assert added_bonus_payment.amount == pytest.approx(-75.0, abs=1e-2)
            assert added_bonus_payment.description == f"Ежедневное списание за 1 кампаний, дата: {current_date}"
            assert added_bonus_payment.operation_type == "auto_subtract"
            assert isinstance(added_bonus_payment.transaction_date_time, datetime.datetime)

            # Проверяем AdvPayment для первого кабинета
            added_adv_payment_1 = mock_session.add.call_args_list[1].args[0]
            assert added_adv_payment_1.date == current_date
            assert added_adv_payment_1.amount == 75.0
            assert added_adv_payment_1.adv_setting_id == mock_adv_setting.id

            # Проверяем добавления для второго кабинета (баланс)
            added_balance_payment = mock_session.add.call_args_list[2].args[0]
            assert added_balance_payment.wb_cabinet_id == mock_wb_cabinet_2.id
            assert added_balance_payment.amount == pytest.approx(-80.0, abs=1e-2)
            assert added_balance_payment.description == f"Ежедневное списание за 1 кампаний, дата: {current_date}"
            assert isinstance(added_balance_payment.transaction_date_time, datetime.datetime)

            # Проверяем AdvPayment для второго кабинета
            added_adv_payment_2 = mock_session.add.call_args_list[3].args[0]
            assert added_adv_payment_2.date == current_date
            assert added_adv_payment_2.amount == 80.0
            assert added_adv_payment_2.adv_setting_id == adv_setting_2.id
            assert mock_session.add.call_count == 4  # 2 платежа кабинета + 2 AdvPayment

            mock_session.commit.assert_called_once()
            mock_session.rollback.assert_not_called()
            assert mock_redis_manager.set_billing_process_for_day.call_count == 2
            mock_redis_manager.set_billing_process_for_day.assert_any_call(mock_wb_cabinet.id, current_date)
            mock_redis_manager.set_billing_process_for_day.assert_any_call(mock_wb_cabinet_2.id, current_date)


@pytest.mark.asyncio
@patch("app.modules.billing.billing.sm", new_callable=MagicMock)
async def test_process_payment_for_advs_race_condition(
    mock_sm, mock_adv_setting, mock_wb_cabinet, mock_pricer, mock_redis_manager
):
    current_date = datetime.date(2023, 1, 1)
    mock_session = AsyncMock(spec=AsyncSession)
    mock_sm.return_value.__aenter__.return_value = mock_session
    mock_sm.return_value.__aexit__.return_value = False

    mock_adv_setting.wb_cabinet_id = mock_wb_cabinet.id
    mock_adv_setting.bot_active = True
    mock_wb_cabinet.adv_settings = [mock_adv_setting]
    mock_wb_cabinet.calculated_bonus = 100.0
    mock_pricer.get_price_for_day_for_shop.return_value = 75.0

    with patch(
        "app.modules.billing.billing.get_active_cabinets_with_data",
        new_callable=AsyncMock,
    ) as mock_get_active_cabinets_with_data:
        mock_get_active_cabinets_with_data.return_value = [mock_wb_cabinet]

        with patch("app.modules.billing.billing.redis_manager", new=mock_redis_manager):
            # Для первого вызова: advisory lock, затем обработка, затем set_billing_process_for_day
            # Для второго вызова: advisory lock, затем get_billing_process_for_day вернет True
            mock_redis_manager.get_billing_process_for_day.side_effect = [
                False,  # Первый вызов: еще не обработано
                True,  # Второй вызов: уже обработано
            ]

            mock_session.execute.side_effect = [
                MagicMock(scalar=MagicMock(return_value=0)),  # lock 1
                MagicMock(scalar=MagicMock(return_value=0)),  # bonus_cnt 1
                MagicMock(scalar=MagicMock(return_value=0)),  # balance_cnt 1
                MagicMock(scalar_one_or_none=MagicMock(return_value=None)),  # AdvPayment 1
                MagicMock(scalar=MagicMock(return_value=None)),  # unlock 1
                MagicMock(scalar=MagicMock(return_value=0)),  # lock 2
                MagicMock(scalar=MagicMock(return_value=None)),  # unlock 2
            ]

            # Запускаем две функции параллельно
            results = await asyncio.gather(
                process_payment_for_advs(current_date=current_date, pricer=mock_pricer),
                process_payment_for_advs(current_date=current_date, pricer=mock_pricer),
                return_exceptions=True,
            )

            # Проверяем, что оба вызова завершились успешно (без исключений)
            for res in results:
                assert res is None or not isinstance(res, Exception)

            # Проверяем, что get_active_cabinets_with_data был вызван дважды
            assert mock_get_active_cabinets_with_data.call_count == 2
            mock_get_active_cabinets_with_data.assert_any_call(mock_session)

            # Проверяем, что RedisManager.get_billing_process_for_day был вызван дважды
            assert mock_redis_manager.get_billing_process_for_day.call_count == 2
            mock_redis_manager.get_billing_process_for_day.assert_any_call(mock_wb_cabinet.id, current_date)

            # Проверяем, что Pricer был вызван только один раз (первым успешным вызовом)
            mock_pricer.get_price_for_day_for_shop.assert_called_once_with(str(mock_wb_cabinet.shop_id))

            # Проверяем, что добавление платежей произошло только один раз
            assert mock_session.add.call_count == 2  # WBBonusPayment + AdvPayment

            # Проверяем, что commit был вызван дважды (каждый _aexit_ вызывает commit)
            assert mock_session.commit.call_count == 2
            mock_session.rollback.assert_not_called()

            # Проверяем, что set_billing_process_for_day был вызван только один раз (первым успешным вызовом)
            mock_redis_manager.set_billing_process_for_day.assert_called_once_with(mock_wb_cabinet.id, current_date)
