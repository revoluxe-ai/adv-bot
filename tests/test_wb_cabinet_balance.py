import pytest
from datetime import datetime
from sqlalchemy import select
from tests.mocks import MockWBBalancePayment, MockWBBonusPayment
from app.client_bot.user_interface.views.messages import process_cabinet_balance_topup, confirm_cabinet_balance_topup
from tests.mocks import MockWBCabinet, MockUser, MockWBUserCabinet

@pytest.fixture
async def mock_wb_user_cabinet():
    return MockWBUserCabinet(
        id=1,
        wb_cabinet_id=1,
        user_id=1,
        name="Test Cabinet"
    )

@pytest.mark.asyncio
async def test_balance_payment_creation(test_async_db, mock_wb_cabinet):
    """Тест создания записи о пополнении баланса"""
    payment = MockWBBalancePayment(
        wb_cabinet_id=mock_wb_cabinet.id,
        amount=1000.0,
        description="Test payment",
        transaction_date_time=datetime.now()
    )
    async with test_async_db as session:
        session.add(payment)
        await session.commit()
        await session.refresh(payment)

    assert payment.id is not None
    assert payment.wb_cabinet_id == mock_wb_cabinet.id
    assert payment.amount == 1000.0
    assert payment.description == "Test payment"

@pytest.mark.asyncio
async def test_bonus_payment_creation(test_async_db, mock_wb_cabinet):
    """Тест создания записи о начислении бонусов"""
    payment = MockWBBonusPayment(
        wb_cabinet_id=mock_wb_cabinet.id,
        amount=500.0,
        description="Test bonus",
        transaction_date_time=datetime.now()
    )
    async with test_async_db as session:
        session.add(payment)
        await session.commit()
        await session.refresh(payment)

    assert payment.id is not None
    assert payment.wb_cabinet_id == mock_wb_cabinet.id
    assert payment.amount == 500.0
    assert payment.description == "Test bonus"

@pytest.mark.asyncio
async def test_process_cabinet_balance_topup(test_async_db, mock_wb_cabinet, mock_user, mock_wb_user_cabinet):
    """Тест процесса пополнения баланса через бота"""
    # Сохраняем фикстуры в базу данных
    async with test_async_db as session:
        session.add(mock_wb_cabinet)
        session.add(mock_user)
        session.add(mock_wb_user_cabinet)
        await session.commit()
        await session.refresh(mock_wb_cabinet)
        await session.refresh(mock_user)
        await session.refresh(mock_wb_user_cabinet)

    # Начальный баланс
    initial_balance = mock_wb_cabinet.balance
    
    # Сумма пополнения
    topup_amount = 500.0
    
    # Вызываем функцию пополнения
    payment = await process_cabinet_balance_topup(
        user_id=mock_user.id,
        cabinet_id=mock_wb_cabinet.id,
        amount=topup_amount
    )
    
    assert payment.id is not None
    assert payment.wb_cabinet_id == mock_wb_cabinet.id
    assert payment.amount == topup_amount

    async with test_async_db as session:
        payments = await session.execute(
            select(MockWBBalancePayment)
            .where(MockWBBalancePayment.wb_cabinet_id == mock_wb_cabinet.id)
            .order_by(MockWBBalancePayment.transaction_date_time.desc())
        )
        payments = payments.scalars().all()
        assert len(payments) == 1
        assert payments[0].id == payment.id
    
    # Проверяем, что баланс кабинета не изменился
    cabinet = await test_async_db.get(MockWBCabinet, mock_wb_cabinet.id)
    assert cabinet.balance == initial_balance

@pytest.mark.asyncio
async def test_confirm_balance_payment(test_async_db, mock_wb_cabinet):
    """Тест подтверждения платежа и обновления баланса кабинета"""
    # Сохраняем фикстуры в базу данных
    async with test_async_db as session:
        session.add(mock_wb_cabinet)
        await session.commit()
        await session.refresh(mock_wb_cabinet)

    # Начальный баланс
    initial_balance = mock_wb_cabinet.balance
    payment_amount = 1000.0
    
    # Создаем запись о платеже
    payment = MockWBBalancePayment(
        wb_cabinet_id=mock_wb_cabinet.id,
        amount=payment_amount,
        description="Test payment",
        transaction_date_time=datetime.now()
    )
    
    async with test_async_db as session:
        session.add(payment)
        await session.commit()
        await session.refresh(payment)
        
        # Подтверждаем платеж
        updated_payment, updated_cabinet = await confirm_cabinet_balance_topup(payment.id, mock_wb_cabinet.id)
        
        assert updated_payment.id == payment.id
        assert updated_cabinet.id == mock_wb_cabinet.id
        assert updated_cabinet.balance == initial_balance + payment_amount 