import dotenv
dotenv.load_dotenv()
from datetime import datetime, date, timedelta
from typing import Dict, List
from sqlalchemy import select
from app.modules.common_slaves.wildberries.models import AdvPayment, WBCabinet
from app.utils.db.session_maker import get_async_session_maker as sm
from app.utils.pricer.pricer import Pricer


class PaymentCompensator:
    pricer = Pricer()

    def __init__(self):
        self.session = None
        self._compensated_cabinet_ids = set()

    async def main(self):
        """Запускает компенсацию платежей без amount за период с 25.03.2025"""
        start_date = date(2025, 3, 25)
        end_date = datetime.now().date()

        async with sm() as session:
            self.session = session
            async with session.begin():  # Одна транзакция на всё
                await self._compensate_over_payments(start_date, end_date)

    async def _compensate_over_payments(self, start_date, end_date):
        """Компенсация излишних списаний за период"""
        for current_date in self._date_range(start_date, end_date):
            over_payments_by_cabinet = await self._get_payments_by_cabinet_for_date(current_date)

            for cabinet_id, over_payments in over_payments_by_cabinet.items():
                if cabinet_id in self._compensated_cabinet_ids:
                    continue
                compansation_sum = self._calculate_over_payments(over_payments)
                for date_for_comp in self._date_range(start_date, current_date):
                    success = await self._create_compensation_payment(cabinet_id, compansation_sum, date_for_comp)
                    if success:
                        await self._compensate_cabinet(cabinet_id, compansation_sum)
                        self._compensated_cabinet_ids.add(cabinet_id)
                        break

    @staticmethod
    def _date_range(start_date, end_date):
        """Генератор дат для диапазона"""
        current_date = start_date
        while current_date <= end_date:
            yield current_date
            current_date += timedelta(days=1)

    async def _get_payments_by_cabinet_for_date(self, current_date) -> Dict[int, AdvPayment]:
        """Получение излишних платежей за день"""
        query = select(AdvPayment).where(AdvPayment.date == current_date)
        payments = await self.session.execute(query)
        payments = payments.scalars().all()

        over_payments_by_cabinet = {}
        for payment in payments:
            if payment.amount is None:
                cabinet_id = payment.wb_cabinet_id
                over_payments_by_cabinet.setdefault(cabinet_id, []).append(payment)
        return over_payments_by_cabinet

    async def _calculate_over_payments(self, payments: List[AdvPayment]) -> float:
        """Вычисляет сумму компенсации"""
        count_advs = len(payments)
        return await self.pricer.get_price_for_count_advs_in_cabinet(count_advs)

    async def _compensate_cabinet(self, cabinet_id, over_payments_sum):
        """Обновление бонуса кабинета"""
        cabinet = await self.session.get(WBCabinet, cabinet_id)
        cabinet.bonus += over_payments_sum

    async def _create_compensation_payment(self, cabinet_id, over_payments_sum, comp_date):
        """Создаёт компенсационную запись и гарантирует её добавление"""
        payment = AdvPayment(
            wb_cabinet_id=cabinet_id,
            date=comp_date,
            amount=over_payments_sum,
            comment='Компенсация излишних списаний'
        )
        self.session.add(payment)
        await self.session.flush()  # Гарантия добавления в БД перед изменением бонуса
        return True
