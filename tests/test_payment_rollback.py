import asyncio
import pytest
from datetime import datetime, date, timedelta
from sqlalchemy import select, and_
from tests.mocks import MockAdvPayment as AdvPayment, MockAdvSetting as AdvSetting, MockWBCabinet as WBCabinet
from app.utils.db.session_maker import get_async_session_maker
from app.utils.pricer.pricer import Pricer
from payment_compensation import fix_payments_without_amount
from app.payment_rollback import rollback_payments, get_rollback_statistics
from sqlalchemy.ext.asyncio import AsyncSession
import json


@pytest.fixture
async def test_data(session, mock_wb_cabinet):
    """Создает тестовые данные для проверки компенсации платежей"""
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
        id=1,
        adv_id=1,
        name="Test Campaign",
        wb_cabinet_id=mock_wb_cabinet.id,
        active_status="active",
        bot_active=False,
        nmids=[12345, 67890],
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

    adv_setting2 = AdvSetting(
        id=2,
        adv_id=2,
        name="Test Campaign 2",
        wb_cabinet_id=mock_wb_cabinet.id,
        active_status="active",
        bot_active=False,
        nmids=[98765, 43210],
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
    session.add(adv_setting2)
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
    return {"cabinet": cabinet, "adv_setting": adv_setting, "adv_setting2": adv_setting2, "payments": payments}


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
            AdvPayment.adv_setting_id == adv_setting_id,
            AdvPayment.type.is_(None)  # Обычные платежи
        )
        result = await session.execute(query)
        payments = result.scalars().all()
        
        # Проверяем, что все платежи за вчера получили amount
        assert all(payment.amount is not None for payment in payments)
        
        # Проверяем запись о компенсации
        query = select(AdvPayment).where(
            AdvPayment.date == yesterday,
            AdvPayment.adv_setting_id == adv_setting_id,
            AdvPayment.type == 'compensation'
        )
        result = await session.execute(query)
        compensation_payments = result.scalars().all()
        assert len(compensation_payments) == 1
        
        compensation_payment = compensation_payments[0]
        assert compensation_payment.amount is not None
        assert compensation_payment.type == 'compensation'
        
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
            AdvPayment.adv_setting_id == adv_setting_id,
            AdvPayment.type.is_(None)  # Обычные платежи
        )
        result = await session.execute(query)
        today_payments = result.scalars().all()
        
        # Проверяем сегодняшние компенсации
        query = select(AdvPayment).where(
            AdvPayment.date == today,
            AdvPayment.adv_setting_id == adv_setting_id,
            AdvPayment.type == 'compensation'
        )
        result = await session.execute(query)
        today_compensations = result.scalars().all()
        
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
        assert len(today_compensations) == 1
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


@pytest.mark.asyncio
async def test_get_rollback_statistics_empty(test_data):
    """Тест получения статистики при отсутствии платежей"""
    future_date = date.today() + timedelta(days=365)  # Дата в будущем
    stats = await get_rollback_statistics(future_date)
    
    assert stats["total_payments"] == 0
    assert stats["total_compensation"] == 0
    assert stats["campaigns_count"] == 0
    assert stats["cabinet_count"] == 0


@pytest.mark.asyncio
async def test_get_rollback_statistics_with_payments(test_data):
    """Тест получения статистики с существующими платежами"""
    cabinet_id = test_data["cabinet"].id
    adv_setting_id = test_data["adv_setting"].id
    yesterday = date.today() - timedelta(days=1)
    
    # Добавляем платежи с amount
    async with get_async_session_maker() as session:
        payments = [
            AdvPayment(
                wb_cabinet_id=cabinet_id,
                adv_setting_id=adv_setting_id,
                date=yesterday,
                amount=100.0
            ),
            AdvPayment(
                wb_cabinet_id=cabinet_id,
                adv_setting_id=adv_setting_id,
                date=yesterday,
                amount=200.0
            )
        ]
        for payment in payments:
            session.add(payment)
        await session.commit()
    
    # Получаем статистику
    stats = await get_rollback_statistics(yesterday)
    
    # Проверяем статистику
    assert stats["total_payments"] == 2
    assert stats["total_compensation"] == 300.0
    assert stats["campaigns_count"] == 1
    assert stats["cabinet_count"] == 1
    
    # Очищаем тестовые данные
    await cleanup_test_data(cabinet_id)


@pytest.mark.asyncio
async def test_get_rollback_statistics_multiple_campaigns(test_data):
    """Тест получения статистики с несколькими кампаниями"""
    cabinet_id = test_data["cabinet"].id
    adv_setting_id = test_data["adv_setting"].id
    yesterday = date.today() - timedelta(days=1)
    
    # Создаем вторую кампанию
    async with get_async_session_maker() as session:
        second_adv_setting = AdvSetting(
            adv_id=2,
            name="Second Campaign",
            wb_cabinet_id=cabinet_id,
            active_status="active",
            type=8,
            nmids=[98765, 43210],
            max_cpc=100.0
        )
        session.add(second_adv_setting)
        await session.flush()
        
        # Добавляем платежи для обеих кампаний
        payments = [
            AdvPayment(
                wb_cabinet_id=cabinet_id,
                adv_setting_id=adv_setting_id,
                date=yesterday,
                amount=100.0
            ),
            AdvPayment(
                wb_cabinet_id=cabinet_id,
                adv_setting_id=second_adv_setting.id,
                date=yesterday,
                amount=200.0
            )
        ]
        for payment in payments:
            session.add(payment)
        await session.commit()
    
    # Получаем статистику
    stats = await get_rollback_statistics(yesterday)
    
    # Проверяем статистику
    assert stats["total_payments"] == 2
    assert stats["total_compensation"] == 300.0
    assert stats["campaigns_count"] == 2
    assert stats["cabinet_count"] == 1
    
    # Очищаем тестовые данные
    await cleanup_test_data(cabinet_id) 