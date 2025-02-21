from aiogram.exceptions import TelegramForbiddenError
from sqlalchemy import select

from app.client_bot import const
from app.modules.common_slaves.wildberries.models import WBUserCabinet
from app.utils.db.models import User
from app.client_bot.bot import bot
import logging
from app.utils.db.session_maker import get_async_session_maker as sm


logger = logging.getLogger(__name__)

class NotValidTokens:

    def __init__(self, wb_cabinet_id: int, shop_id: str):
        self.wb_cabinet_original_id = wb_cabinet_id
        self.shop_id = shop_id

    async def send_all_users(self):
        async with sm() as session:
            stmt = select(User)\
            .join(User.wb_user_cabinets)\
                .where(WBUserCabinet.wb_cabinet_id == self.wb_cabinet_original_id)
            users = (await session.execute(stmt)).scalars().all()
            for user in users:
                try:
                    await bot.send_message(user.user_telegram_id,
                                           f'Ваш токен для работы с Wildberries для магазина с shop id {self.shop_id}'
                                           f' не действителен. Для продолжения работы обновите его в настройках бота. '
                                           f'Чтобы обновить токен, добавьте магазин заново под новым именем и введите новый токен.'
                                           f'Новый магазин создан не будет, а у старого магазина токен будет обновлен. '
                                           f'Если возникли вопросы или вы считаете, что произошла ошибка и ваш токен в порядке, обратитесь в поддержку -> {const.SUPPORT_LINK}')
                except TelegramForbiddenError:
                    continue
                except Exception as e:
                    logger.error(f'Ошибка отправки сообщения пользователю {user.username} {e}', exc_info=True)