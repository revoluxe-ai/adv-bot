import asyncio
import pytest
from datetime import datetime, date, timedelta
from sqlalchemy import select, and_
from tests.mocks import MockAdvPayment as AdvPayment, MockAdvSetting as AdvSetting, MockWBCabinet as WBCabinet
from app.utils.db.session_maker import get_async_session_maker
from app.utils.pricer.pricer import Pricer
from payment_compensation import fix_payments_without_amount
from app.payment_rollback import rollback_payments
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.fixture
async def test_data():
    """Создает тестовые данные для проверки компенсации платежей"""
    async with get_async_session_maker() as session:
        # Создаем тестовый кабинет WB
        cabinet = WBCabinet(
            shop_id="test_shop_123",
            balance=1000.0,
            bonus=100.0,
            active=True
        )
        session.add(cabinet)
        await session.flush()

        # Создаем тестовые настройки рекламы
        adv_setting = AdvSetting(
            adv_id=1,
            name="Test Campaign",
            wb_cabinet_id=cabinet.id,
            active_status="active",
            type="search",
            max_cpc=100.0
        )
        session.add(adv_setting)
        await session.flush()

        # Создаем тестовые платежи без amount за вчера и сегодня
        yesterday = date.today() - timedelta(days=1)
        today = date.today()

        payments = [
            AdvPayment(
                wb_cabinet_id=cabinet.id,
                adv_setting_id=adv_setting.id,
                date=yesterday,
                amount=None
            ),
            AdvPayment(
                wb_cabinet_id=cabinet.id,
                adv_setting_id=adv_setting.id,
                date=today,
                amount=None
            )
        ]
        for payment in payments:
            session.add(payment)
        
        await session.commit()
        return {"cabinet": cabinet, "adv_setting": adv_setting, "payments": payments}


async def cleanup_test_data(cabinet_id):
    """Удаляет тестовые данные"""
    async with get_async_session_maker() as session:
        # Получаем adv_settings для кабинета
        query = select(AdvSetting).where(AdvSetting.wb_cabinet_id == cabinet_id)
        result = await session.execute(query)
        adv_settings = result.scalars().all()
        
        # Удаляем платежи для каждого adv_setting
        for adv_setting in adv_settings:
            query = select(AdvPayment).where(AdvPayment.adv_setting_id == adv_setting.id)
            result = await session.execute(query)
            payments = result.scalars().all()
            for payment in payments:
                await session.delete(payment)
        
        # Удаляем adv_settings
        for adv_setting in adv_settings:
            await session.delete(adv_setting)
        
        # Удаляем кабинет
        query = select(WBCabinet).where(WBCabinet.id == cabinet_id)
        result = await session.execute(query)
        cabinet = result.scalar_one()
        await session.delete(cabinet)
        
        await session.commit()


@pytest.mark.asyncio
async def test_fix_payments_without_amount(test_data):
    """Тест функции исправления платежей без amount"""
    cabinet_id = test_data["cabinet"].id
    adv_setting_id = test_data["adv_setting"].id
    yesterday = date.today() - timedelta(days=1)
    
    # Исправляем платежи
    await fix_payments_without_amount(yesterday)
    
    async with get_async_session_maker() as session:
        # Проверяем, что платежи были правильно обработаны
        query = select(AdvPayment).where(
            AdvPayment.date == yesterday,
            AdvPayment.adv_setting_id == adv_setting_id
        )
        result = await session.execute(query)
        payments = result.scalars().all()
        
        # Проверяем, что все платежи за вчера получили amount
        assert all(payment.amount is not None for payment in payments)
        
        # Проверяем баланс кабинета
        cabinet = await session.get(WBCabinet, cabinet_id)
        assert cabinet.balance != 1000.0  # Баланс должен измениться


@pytest.mark.asyncio
async def test_fix_payments_without_amount_only_today(test_data):
    """Тест обработки только сегодняшних платежей"""
    cabinet_id = test_data["cabinet"].id
    adv_setting_id = test_data["adv_setting"].id
    today = date.today()
    
    # Исправляем платежи только за сегодня
    await fix_payments_without_amount(today)
    
    async with get_async_session_maker() as session:
        # Проверяем сегодняшние платежи
        query = select(AdvPayment).where(
            AdvPayment.date == today,
            AdvPayment.adv_setting_id == adv_setting_id
        )
        result = await session.execute(query)
        today_payments = result.scalars().all()
        
        # Проверяем вчерашние платежи
        yesterday = today - timedelta(days=1)
        query = select(AdvPayment).where(
            AdvPayment.date == yesterday,
            AdvPayment.adv_setting_id == adv_setting_id
        )
        result = await session.execute(query)
        yesterday_payments = result.scalars().all()
        
        # Проверяем, что обработаны только сегодняшние платежи
        assert all(payment.amount is not None for payment in today_payments)
        assert all(payment.amount is None for payment in yesterday_payments)


@pytest.mark.asyncio
async def test_rollback_payments_with_compensation(test_data):
    """Тест отката платежей с компенсацией"""
    cabinet_id = test_data["cabinet"].id
    adv_setting_id = test_data["adv_setting"].id
    yesterday = date.today() - timedelta(days=1)
    
    # Откатываем платежи
    await rollback_payments(yesterday)
    
    async with get_async_session_maker() as session:
        # Проверяем, что все платежи за вчера удалены
        query = select(AdvPayment).where(
            AdvPayment.date == yesterday,
            AdvPayment.adv_setting_id == adv_setting_id
        )
        result = await session.execute(query)
        payments = result.scalars().all()
        assert len(payments) == 0
        
        # Проверяем, что баланс кабинета изменился
        cabinet = await session.get(WBCabinet, cabinet_id)
        assert cabinet.balance > 1000.0  # Баланс должен увеличиться после компенсации

    try:
        # Очищаем тестовые данные
        await cleanup_test_data(cabinet_id)
    except Exception as e:
        print(f"Ошибка при очистке тестовых данных: {e}") 