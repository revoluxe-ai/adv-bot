from abc import ABC, abstractmethod
import os
from typing import Union

from sqlalchemy import select

from app.core.telegram.event_send_message_manager import events
from app.utils.db.session_maker import get_async_session_maker as sm
from . import exceptions
import json
import aiohttp
import logging
from . import models
import app
from .models import WBToken, WBUserCabinet, WBCabinet
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .super_cabinet_manager import WBCabinetAccess




logger = logging.getLogger(__name__)






class WbRequestApiMixin(ABC):
    pass





class Headers:
    def __init__(self, token: models.WBToken):
       self.current_token: models.WBToken = token
    @property
    def standart(self):
        return {'Authorization': self.current_token.api_key}



class ABC_WB_API(WbRequestApiMixin):
    HOST = 'https://suppliers-api.wildberries.ru/'
    current_path = os.path.dirname(os.path.abspath(__file__))

    ORDERS_REPORTS_FOLDER = os.path.join(current_path, 'WB_orders_reports')
    DISCOUNT_REPORTS_FOLDER = os.path.join(current_path, 'WB_discount_reports')
    DB_NAME = os.path.join(current_path, 'stoks_from_site.db')
    _single_adv_files = os.path.join(current_path, 'singe_adv_files')
    _single_advs_report = os.path.join(current_path, 'single_advs_report.csv')


    def __init__(self, wb_access: 'WBCabinetAccess'):
        tokens: list[WBToken]= wb_access.tokens
        self.access = wb_access
        wb_cabinet: Union[WBUserCabinet] = wb_access.wb_cabinet
        self.wb_cabinet = wb_cabinet
        assert wb_cabinet
        if not tokens:
            raise exceptions.ApiForbiddenError('Нет токенов для доступа к API',
                                               wb_user_cabinet=wb_access.wb_user_cabinet)
        tokens = sorted(tokens, key=lambda x: x.expires, reverse=True)
        self._free_tokens = tokens
        current_token = self._free_tokens.pop()
        self.headers = Headers(current_token)
        self._shop_id = current_token.shop_id


    @property
    @abstractmethod
    def _rights(self) -> set[str]:
        pass

    @property
    @abstractmethod
    def _only_read(self):
        pass




    @staticmethod
    def chunks(lst, n):
        for i in range(0, len(lst), n):
            yield lst[i:i + n]



    async def set_next_token(self):
        if self._free_tokens:
            self.headers = Headers(self._free_tokens.pop())
        else:
            wb_cabinet: WBCabinet = self.access.wb_cabinet
            try:
                async with sm() as session:
                    fresh_cabinet = await session.get(WBCabinet, wb_cabinet.id)
                    if fresh_cabinet:
                        fresh_cabinet.active = False
                        await session.commit()
            except Exception as e:
                logger.error(f'Ошибка при отключении кабинета {wb_cabinet.shop_id}: {e}', exc_info=True)
                raise e
            try:
                await events.NotValidTokens(wb_cabinet.id,
                                            wb_cabinet.shop_id).send_all_users()
            except Exception as e:
                logger.error(f'Ошибка при отправке сообщения о невалидных токенах: {e}', exc_info=True)
            raise exceptions.ApiForbiddenError('Нет свободных токенов',
                                               wb_user_cabinet=self.access.wb_cabinet)
