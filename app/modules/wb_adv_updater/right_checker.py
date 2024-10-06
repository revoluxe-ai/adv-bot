import asyncio

import aiohttp

from app.modules.common_slaves.wildberries.api_rights import TokenRightChecker
from app.modules.common_slaves.wildberries.exceptions import ApiForbiddenError, UnknownApiRequestError
from app.modules.common_slaves.wildberries.models import WBToken
import logging


logger = logging.getLogger(__name__)

class RightChecker:
    # def __init__(self, wb_user_cabinet: app.my_types.WBUserCabinet):
    #     self._user_cab = wb_user_cabinet
    #     self._wb_user_cabinet = wb_user_cabinet
    #     self._user: app.my_types.User = wb_user_cabinet.user
    #     self._wb_api = WBApi(wb_user_cabinet)
    #     self._shop_data_updater = ShopDataUpdater(self._wb_api,
    #                                               self._user_cab)


    @classmethod
    async def check_access(cls, token: WBToken):
        right_checker = TokenRightChecker(token)
        try:
            await asyncio.gather(
                right_checker.adverts(),
                right_checker.content())

        except ApiForbiddenError:
            raise
        except UnknownApiRequestError as e:
            logger.error(e)
        except aiohttp.client_exceptions.ServerDisconnectedError as e:
            logger.error(e)
        except aiohttp.client_exceptions.ClientOSError as e:
            logger.error(e)