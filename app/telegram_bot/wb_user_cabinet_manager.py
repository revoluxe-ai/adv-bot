import asyncio
from app import exc
import app
from app.wildberries.api import WBApi
from app.wildberries.adv_data_updater import ShopDataUpdater
from app.wildberries.api_rights import TokenRightChecker


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








