import asyncio
from datetime import datetime, date, timedelta
from sqlalchemy import select, and_
from app.modules.common_slaves.wildberries.models import AdvPayment, AdvSetting, WBCabinet
from app.utils.db.session_maker import get_async_session_maker
from app.utils.pricer.pricer import Pricer


async def fix_payments_without_amount(date_to_fix: date) -> None:
    """
    Исправляет проблему с платежами без указания amount за указанную дату.
    
    Логика компенсации:
    1. Находим все платежи без amount за указанную дату
    2. Группируем их по кабинетам
    3. Для каждого кабинета вычисляем количество кампаний (платежей - 1)
    4. Рассчитываем сумму компенсации через Pricer
    5. Начисляем компенсацию на баланс кабинета
    """
    async_session_maker = get_async_session_maker()
    async with async_session_maker() as session:
        # Найдем все кабинеты, для которых есть платежи без amount за указанную дату
        query = (
            select(WBCabinet)
            .join(AdvSetting, WBCabinet.id == AdvSetting.wb_cabinet_id)
            .join(AdvPayment, AdvSetting.id == AdvPayment.adv_setting_id)
            .where(AdvPayment.date == date_to_fix)
            .where(AdvPayment.amount.is_(None))
            .distinct()
        )
        result = await session.execute(query)
        cabinets = result.scalars().all()
        
        pricer = Pricer()
        
        # Для каждого кабинета вычисляем компенсацию
        for cabinet in cabinets:
            # Получаем все платежи без amount для данного кабинета за указанную дату
            query = (
                select(AdvPayment)
                .join(AdvSetting, AdvPayment.adv_setting_id == AdvSetting.id)
                .where(AdvSetting.wb_cabinet_id == cabinet.id)
                .where(AdvPayment.date == date_to_fix)
                .where(AdvPayment.amount.is_(None))
            )
            result = await session.execute(query)
            payments = result.scalars().all()
            
            # Количество кампаний = количество платежей
            # Если платеж только один, компенсация не требуется
            if len(payments) <= 1:
                continue
            
            # Рассчитываем стоимость за день для кабинета
            price_per_day = await pricer.get_price_for_day_for_shop(cabinet.shop_id)
            
            # Рассчитываем сумму компенсации: (количество платежей - 1) * цена за день
            compensation_amount = (len(payments) - 1) * price_per_day
            
            # Зачисляем компенсацию на баланс кабинета
            cabinet.balance += compensation_amount
            
            print(f"Компенсировано {compensation_amount} для кабинета {cabinet.id}, количество платежей: {len(payments)}")
        
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