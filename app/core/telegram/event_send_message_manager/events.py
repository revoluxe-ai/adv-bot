from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.utils.db.session_maker import get_async_session_maker as sm
from app.modules.common_slaves.wildberries.models import WBCabinet, WBUserCabinet
from app.utils.db.models import User
from app.client_bot.bot import bot

class NotValidTokens:

    def __init__(self, wb_cabinet: WBCabinet):
        self.wb_cabinet = wb_cabinet


    async def send_all_users(self):
        stmt = select(User)\
        .join(User.wb_user_cabinets)\
            .where(WBUserCabinet.wb_cabinet_id == self.wb_cabinet.id)
        async with sm() as session:
            users = (await session.execute(stmt)).scalars().all()
            for user in users:
                await bot(
                    user.user_telegram_id,
                    'Ваш токен для работы с Wildberries не действителен. Для продолжения работы обновите его в настройках бота'
                )
