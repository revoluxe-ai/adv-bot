from abc import ABC, abstractmethod
import os
from typing import Union

from sqlalchemy import select

from app.utils.db.session_maker import get_async_session_maker as sm
from . import exceptions
import json
import aiohttp
import logging
from . import models
import app
from .models import WBToken, WBUserCabinet
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .super_cabinet_manager import WBCabinetAccess




logger = logging.getLogger(__name__)






class WbRequestApiMixin(ABC):

    @property
    @abstractmethod
    def _wb_user_cabinet(self) :
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
        wb_user_cabinet: Union[WBUserCabinet] = wb_access.wb_user_cabinet

        if not tokens:
            raise exceptions.ApiForbiddenError('Нет токенов для доступа к API',
                                               wb_user_cabinet=wb_user_cabinet)
        tokens = sorted(tokens, key=lambda x: x.expires, reverse=True)
        self._free_tokens = tokens
        current_token = self._free_tokens.pop()
        self.headers = Headers(current_token)
        self._shop_id = current_token.shop_id


    @property
    def _wb_user_cabinet(self):
        return self.__wb_user_cabinet

    @_wb_user_cabinet.setter
    def _wb_user_cabinet(self, value):
        self.__wb_user_cabinet = value


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
        current_token: WBToken = self.headers.current_token
        async with sm() as session:
            stmt = select(WBToken).where(WBToken.id == current_token.id)
            result = await session.execute(stmt)
            token = result.scalar()
            token.active = False
            await session.commit()
        if self._free_tokens:
            self.headers = Headers(self._free_tokens.pop())
        else:
            raise exceptions.ApiForbiddenError('Нет свободных токенов',
                                               wb_user_cabinet=self._wb_user_cabinet)
