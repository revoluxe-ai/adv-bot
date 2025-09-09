import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing.billing import (
    PaymentType,
    calculate_daily_price_for_adv,
    check_adv_payment,
    commit_operations,
    create_adv_payment,
    create_balance_payment,
    create_bonus_payment,
    deactivate_adv_setting,
    determine_payment_method,
    get_active_adv_settings,
    get_count_advs_for_wb_cabinet,
    process_payment_for_advs,
    process_payment_operations,
    process_single_adv_payment,
)
from app.modules.billing.pricer import Pricer
from app.modules.common_slaves.wildberries.models import AdvSetting, WBBalancePayment, WBBonusPayment
from app.modules.wb_adv_updater.models import AdvPayment


@pytest.fixture
def mock_adv_setting():
    adv_setting = MagicMock(spec=AdvSetting)
    adv_setting.id = 1
    adv_setting.adv_id = "test_adv_id_1"
    adv_setting.bot_active = True
    adv_setting.auto_update_white_list = True
    adv_setting.auto_update_target_place = True
    adv_setting.payments = []
    adv_setting.wb_cabinet = None  # Инициализируем None, будет установлено mock_wb_cabinet
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
    return wb_cabinet


@pytest.fixture
def mock_pricer():
    pricer = AsyncMock(spec=Pricer)
    pricer.get_price_for_day_for_shop.return_value = 100.0
    return pricer


@pytest.fixture
def mock_session():
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value.unique.return_value.scalars.return_value.all.return_value = []
    return session


def test_get_count_advs_for_wb_cabinet(mock_adv_setting, mock_wb_cabinet):
    mock_adv_setting.wb_cabinet = mock_wb_cabinet

    # Тест: один adv_setting для кабинета
    adv_settings = [mock_adv_setting]
    result = get_count_advs_for_wb_cabinet(mock_wb_cabinet, adv_settings)
    assert result == 1

    # Тест: несколько adv_settings, некоторые принадлежат другому кабинету
    adv_setting_2 = MagicMock(spec=AdvSetting)
    adv_setting_2.wb_cabinet = MagicMock()
    adv_setting_2.wb_cabinet.id = 101

    adv_setting_3 = MagicMock(spec=AdvSetting)
    adv_setting_3.wb_cabinet = mock_wb_cabinet  # Этот относится к тому же кабинету

    adv_settings = [mock_adv_setting, adv_setting_2, adv_setting_3]
    result = get_count_advs_for_wb_cabinet(mock_wb_cabinet, adv_settings)
    assert result == 2  # mock_adv_setting и adv_setting_3

    # Тест: пустой список adv_settings
    result = get_count_advs_for_wb_cabinet(mock_wb_cabinet, [])
    assert result == 0

    # Тест: ни один adv_setting не принадлежит кабинету
    adv_setting_4 = MagicMock(spec=AdvSetting)
    adv_setting_4.wb_cabinet = MagicMock()
    adv_setting_4.wb_cabinet.id = 102
    adv_settings = [adv_setting_4, adv_setting_2]
    result = get_count_advs_for_wb_cabinet(mock_wb_cabinet, adv_settings)
    assert result == 0


@pytest.mark.asyncio
async def test_check_adv_payment(mock_session, mock_adv_setting):
    current_date = datetime.date.today()

    # Тест: платеж существует
    mock_session.execute.reset_mock()
    mock_session.execute.return_value.scalar.return_value = MagicMock(spec=AdvPayment)
    result = await check_adv_payment(mock_session, mock_adv_setting, current_date)
    assert result is True
    mock_session.execute.assert_called_once()

    # Тест: платеж не существует
    mock_session.execute.reset_mock()
    mock_session.execute.return_value.scalar.return_value = None
    result = await check_adv_payment(mock_session, mock_adv_setting, current_date)
    assert result is False
    mock_session.execute.assert_called_once()

    # Тест: ошибка при выполнении запроса
    mock_session.execute.reset_mock()
    mock_session.execute.side_effect = Exception("DB Error")
    result = await check_adv_payment(mock_session, mock_adv_setting, current_date)
    assert result is False
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_active_adv_settings(mock_session, mock_adv_setting):
    # Создаем мок для результата execute
    mock_execute_result = MagicMock()
    mock_execute_result.unique.return_value.scalars.return_value.all.return_value = [mock_adv_setting]

    # Тест: возвращает активные настройки
    mock_session.execute.return_value = mock_execute_result
    result = await get_active_adv_settings(mock_session)
    assert result == [mock_adv_setting]
    mock_session.execute.assert_called_once()

    # Тест: возвращает пустой список, если нет активных настроек
    mock_session.execute.reset_mock()
    mock_execute_result.unique.return_value.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_execute_result
    result = await get_active_adv_settings(mock_session)
    assert result == []

    # Тест: обрабатывает исключения
    mock_session.execute.reset_mock()
    mock_session.execute.side_effect = Exception("DB Error")
    with pytest.raises(Exception, match="DB Error"):
        await get_active_adv_settings(mock_session)


@pytest.mark.asyncio
async def test_calculate_daily_price_for_adv(mock_adv_setting, mock_wb_cabinet, mock_pricer):
    mock_adv_setting.wb_cabinet = mock_wb_cabinet
    adv_settings = [mock_adv_setting]

    # Тест: успешный расчет
    mock_pricer.get_price_for_day_for_shop.return_value = 100.0
    result = await calculate_daily_price_for_adv(mock_adv_setting, adv_settings, mock_pricer)
    assert result == 100.0
    mock_pricer.get_price_for_day_for_shop.assert_called_once_with(str(mock_wb_cabinet.shop_id))

    # Тест: отсутствие wb_cabinet
    original_wb_cabinet = mock_adv_setting.wb_cabinet  # Сохраняем для восстановления
    mock_adv_setting.wb_cabinet = None
    with pytest.raises(ValueError, match=f"Отсутствует wb_cabinet для adv_setting {mock_adv_setting.id}"):
        await calculate_daily_price_for_adv(mock_adv_setting, adv_settings, mock_pricer)
    mock_adv_setting.wb_cabinet = original_wb_cabinet  # Восстанавливаем для следующих тестов

    # Тест: некорректный shop_id
    original_shop_id = mock_wb_cabinet.shop_id
    mock_wb_cabinet.shop_id = None
    with pytest.raises(ValueError, match=f"Некорректный shop_id для кабинета {mock_wb_cabinet.id}"):
        await calculate_daily_price_for_adv(mock_adv_setting, adv_settings, mock_pricer)
    mock_wb_cabinet.shop_id = original_shop_id  # Восстанавливаем

    # Тест: отрицательная цена от pricer
    mock_pricer.get_price_for_day_for_shop.return_value = -10.0
    with pytest.raises(ValueError, match="Отрицательная цена для магазина"):
        await calculate_daily_price_for_adv(mock_adv_setting, adv_settings, mock_pricer)

    # Тест: 0 активных кампаний
    mock_pricer.get_price_for_day_for_shop.return_value = 100.0
    adv_setting_other_cabinet = MagicMock(spec=AdvSetting)
    adv_setting_other_cabinet.wb_cabinet = MagicMock()
    adv_setting_other_cabinet.wb_cabinet.id = 999
    result = await calculate_daily_price_for_adv(mock_adv_setting, [adv_setting_other_cabinet], mock_pricer)
    assert result == 0.0

    # Тест: отрицательная дневная цена (невозможный сценарий, но проверяем)
    with patch(
        "app.modules.billing.billing.get_count_advs_for_wb_cabinet", return_value=-1
    ):  # Мокаем для создания ситуации
        mock_pricer.get_price_for_day_for_shop.return_value = 100.0
        with pytest.raises(ValueError, match="Отрицательная дневная цена"):
            await calculate_daily_price_for_adv(mock_adv_setting, adv_settings, mock_pricer)

    # Тест: обработка общей ошибки
    mock_pricer.get_price_for_day_for_shop.side_effect = Exception("Pricer Error")
    with pytest.raises(Exception, match="Pricer Error"):
        await calculate_daily_price_for_adv(mock_adv_setting, adv_settings, mock_pricer)


def test_determine_payment_method(mock_wb_cabinet):
    # Тест: оплата бонусами
    mock_wb_cabinet.calculated_bonus = 100.0
    mock_wb_cabinet.calculated_balance = 50.0
    assert determine_payment_method(mock_wb_cabinet, 75.0) == PaymentType.BONUS

    # Тест: оплата балансом
    mock_wb_cabinet.calculated_bonus = 50.0
    mock_wb_cabinet.calculated_balance = 100.0
    assert determine_payment_method(mock_wb_cabinet, 75.0) == PaymentType.BALANCE

    # Тест: недостаточно средств
    mock_wb_cabinet.calculated_bonus = 10.0
    mock_wb_cabinet.calculated_balance = 20.0
    assert determine_payment_method(mock_wb_cabinet, 75.0) == PaymentType.INSUFFICIENT_FUNDS

    # Тест: требуемая сумма равна бонусам
    mock_wb_cabinet.calculated_bonus = 75.0
    mock_wb_cabinet.calculated_balance = 50.0
    assert determine_payment_method(mock_wb_cabinet, 75.0) == PaymentType.BONUS

    # Тест: требуемая сумма равна балансу (после бонусов)
    mock_wb_cabinet.calculated_bonus = 0.0
    mock_wb_cabinet.calculated_balance = 75.0
    assert determine_payment_method(mock_wb_cabinet, 75.0) == PaymentType.BALANCE

    # Тест: отрицательные балансы должны быть обработаны как 0
    mock_wb_cabinet.calculated_bonus = -10.0
    mock_wb_cabinet.calculated_balance = -20.0
    assert determine_payment_method(mock_wb_cabinet, 1.0) == PaymentType.INSUFFICIENT_FUNDS

    # Тест: некорректная сумма платежа (отрицательная)
    with pytest.raises(ValueError, match="Некорректная сумма платежа"):
        determine_payment_method(mock_wb_cabinet, -10.0)

    # Тест: некорректная сумма платежа (нулевая)
    with pytest.raises(ValueError, match="Некорректная сумма платежа"):
        determine_payment_method(mock_wb_cabinet, 0.0)


def test_create_adv_payment():
    current_date = datetime.date.today()
    amount = 100.0

    # Тест: успешное создание
    payment = create_adv_payment(current_date, amount)
    assert isinstance(payment, AdvPayment)
    assert payment.date == current_date
    assert payment.amount == amount

    # Тест: некорректная сумма (отрицательная)
    with pytest.raises(ValueError, match="Некорректная сумма платежа"):
        create_adv_payment(current_date, -10.0)

    # Тест: некорректная сумма (нулевая)
    with pytest.raises(ValueError, match="Некорректная сумма платежа"):
        create_adv_payment(current_date, 0.0)


def test_create_bonus_payment():
    wb_cabinet_id = 100
    amount = 50.0
    adv_id = 1

    # Тест: успешное создание
    payment = create_bonus_payment(wb_cabinet_id, amount, adv_id)
    assert isinstance(payment, WBBonusPayment)
    assert payment.wb_cabinet_id == wb_cabinet_id
    assert payment.amount == -amount  # Списание, поэтому отрицательное
    assert payment.description == f"Списание за рекламную кампанию {adv_id}"

    # Тест: некорректная сумма (отрицательная)
    with pytest.raises(ValueError, match="Некорректная сумма бонусного платежа"):
        create_bonus_payment(wb_cabinet_id, -10.0, adv_id)

    # Тест: некорректная сумма (нулевая)
    with pytest.raises(ValueError, match="Некорректная сумма бонусного платежа"):
        create_bonus_payment(wb_cabinet_id, 0.0, adv_id)


def test_create_balance_payment():
    wb_cabinet_id = 100
    amount = 50.0
    adv_id = "test_adv_id_1"

    # Тест: успешное создание
    payment = create_balance_payment(wb_cabinet_id, amount, adv_id)
    assert isinstance(payment, WBBalancePayment)
    assert payment.wb_cabinet_id == wb_cabinet_id
    assert payment.amount == -amount  # Списание, поэтому отрицательное
    assert payment.description == f"Списание за рекламную кампанию {adv_id}"

    # Тест: некорректная сумма (отрицательная)
    with pytest.raises(ValueError, match="Некорректная сумма балансного платежа"):
        create_balance_payment(wb_cabinet_id, -10.0, adv_id)

    # Тест: некорректная сумма (нулевая)
    with pytest.raises(ValueError, match="Некорректная сумма балансного платежа"):
        create_balance_payment(wb_cabinet_id, 0.0, adv_id)


def test_deactivate_adv_setting(mock_adv_setting):
    # Тест: успешная деактивация
    deactivate_adv_setting(mock_adv_setting)
    assert mock_adv_setting.bot_active is False
    assert mock_adv_setting.auto_update_white_list is False
    assert mock_adv_setting.auto_update_target_place is False

    # Тест: повторная деактивация не должна вызывать ошибок
    deactivate_adv_setting(mock_adv_setting)
    assert mock_adv_setting.bot_active is False


@pytest.mark.asyncio
async def test_process_single_adv_payment(mock_session, mock_adv_setting, mock_wb_cabinet):
    current_date = datetime.date.today()
    daily_price = 75.0
    mock_adv_setting.wb_cabinet = mock_wb_cabinet

    # Тест: платеж уже существует
    with patch("app.modules.billing.billing.check_adv_payment", new_callable=AsyncMock) as mock_check_adv_payment_1:
        mock_check_adv_payment_1.return_value = True
        result = await process_single_adv_payment(mock_session, mock_adv_setting, current_date, daily_price)
        assert result is None
        mock_check_adv_payment_1.assert_called_once_with(mock_session, mock_adv_setting, current_date)

    # Тест: нулевая или отрицательная цена
    with patch("app.modules.billing.billing.check_adv_payment", new_callable=AsyncMock) as mock_check_adv_payment_2:
        mock_check_adv_payment_2.return_value = False
        result = await process_single_adv_payment(mock_session, mock_adv_setting, current_date, 0.0)
        assert result is None

    # Тест: оплата бонусами
    mock_adv_setting.payments = []
    mock_wb_cabinet.calculated_bonus = daily_price
    mock_wb_cabinet.calculated_balance = 0.0
    with (
        patch("app.modules.billing.billing.check_adv_payment", new_callable=AsyncMock) as mock_check_adv_payment_3,
        patch(
            "app.modules.billing.billing.determine_payment_method", return_value=PaymentType.BONUS
        ) as mock_determine_payment_method_1,
        patch(
            "app.modules.billing.billing.create_adv_payment", return_value=MagicMock(spec=AdvPayment)
        ) as mock_create_adv_payment_1,
        patch(
            "app.modules.billing.billing.create_bonus_payment", return_value=MagicMock(spec=WBBonusPayment)
        ) as mock_create_bonus_payment_1,
    ):
        mock_check_adv_payment_3.return_value = False

        operation = await process_single_adv_payment(mock_session, mock_adv_setting, current_date, daily_price)

        mock_determine_payment_method_1.assert_called_once_with(mock_wb_cabinet, daily_price)
        mock_create_adv_payment_1.assert_called_once_with(current_date, daily_price)
        mock_create_bonus_payment_1.assert_called_once_with(mock_wb_cabinet.id, daily_price, mock_adv_setting.adv_id)
        mock_session.add.assert_called_once_with(mock_create_bonus_payment_1.return_value)
        assert len(mock_adv_setting.payments) == 1
        assert operation.operation_type == PaymentType.BONUS
        assert operation.adv_setting == mock_adv_setting
        assert operation.amount == daily_price

    # Тест: оплата балансом
    mock_adv_setting.payments = []
    mock_session.add.reset_mock()
    mock_wb_cabinet.calculated_bonus = 0.0
    mock_wb_cabinet.calculated_balance = daily_price
    with (
        patch("app.modules.billing.billing.check_adv_payment", new_callable=AsyncMock) as mock_check_adv_payment_4,
        patch(
            "app.modules.billing.billing.determine_payment_method", return_value=PaymentType.BALANCE
        ) as mock_determine_payment_method_2,
        patch(
            "app.modules.billing.billing.create_adv_payment", return_value=MagicMock(spec=AdvPayment)
        ) as mock_create_adv_payment_2,
        patch(
            "app.modules.billing.billing.create_balance_payment", return_value=MagicMock(spec=WBBalancePayment)
        ) as mock_create_balance_payment_2,
    ):
        mock_check_adv_payment_4.return_value = False

        operation = await process_single_adv_payment(mock_session, mock_adv_setting, current_date, daily_price)

        mock_determine_payment_method_2.assert_called_once_with(mock_wb_cabinet, daily_price)
        mock_create_adv_payment_2.assert_called_once_with(current_date, daily_price)
        mock_create_balance_payment_2.assert_called_once_with(mock_wb_cabinet.id, daily_price, mock_adv_setting.adv_id)
        mock_session.add.assert_called_once_with(mock_create_balance_payment_2.return_value)
        assert len(mock_adv_setting.payments) == 1
        assert operation.operation_type == PaymentType.BALANCE
        assert operation.adv_setting == mock_adv_setting
        assert operation.amount == daily_price

    # Тест: недостаточно средств, деактивация
    mock_adv_setting.payments = []
    mock_session.add.reset_mock()
    mock_wb_cabinet.calculated_bonus = 0.0
    mock_wb_cabinet.calculated_balance = 0.0
    with (
        patch("app.modules.billing.billing.check_adv_payment", new_callable=AsyncMock) as mock_check_adv_payment_5,
        patch(
            "app.modules.billing.billing.determine_payment_method", return_value=PaymentType.INSUFFICIENT_FUNDS
        ) as mock_determine_payment_method_3,
        patch("app.modules.billing.billing.deactivate_adv_setting") as mock_deactivate_adv_setting_1,
    ):
        mock_check_adv_payment_5.return_value = False

        operation = await process_single_adv_payment(mock_session, mock_adv_setting, current_date, daily_price)

        mock_determine_payment_method_3.assert_called_once_with(mock_wb_cabinet, daily_price)
        mock_deactivate_adv_setting_1.assert_called_once_with(mock_adv_setting)
        assert mock_session.add.call_count == 0
        assert len(mock_adv_setting.payments) == 0
        assert operation.operation_type == PaymentType.INSUFFICIENT_FUNDS
        assert operation.adv_setting == mock_adv_setting
        assert operation.amount == 0  # Деактивация обычно с нулевой суммой

    # Тест: обработка исключения
    with patch("app.modules.billing.billing.check_adv_payment", new_callable=AsyncMock) as mock_check_adv_payment_6:
        mock_check_adv_payment_6.side_effect = Exception("Test Error")
        with pytest.raises(Exception, match="Test Error"):
            await process_single_adv_payment(mock_session, mock_adv_setting, current_date, daily_price)


@pytest.mark.asyncio
async def test_process_payment_operations(mock_session, mock_adv_setting, mock_pricer):
    current_date = datetime.date.today()

    # Тест: успешная обработка нескольких настроек
    adv_setting_2 = MagicMock(spec=AdvSetting, id=2, adv_id="test_adv_id_2")
    adv_setting_2.wb_cabinet = MagicMock(id=200, shop_id=456, calculated_bonus=200.0, calculated_balance=100.0)
    adv_settings = [mock_adv_setting, adv_setting_2]
    mock_adv_setting.wb_cabinet = mock_wb_cabinet  # Привязываем к первому adv_setting

    with (
        patch(
            "app.modules.billing.billing.check_adv_payment", new_callable=AsyncMock
        ) as mock_check_adv_payment_scenario1,
        patch(
            "app.modules.billing.billing.calculate_daily_price_for_adv", new_callable=AsyncMock
        ) as mock_calculate_daily_price_for_adv_scenario1,
        patch(
            "app.modules.billing.billing.process_single_adv_payment", new_callable=AsyncMock
        ) as mock_process_single_adv_payment_scenario1,
    ):
        mock_check_adv_payment_scenario1.side_effect = [False, False]
        mock_calculate_daily_price_for_adv_scenario1.side_effect = [100.0, 50.0]
        mock_process_single_adv_payment_scenario1.side_effect = [
            MagicMock(operation_type=PaymentType.BONUS, adv_setting=mock_adv_setting, amount=100.0),
            MagicMock(operation_type=PaymentType.BALANCE, adv_setting=adv_setting_2, amount=50.0),
        ]

        operations = await process_payment_operations(mock_session, adv_settings, current_date, mock_pricer)

        assert len(operations) == 2
        assert operations[0].operation_type == PaymentType.BONUS
        assert operations[1].operation_type == PaymentType.BALANCE

        assert mock_check_adv_payment_scenario1.call_count == 2
        mock_check_adv_payment_scenario1.assert_any_call(mock_session, mock_adv_setting, current_date)
        mock_check_adv_payment_scenario1.assert_any_call(mock_session, adv_setting_2, current_date)

        assert mock_calculate_daily_price_for_adv_scenario1.call_count == 2
        mock_calculate_daily_price_for_adv_scenario1.assert_any_call(mock_adv_setting, adv_settings, mock_pricer)
        mock_calculate_daily_price_for_adv_scenario1.assert_any_call(adv_setting_2, adv_settings, mock_pricer)

        assert mock_process_single_adv_payment_scenario1.call_count == 2
        mock_process_single_adv_payment_scenario1.assert_any_call(mock_session, mock_adv_setting, current_date, 100.0)
        mock_process_single_adv_payment_scenario1.assert_any_call(mock_session, adv_setting_2, current_date, 50.0)

    # Тест: пропуск уже оплаченных настроек
    # Сброс и повторная привязка для обеспечения чистоты состояния
    mock_adv_setting.wb_cabinet = mock_wb_cabinet
    adv_setting_2.wb_cabinet = MagicMock(id=200, shop_id=456, calculated_bonus=200.0, calculated_balance=100.0)

    with (
        patch(
            "app.modules.billing.billing.check_adv_payment", new_callable=AsyncMock
        ) as mock_check_adv_payment_scenario2,
        patch(
            "app.modules.billing.billing.calculate_daily_price_for_adv", new_callable=AsyncMock
        ) as mock_calculate_daily_price_for_adv_scenario2,
        patch(
            "app.modules.billing.billing.process_single_adv_payment", new_callable=AsyncMock
        ) as mock_process_single_adv_payment_scenario2,
    ):
        mock_check_adv_payment_scenario2.side_effect = [True, False]  # Первая уже оплачена
        mock_calculate_daily_price_for_adv_scenario2.return_value = 50.0
        mock_process_single_adv_payment_scenario2.return_value = MagicMock(
            operation_type=PaymentType.BALANCE, adv_setting=adv_setting_2, amount=50.0
        )

        operations = await process_payment_operations(mock_session, adv_settings, current_date, mock_pricer)

        assert len(operations) == 1
        assert operations[0].operation_type == PaymentType.BALANCE
        assert mock_check_adv_payment_scenario2.call_count == 2
        assert mock_calculate_daily_price_for_adv_scenario2.call_count == 1  # Вызвана только для adv_setting_2
        assert mock_process_single_adv_payment_scenario2.call_count == 1  # Вызвана только для adv_setting_2

    # Тест: пропуск с нулевой ценой
    # Сброс и повторная привязка для обеспечения чистоты состояния
    mock_adv_setting.wb_cabinet = mock_wb_cabinet
    adv_setting_2.wb_cabinet = MagicMock(id=200, shop_id=456, calculated_bonus=200.0, calculated_balance=100.0)

    with (
        patch(
            "app.modules.billing.billing.check_adv_payment", new_callable=AsyncMock
        ) as mock_check_adv_payment_scenario3,
        patch(
            "app.modules.billing.billing.calculate_daily_price_for_adv", new_callable=AsyncMock
        ) as mock_calculate_daily_price_for_adv_scenario3,
        patch(
            "app.modules.billing.billing.process_single_adv_payment", new_callable=AsyncMock
        ) as mock_process_single_adv_payment_scenario3,
    ):
        mock_check_adv_payment_scenario3.side_effect = [False, False]
        mock_calculate_daily_price_for_adv_scenario3.side_effect = [0.0, 50.0]  # Первая с нулевой ценой
        mock_process_single_adv_payment_scenario3.return_value = MagicMock(
            operation_type=PaymentType.BALANCE, adv_setting=adv_setting_2, amount=50.0
        )

        operations = await process_payment_operations(mock_session, adv_settings, current_date, mock_pricer)

        assert len(operations) == 1
        assert operations[0].operation_type == PaymentType.BALANCE
        assert mock_check_adv_payment_scenario3.call_count == 2
        assert mock_calculate_daily_price_for_adv_scenario3.call_count == 2
        assert mock_process_single_adv_payment_scenario3.call_count == 1  # Вызвана только для adv_setting_2

    # Тест: обработка исключения в `calculate_daily_price_for_adv`
    # Сброс и повторная привязка для обеспечения чистоты состояния
    mock_adv_setting.wb_cabinet = mock_wb_cabinet
    adv_setting_2.wb_cabinet = MagicMock(id=200, shop_id=456, calculated_bonus=200.0, calculated_balance=100.0)

    with (
        patch(
            "app.modules.billing.billing.check_adv_payment", new_callable=AsyncMock
        ) as mock_check_adv_payment_scenario4,
        patch(
            "app.modules.billing.billing.calculate_daily_price_for_adv", new_callable=AsyncMock
        ) as mock_calculate_daily_price_for_adv_scenario4,
        patch(
            "app.modules.billing.billing.process_single_adv_payment", new_callable=AsyncMock
        ) as mock_process_single_adv_payment_scenario4,
    ):
        mock_check_adv_payment_scenario4.side_effect = [False, False]
        mock_calculate_daily_price_for_adv_scenario4.side_effect = [Exception("Calc Error"), 50.0]
        mock_process_single_adv_payment_scenario4.return_value = MagicMock(
            operation_type=PaymentType.BALANCE, adv_setting=adv_setting_2, amount=50.0
        )

        operations = await process_payment_operations(mock_session, adv_settings, current_date, mock_pricer)

        assert len(operations) == 1
        assert operations[0].operation_type == PaymentType.BALANCE
        assert mock_check_adv_payment_scenario4.call_count == 2
        assert mock_calculate_daily_price_for_adv_scenario4.call_count == 2
        assert mock_process_single_adv_payment_scenario4.call_count == 1

    # Тест: обработка исключения в `process_single_adv_payment`
    # Сброс и повторная привязка для обеспечения чистоты состояния
    mock_adv_setting.wb_cabinet = mock_wb_cabinet
    adv_setting_2.wb_cabinet = MagicMock(id=200, shop_id=456, calculated_bonus=200.0, calculated_balance=100.0)

    with (
        patch(
            "app.modules.billing.billing.check_adv_payment", new_callable=AsyncMock
        ) as mock_check_adv_payment_scenario5,
        patch(
            "app.modules.billing.billing.calculate_daily_price_for_adv", new_callable=AsyncMock
        ) as mock_calculate_daily_price_for_adv_scenario5,
        patch(
            "app.modules.billing.billing.process_single_adv_payment", new_callable=AsyncMock
        ) as mock_process_single_adv_payment_scenario5,
    ):
        mock_check_adv_payment_scenario5.side_effect = [False, False]
        mock_calculate_daily_price_for_adv_scenario5.side_effect = [100.0, 50.0]
        mock_process_single_adv_payment_scenario5.side_effect = [Exception("Single Process Error"), None]

        operations = await process_payment_operations(mock_session, adv_settings, current_date, mock_pricer)

        assert len(operations) == 0  # Ни одна операция не была добавлена успешно
        assert mock_check_adv_payment_scenario5.call_count == 2
        assert mock_calculate_daily_price_for_adv_scenario5.call_count == 2
        assert mock_process_single_adv_payment_scenario5.call_count == 2


@pytest.mark.asyncio
async def test_commit_operations(mock_session, mock_adv_setting):
    # Тест: успешный коммит операций
    operations = [
        MagicMock(operation_type=PaymentType.BONUS, adv_setting=mock_adv_setting, amount=100.0),
        MagicMock(operation_type=PaymentType.BALANCE, adv_setting=mock_adv_setting, amount=50.0),
    ]
    await commit_operations(mock_session, operations)
    mock_session.commit.assert_called_once()
    mock_session.rollback.assert_not_called()

    # Тест: пустой список операций
    mock_session.commit.reset_mock()
    mock_session.rollback.reset_mock()
    await commit_operations(mock_session, [])
    mock_session.commit.assert_not_called()
    mock_session.rollback.assert_not_called()

    # Тест: обработка исключения при коммите
    mock_session.commit.reset_mock()
    mock_session.rollback.reset_mock()
    mock_session.commit.side_effect = Exception("Commit Error")
    with pytest.raises(Exception, match="Commit Error"):
        await commit_operations(mock_session, operations)
    mock_session.commit.assert_called_once()
    mock_session.rollback.assert_called_once()


@pytest.mark.asyncio
@patch("app.modules.billing.billing.sm")
async def test_process_payment_for_advs(mock_sm, mock_adv_setting, mock_pricer, mock_wb_cabinet):
    mock_session = AsyncMock(spec=AsyncSession)
    mock_sm.return_value.__aenter__.return_value = mock_session
    mock_adv_setting.wb_cabinet = mock_wb_cabinet  # Привязываем к adv_setting

    # Тест: успешное выполнение без предоставления даты и Pricer
    with (
        patch(
            "app.modules.billing.billing.get_active_adv_settings", new_callable=AsyncMock
        ) as mock_get_active_adv_settings_scenario1,
        patch(
            "app.modules.billing.billing.process_payment_operations", new_callable=AsyncMock
        ) as mock_process_payment_operations_scenario1,
        patch(
            "app.modules.billing.billing.commit_operations", new_callable=AsyncMock
        ) as mock_commit_operations_scenario1,
        patch("app.modules.billing.billing.Pricer", return_value=mock_pricer),
    ):
        mock_get_active_adv_settings_scenario1.return_value = [mock_adv_setting]
        mock_process_payment_operations_scenario1.return_value = [
            MagicMock(operation_type=PaymentType.BONUS, adv_setting=mock_adv_setting, amount=100.0)
        ]

        await process_payment_for_advs()

        mock_get_active_adv_settings_scenario1.assert_called_once_with(mock_session)
        mock_process_payment_operations_scenario1.assert_called_once_with(
            mock_session, [mock_adv_setting], datetime.date.today(), mock_pricer
        )
        mock_commit_operations_scenario1.assert_called_once_with(
            mock_session, [MagicMock(operation_type=PaymentType.BONUS, adv_setting=mock_adv_setting, amount=100.0)]
        )
        mock_session.rollback.assert_not_called()

    # Тест: выполнение с предоставлением даты и Pricer
    custom_date = datetime.date(2023, 1, 1)
    custom_pricer = AsyncMock(spec=Pricer)

    with (
        patch(
            "app.modules.billing.billing.get_active_adv_settings", new_callable=AsyncMock
        ) as mock_get_active_adv_settings_scenario2,
        patch(
            "app.modules.billing.billing.process_payment_operations", new_callable=AsyncMock
        ) as mock_process_payment_operations_scenario2,
        patch(
            "app.modules.billing.billing.commit_operations", new_callable=AsyncMock
        ) as mock_commit_operations_scenario2,
    ):
        mock_get_active_adv_settings_scenario2.return_value = [mock_adv_setting]
        mock_process_payment_operations_scenario2.return_value = [
            MagicMock(operation_type=PaymentType.BONUS, adv_setting=mock_adv_setting, amount=100.0)
        ]

        await process_payment_for_advs(current_date=custom_date, pricer=custom_pricer)

        mock_get_active_adv_settings_scenario2.assert_called_once_with(mock_session)
        mock_process_payment_operations_scenario2.assert_called_once_with(
            mock_session, [mock_adv_setting], custom_date, custom_pricer
        )
        mock_commit_operations_scenario2.assert_called_once_with(
            mock_session, [MagicMock(operation_type=PaymentType.BONUS, adv_setting=mock_adv_setting, amount=100.0)]
        )
        mock_session.rollback.assert_not_called()

    # Тест: нет активных рекламных настроек
    with (
        patch(
            "app.modules.billing.billing.get_active_adv_settings", new_callable=AsyncMock
        ) as mock_get_active_adv_settings_scenario3,
        patch(
            "app.modules.billing.billing.process_payment_operations", new_callable=AsyncMock
        ) as mock_process_payment_operations_scenario3,
        patch(
            "app.modules.billing.billing.commit_operations", new_callable=AsyncMock
        ) as mock_commit_operations_scenario3,
    ):
        mock_get_active_adv_settings_scenario3.return_value = []

        await process_payment_for_advs()

        mock_get_active_adv_settings_scenario3.assert_called_once_with(mock_session)
        mock_process_payment_operations_scenario3.assert_not_called()
        mock_commit_operations_scenario3.assert_not_called()
        mock_session.rollback.assert_not_called()

    # Тест: нет операций для обработки
    with (
        patch(
            "app.modules.billing.billing.get_active_adv_settings", new_callable=AsyncMock
        ) as mock_get_active_adv_settings_scenario4,
        patch(
            "app.modules.billing.billing.process_payment_operations", new_callable=AsyncMock
        ) as mock_process_payment_operations_scenario4,
        patch(
            "app.modules.billing.billing.commit_operations", new_callable=AsyncMock
        ) as mock_commit_operations_scenario4,
    ):
        mock_get_active_adv_settings_scenario4.return_value = [mock_adv_setting]
        mock_process_payment_operations_scenario4.return_value = []

        await process_payment_for_advs()

        mock_get_active_adv_settings_scenario4.assert_called_once_with(mock_session)
        mock_process_payment_operations_scenario4.assert_called_once()
        mock_commit_operations_scenario4.assert_not_called()
        mock_session.rollback.assert_not_called()

    # Тест: обработка критической ошибки
    with patch(
        "app.modules.billing.billing.get_active_adv_settings", new_callable=AsyncMock
    ) as mock_get_active_adv_settings_scenario5:
        mock_get_active_adv_settings_scenario5.side_effect = Exception("Critical Error")

        with pytest.raises(Exception, match="Critical Error"):
            await process_payment_for_advs()

        mock_session.rollback.assert_called_once()
