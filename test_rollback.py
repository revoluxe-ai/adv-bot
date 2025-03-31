import asyncio
import pytest
from datetime import datetime, date, timedelta
from sqlalchemy import select, and_
from app.modules.wb_adv_updater.models import AdvPayment, AdvSetting
from app.modules.common_slaves.wildberries.models import WBCabinet
from app.utils.db.session_maker import get_async_session_maker
from app.payment_rollback import rollback_payments
from app.utils.pricer.pricer import Pricer

@pytest.mark.asyncio
async def test_rollback_payments():
    """Тест функции отката платежей"""
    # Создаем тестовые данные в базе
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
            type=9,  # search
            max_cpc=100.0
        )
        session.add(adv_setting)
        await session.flush()

        # Создаем тестовые платежи
        yesterday = date.today() - timedelta(days=1)
        payment = AdvPayment(
            wb_cabinet_id=cabinet.id,
            adv_setting_id=adv_setting.id,
            date=yesterday,
            amount=100.0,
            type="auto"
        )
        session.add(payment)
        await session.commit()

        # Получаем начальный баланс кабинета
        initial_balance = cabinet.balance

        # Откатываем платежи за вчера
        await rollback_payments(yesterday)

        # Проверяем, что платежи были удалены
        query = select(AdvPayment).where(
            AdvPayment.date == yesterday,
            AdvPayment.adv_setting_id == adv_setting.id
        )
        result = await session.execute(query)
        payments = result.scalars().all()
        assert len(payments) == 0

        # Проверяем, что баланс кабинета был увеличен
        await session.refresh(cabinet)
        assert cabinet.balance > initial_balance

        # Очищаем данные
        await session.delete(adv_setting)
        await session.delete(cabinet)
        await session.commit()

if __name__ == "__main__":
    asyncio.run(test_rollback_payments()) 