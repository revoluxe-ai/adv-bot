import asyncio
import logging
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.admin_bot.sender import redis_manager
from app.client_bot import single_messages
from app.client_bot.bot import bot
from app.modules.common_slaves.wildberries.models.models import AdvSetting, WBUserCabinet
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker as sm
from get_clients_to_file import get_total_spend

logger = logging.getLogger(__name__)


USER_TYPE = "user_with_active_company"

test_users_ids = [373435337, 707068503]


async def get_users():
    stmt = select(User).options(selectinload(User.wb_user_cabinets).selectinload(WBUserCabinet.wb_cabinet))
    async with sm() as session:
        users = await session.stream(stmt)
        async for user in users.scalars().yield_per(10):
            total_spend = 0
            total_advs = 0
            active_advs_with_bot = 0
            total_balance = 0
            total_bonus = 0
            wb_user_cabinets = user.wb_user_cabinets
            for wb_user_cabinet in wb_user_cabinets:
                wb_cabinet = wb_user_cabinet.wb_cabinet
                total_balance += wb_cabinet.balance or 0
                total_bonus += wb_cabinet.bonus or 0

                stmt = select(AdvSetting.adv_id).where(AdvSetting.wb_cabinet_id == wb_cabinet.id)

                adv_ids = await session.execute(stmt)
                adv_ids = adv_ids.scalars().all()

                spend = await get_total_spend(adv_ids)
                total_spend += spend

                stmt = select(AdvSetting).where(
                    AdvSetting.adv_id.in_(adv_ids),
                    AdvSetting.active_status == "started",
                )

                advs = await session.execute(stmt)
                advs = advs.scalars().all()

                total_advs += len(advs)
                active_advs_with_bot += len([adv for adv in advs if adv.bot_active])
            "; ".join([wb_user_cabinet.wb_cabinet.shop_id for wb_user_cabinet in wb_user_cabinets])
            total_bonus + total_balance
            # if  not  wb_user_cabinets:
            yield user
            # continue


async def get_test_user():
    async with sm() as session:
        stmt = (
            select(User)
            .options(selectinload(User.wb_user_cabinets).selectinload(WBUserCabinet.wb_cabinet))
            .where(User.user_telegram_id.in_(test_users_ids))
        )
        user = await session.execute(stmt)
        user = user.scalars().all()
    for user in user:
        yield user


async def async_chain(*async_generators):
    for gen in async_generators:
        async for item in gen:
            yield item


async def send_message_to_users():
    send_count = 0
    not_send_count = 0
    users = get_users()
    # admin_users = get_test_user()
    # chain = async_chain(admin_users, users)
    async for user in users:
        user_id = user.user_telegram_id
        message = single_messages.Single_message
        hash = sha256((str(message)).encode()).hexdigest()
        if await redis_manager.check_message_send(hash, user_id):
            if user_id not in [373435337]:
                continue

        try:
            await message(bot, user_id)()
            await redis_manager.set_message_send(hash, user_id)
            send_count += 1
        except Exception as e:
            logger.error(e)
            del e
            not_send_count += 1
        print("Отправлено сообщений: ", send_count)
        print("Не отправлено сообщений: ", not_send_count)


if __name__ == "__main__":
    asyncio.run(send_message_to_users())
