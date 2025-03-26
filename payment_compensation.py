import asyncio
from datetime import datetime, date, timedelta
from sqlalchemy import select, and_, func
from app.modules.common_slaves.wildberries.models import AdvPayment, AdvSetting, WBCabinet
from app.utils.db.session_maker import get_async_session_maker
from app.utils.pricer.pricer import Pricer


async def fix_payments_without_amount(target_date: date) -> None:
    """
    Исправляет проблему с платежами без указания amount за указанную дату.
    
    Логика компенсации:
    1. Находим все платежи без amount за указанную дату
    2. Группируем их по кабинетам и рекламным кампаниям
    3. Для каждой кампании:
       - Считаем количество платежей - 1 (это количество кампаний)
       - Рассчитываем тариф через Pricer
       - Компенсируем на основе тарифа и количества кампаний
    
    Args:
        target_date (date): Дата, за которую нужно исправить платежи
    """
    async_session_maker = get_async_session_maker()
    async with async_session_maker() as session:
        # Получаем все платежи без amount за указанную дату
        query = select(AdvPayment).join(AdvPayment.adv_setting).where(
            and_(
                AdvPayment.date == target_date,
                AdvPayment.amount.is_(None)
            )
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
            
            # Рассчитываем количество кампаний (количество платежей - 1)
            num_campaigns = len(campaign_payments_list) - 1
            if num_campaigns <= 0:
                continue
            
            # Рассчитываем тариф через Pricer
            pricer = Pricer()
            tariff = pricer.get_tariff(adv_setting.type)
            
            # Рассчитываем компенсацию
            compensation = tariff * num_campaigns
            
            # Обновляем amount в платежах
            payment_amount = compensation / len(campaign_payments_list)
            for payment in campaign_payments_list:
                payment.amount = payment_amount
            
            # Компенсируем на баланс кабинета
            cabinet.balance += compensation
        
        # Сохраняем изменения
        await session.commit()


async def main():
    """Функция для запуска компенсации платежей без amount за вчерашний день"""
    yesterday = datetime.now().date() - timedelta(days=1)
    print(f"Исправление платежей без amount за {yesterday}")
    await fix_payments_without_amount(yesterday)
    print("Компенсация завершена")


if __name__ == "__main__":
    asyncio.run(main()) 