import asyncio

import aiohttp

import app
from app.modules.common_slaves.wildberries.api_rights import TokenRightChecker
from app.modules.common_slaves.wildberries.exceptions import ApiForbiddenError, UnknownApiRequestError
from app.modules.common_slaves.wildberries.models import WBToken
from app.modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
from app.utils.db.session_maker import get_async_session_maker
import logging


logger = logging.getLogger(__name__)

_sm = get_async_session_maker()


#
#
# async  def get_cabinet_manager(wb_user_cabinet_original_id):
#     async with _sm() as session:
#         stmt = (
#             select(WBUserCabinet)
#             .join(WBUserCabinet.wb_cabinet)  # Явно указываем соединение с WBCabinet
#             .options(
#                 selectinload(WBUserCabinet.wb_cabinet).
#                 selectinload(WBCabinet.adv_settings),  # Загружаем adv_settings
#                 selectinload(WBUserCabinet.user)\
#                 .selectinload(User.wb_tokens)# Загружаем информацию о пользователе
#             )
#             .where(WBUserCabinet.id == wb_user_cabinet_original_id)  # Условие должно быть скорректировано
#         )
#         result = await session.execute(stmt)
#         wb_user_cabinet: WBUserCabinet = result.scalars().first()
#
#     return CabinetManager(wb_user_cabinet)








class CabinetManager:
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








