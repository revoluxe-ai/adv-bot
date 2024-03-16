import asyncio

from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from app import exc
import app
from app.db.associations import WBUserCabinet
from app.telegram_bot.models import User
from app.wildberries.api import WBApi
from app.wildberries.adv_data_updater import ShopDataUpdater
from app.wildberries.api_rights import TokenRightChecker
from app.wildberries.models import WBCabinet
from session_maker import get_async_session_maker


_sm = get_async_session_maker()




async  def get_cabinet_manager(wb_user_cabinet_original_id):
    async with _sm() as session:
        stmt = (
            select(WBUserCabinet)
            .join(WBUserCabinet.wb_cabinet)  # Явно указываем соединение с WBCabinet
            .options(
                selectinload(WBUserCabinet.wb_cabinet).
                selectinload(WBCabinet.adv_settings),  # Загружаем adv_settings
                selectinload(WBUserCabinet.user)\
                .selectinload(User.wb_tokens)# Загружаем информацию о пользователе
            )
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)  # Условие должно быть скорректировано
        )
        result = await session.execute(stmt)
        wb_user_cabinet: WBUserCabinet = result.scalars().first()

    return CabinetManager(wb_user_cabinet)








class CabinetManager:
    def __init__(self, wb_user_cabinet: app.my_types.WBUserCabinet):
        self._user_cab = wb_user_cabinet
        self._wb_user_cabinet = wb_user_cabinet
        self._user: app.my_types.User = wb_user_cabinet.user
        self._wb_api = WBApi(wb_user_cabinet)
        self._shop_data_updater = ShopDataUpdater(self._wb_api,
                                                  self._user_cab)


    async def update_all_data(self):
        await self._shop_data_updater.update_all_data()


    @classmethod
    async def check_token_for_adv(cls, wb_user_cabinet: app.my_types.WBUserCabinet):
        right_checker = TokenRightChecker(wb_user_cabinet)
        return all(await asyncio.gather(
            right_checker.adverts(),
            right_checker.content()))








