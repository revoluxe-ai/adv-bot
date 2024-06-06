import datetime
import logging

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import selectinload

from app.admin_bot.sender import sender_manager
from app.client_bot.bot import bot
from app.modules.common_slaves.wildberries.models import WBCabinet, WBUserCabinet
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker

from . import messages

logger = logging.getLogger(__name__)

_sm = get_async_session_maker

# период в сутках - сообщение
_messages_period = [
    [1, messages.TestPeriodExpire],
    [2, messages.TestPeriodExpire],
    [3, messages.TestPeriodExpire],
    [4, messages.TestPeriodExpire],
    [5, messages.TestPeriodExpire],
    [6, messages.TestPeriodExpire],
    [7, messages.TestPeriodExpire],

]

_messages_period.reverse()


async def check_all():
    await send_messages_for_shop_subscribes_expire()


async def send_messages_for_shop_subscribes_expire():
    now = datetime.datetime.now()
    today = now.date()
    if 12 <= now.hour <= 16:
        for n, row in enumerate(_messages_period):
            days = row[0]
            message = row[1]
            expiration_date = today + datetime.timedelta(days=days)

            stmt = select(WBCabinet) \
                .options(selectinload(WBCabinet.wb_user_cabinets) \
                         .selectinload(WBUserCabinet.user)) \
                .filter(
                and_(
                    func.date(WBCabinet.expiration_time) == expiration_date,
                    or_(
                        WBCabinet.expiration_alarm_days_pass == None,
                        WBCabinet.expiration_alarm_days_pass > days
                    )
                )
            )
            async with _sm() as session:
                result = await session.execute(stmt)
                wb_cabinets = result.scalars().all()

                for wb_cabinet in wb_cabinets:
                    wb_user_cabinets = wb_cabinet.wb_user_cabinets
                    for wb_user_cabinet in wb_user_cabinets:
                        user_telegram_id = wb_user_cabinet.user.user_telegram_id
                        try:
                            await message(bot, user_telegram_id, days, wb_user_cabinet)()
                        except Exception as e:
                            logger.error(f'Не удалось отправить сообщение пользователю: {e}')
                        wb_cabinet.expiration_alarm_days_pass = days
                        await session.commit()
