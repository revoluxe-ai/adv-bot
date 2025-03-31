import asyncio
from datetime import datetime, date, timedelta
from sqlalchemy import select, and_, func, delete
from app.modules.common_slaves.wildberries.models import AdvPayment, AdvSetting, WBCabinet
from app.utils.db.session_maker import get_async_session_maker
from app.utils.pricer.pricer import Pricer
import sys
import os

# Добавляем корневую директорию в sys.path для импорта из корня
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from payment_compensation import fix_payments_without_amount


async def rollback_payments(target_date: date) -> None:
    """
    Откатывает платежи и предоставляет компенсацию за указанную дату.
    
    Логика отката:
    1. Находим все платежи за указанную дату
    2. Группируем их по кабинетам и рекламным кампаниям
    3. Для каждой кампании:
       - Рассчитываем сумму компенсации
       - Возвращаем деньги на баланс кабинета
       - Удаляем платежи
    
    Args:
        target_date (date): Дата, за которую нужно откатить платежи
    """
    async_session_maker = get_async_session_maker()
    async with async_session_maker() as session:
        # Получаем все платежи за указанную дату
        query = select(AdvPayment).join(AdvPayment.adv_setting).where(
            AdvPayment.date == target_date
        )
        result = await session.execute(query)
        payments = result.scalars().all()
        
        if not payments:
            return
            
        # Группируем платежи по кампаниям
        campaign_payments = {}
        for payment in payments:
            campaign_id = payment.adv_setting_id
            if campaign_id not in campaign_payments:
                campaign_payments[campaign_id] = []
            campaign_payments[campaign_id].append(payment)
        
        # Обрабатываем каждую кампанию
        for campaign_id, campaign_payments_list in campaign_payments.items():
            # Получаем настройки кампании
            adv_setting = await session.get(AdvSetting, campaign_id)
            if not adv_setting:
                continue
                
            # Получаем кабинет
            cabinet = await session.get(WBCabinet, adv_setting.wb_cabinet_id)
            if not cabinet:
                continue
            
            # Рассчитываем сумму компенсации
            compensation = 0
            for payment in campaign_payments_list:
                if payment.amount:
                    compensation += payment.amount
            
            # Компенсируем на баланс кабинета
            cabinet.balance += compensation
            
            # Удаляем платежи
            for payment in campaign_payments_list:
                await session.delete(payment)
        
        # Сохраняем изменения
        await session.commit() 