import aiogram
from sqlalchemy import select, func

from app.payments.db.models import Payment
from app.utils.db.models import User, RefLink, user_reflink_association
from app.utils.db.session_maker import get_async_session_maker
from aiogram.utils import deep_linking

_sm = get_async_session_maker()




from dataclasses import dataclass
from typing import List, Optional
from sqlalchemy.future import select
from sqlalchemy import func

@dataclass
class ReferralStatistic:
    name: str
    referrals_count: int
    total_payments: float

async def get_ref_statistic(user_telegram_id: int) -> Optional[List[ReferralStatistic]]:
    """Получить статистику по рефералам пользователя: количество приведенных пользователей и сумму их платежей."""
    async with _sm() as session:
        # Сначала найдем пользователя по telegram_id
        user_query = select(User.id).where(User.user_telegram_id == user_telegram_id)
        result = await session.execute(user_query)
        user_id = result.scalar() # Используйте scalar_one_or_none для обработки случая, когда пользователь не найден

        # Теперь получим статистику по реферальным ссылкам
        statistics_query = select(
            RefLink.name,
            func.count(user_reflink_association.c.user_id).label("referrals_count"),
            func.coalesce(func.sum(Payment.amount), 0).label("total_payments")
        ).select_from(RefLink) \
         .outerjoin(user_reflink_association, RefLink.id == user_reflink_association.c.reflink_id) \
         .outerjoin(User, user_reflink_association.c.user_id == User.id) \
         .outerjoin(Payment, Payment.user_id == User.id) \
         .where(RefLink.referrer_id == user_id) \
         .group_by(RefLink.name)

        result = await session.execute(statistics_query)
        stats = result.fetchall()

        if not stats:
            return None

        # Возвращаем результаты в удобном для использования виде
        return [ReferralStatistic(name=row[0], referrals_count=row[1], total_payments=row[2]) for row in stats]


@dataclass
class ReferralLink:
    name: str
    link: str



async def get_ref_names_and_links(user_telegram_id: int, bot:aiogram.Bot):
    async with _sm() as session:
        stmt = select(User.id).where(User.user_telegram_id == user_telegram_id)
        result = await session.execute(stmt)
        user_id = result.scalar()
        stmt = select(RefLink.name, RefLink.id).where(RefLink.referrer_id == user_id)
        result = await session.execute(stmt)
        refs = result.fetchall()

    ref_links = []
    for ref in refs:
        link = await deep_linking.create_start_link(bot, ref[1])
        ref_links.append(ReferralLink(name=ref[0], link= link))
    return ref_links








