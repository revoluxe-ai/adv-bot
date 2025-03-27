import pytest
from datetime import date, timedelta
from sqlalchemy import select
from tests.mocks import MockAdvPayment as AdvPayment, MockWBCabinet as WBCabinet, MockAdvSetting as AdvSetting, MockUser as User
from app.modules.payment_compensation.compensator import PaymentCompensator
from app.utils.db.session_maker import get_async_session_maker


@pytest.fixture
async def test_data(session):
    """Создает тестовые данные для проверки компенсации платежей"""
    # Создаем тестового пользователя
    user = User(
        id=1,
        user_telegram_id=123456789,
        username="test_user"
    )
    session.add(user)
    await session.flush()

    # Создаем тестовый кабинет WB
    cabinet = WBCabinet(
        id=1,
        shop_id="test_shop_123",
        balance=1000.0,
        bonus=0.0,
        active=True
    )
    session.add(cabinet)
    await session.flush()

    # Создаем тестовую настройку рекламы
    adv_setting = AdvSetting(
        id=1,
        adv_id=1,
        name="Test Campaign",
        wb_cabinet_id=cabinet.id,
        active_status="active",
        bot_active=False,
        nmids=[12345],
        pass_days=30,
        boost=1,
        type=8,
        max_cpc=100,
        min_views_for_ml_predict=0,
        parsing_active=False,
        bidder_active=False,
        min_block_position=0,
        clusters_mode=True,
        target_ctr_mode=False,
        hide_small_query_keywords=0,
        target_ctr_mode_strategy="forward",
        new_auto_min_ctr_mode=True,
        reset_place=True,
        bidder_step=0.5,
        exponent_predict_ctr=3,
        auction_boost_all_phrase_mode=False,
        bidder_for_auto=True
    )
    session.add(adv_setting)
    await session.flush()

    # Создаем тестовые платежи без amount
    start_date = date(2025, 3, 25)
    end_date = date.today()
    
    payments = []
    current_date = start_date
    while current_date <= end_date:
        payment = AdvPayment(
            wb_cabinet_id=cabinet.id,
            adv_setting_id=adv_setting.id,
            date=current_date,
            amount=None,
            type=None,
            user_id=user.id
        )
        payments.append(payment)
        current_date += timedelta(days=1)
    
    for payment in payments:
        session.add(payment)
    
    await session.commit()
    return {"cabinet": cabinet, "adv_setting": adv_setting, "user": user, "payments": payments}


@pytest.mark.asyncio
async def test_payment_compensation_main(test_data):
    """Тест основного метода компенсации платежей"""
    cabinet_id = test_data["cabinet"].id
    adv_setting_id = test_data["adv_setting"].id
    
    # Запускаем компенсацию
    compensator = PaymentCompensator()
    await compensator.main()
    
    async with get_async_session_maker() as session:
        # Проверяем, что созданы компенсационные платежи
        query = select(AdvPayment).where(
            AdvPayment.wb_cabinet_id == cabinet_id,
            AdvPayment.adv_setting_id == adv_setting_id,
            AdvPayment.amount.isnot(None),
            AdvPayment.type == 'compensation'
        )
        result = await session.execute(query)
        compensation_payments = result.scalars().all()
        
        assert len(compensation_payments) > 0
        
        # Проверяем, что бонус кабинета был обновлен
        cabinet = await session.get(WBCabinet, cabinet_id)
        assert cabinet.bonus > 0


@pytest.mark.asyncio
async def test_payment_compensation_date_range(test_data):
    """Тест генерации диапазона дат"""
    compensator = PaymentCompensator()
    start_date = date(2025, 3, 25)
    end_date = date(2025, 3, 27)
    
    dates = list(compensator._date_range(start_date, end_date))
    assert len(dates) == 3
    assert dates[0] == start_date
    assert dates[-1] == end_date


@pytest.mark.asyncio
async def test_get_payments_by_cabinet_for_date(test_data):
    """Тест получения платежей по кабинету за определенную дату"""
    compensator = PaymentCompensator()
    cabinet_id = test_data["cabinet"].id
    test_date = date(2025, 3, 25)
    
    async with get_async_session_maker() as session:
        compensator.session = session
        payments = await compensator._get_payments_by_cabinet_for_date(test_date)
        
        assert cabinet_id in payments
        assert len(payments[cabinet_id]) > 0
        assert all(payment.amount is None for payment in payments[cabinet_id])


@pytest.mark.asyncio
async def test_calculate_over_payments(test_data):
    """Тест расчета суммы излишних платежей"""
    compensator = PaymentCompensator()
    payments = test_data["payments"]
    
    over_payments_sum = await compensator._calculate_over_payments(payments)
    assert over_payments_sum > 0


@pytest.mark.asyncio
async def test_compensate_cabinet(test_data):
    """Тест обновления бонуса кабинета"""
    compensator = PaymentCompensator()
    cabinet_id = test_data["cabinet"].id
    compensation_sum = 100.0
    
    async with get_async_session_maker() as session:
        compensator.session = session
        await compensator._compensate_cabinet(cabinet_id, compensation_sum)
        
        cabinet = await session.get(WBCabinet, cabinet_id)
        assert cabinet.bonus == compensation_sum


@pytest.mark.asyncio
async def test_create_compensation_payment(test_data):
    """Тест создания компенсационного платежа"""
    compensator = PaymentCompensator()
    cabinet_id = test_data["cabinet"].id
    adv_setting_id = test_data["adv_setting"].id
    user_id = test_data["user"].id
    compensation_sum = 100.0
    comp_date = date(2025, 3, 25)
    
    async with get_async_session_maker() as session:
        compensator.session = session
        success = await compensator._create_compensation_payment(
            cabinet_id, adv_setting_id, comp_date, compensation_sum, user_id
        )
        
        assert success
        
        # Проверяем, что платеж был создан
        query = select(AdvPayment).where(
            AdvPayment.wb_cabinet_id == cabinet_id,
            AdvPayment.adv_setting_id == adv_setting_id,
            AdvPayment.date == comp_date,
            AdvPayment.amount == compensation_sum,
            AdvPayment.type == 'compensation',
            AdvPayment.user_id == user_id
        )
        result = await session.execute(query)
        payment = result.scalar_one_or_none()
        
        assert payment is not None 