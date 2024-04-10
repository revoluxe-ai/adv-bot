import datetime
from app.admin_bot.sender import sender_manager
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from app.client_bot.bot import bot
from app.utils.db.models import User
from app.modules.common_slaves.wildberries.models import WBCabinet, WBUserCabinet
from app.utils.db.session_maker import get_async_session_maker
from . import messages

_sm = get_async_session_maker()

#период в сутках - сообщение
_messages_period = [
    [1, messages.TestPeriodExpire],
    [2, messages.TestPeriodExpire],
    [3, messages.TestPeriodExpire],

]

_messages_period.reverse()

async def check_all():
    await send_messages_for_shop_subscribes_expire()



async def send_messages_for_shop_subscribes_expire():
    if 16 >= datetime.datetime.now().hour >= 8:
        for  n, row in enumerate(_messages_period):
            days = row[0]
            message = row[1]
            if n == 0:
                prev_period = None
            else:
                prev_period  = _messages_period[n-1][0]
            now = datetime.datetime.now()
            alarm_period = now - datetime.timedelta(days=days)
            async with _sm() as session:
                stmt = select(WBCabinet)\
                .options(selectinload(WBCabinet.wb_user_cabinets)\
                         .selectinload(WBUserCabinet.user))\
                    .filter(and_(WBCabinet.expiration_time > alarm_period,
                                                WBCabinet.expiration_alarm_days_pass == prev_period))
                result = await session.execute(stmt)
                wb_cabinets: list[WBCabinet] = result.scalars().all()

                for wb_cabinet in wb_cabinets:
                    wb_user_cabinets: list[User] = wb_cabinet.wb_user_cabinets
                    for wb_user_cabinet in wb_user_cabinets:
                        user_telegram_id = wb_user_cabinet.user.user_telegram_id
                        if user_telegram_id != 373435337:
                            continue
                        await message(bot, user_telegram_id, days, wb_user_cabinet)()
                        wb_cabinet.expiration_alarm_days_pass = days
                        await session.commit()









