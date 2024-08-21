from abc import ABC, abstractmethod
import os
from typing import Union

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
       self.__token = token
    @property
    def standart(self):
        return {'Authorization': self.__token.api_key}



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

        self._wb_user_cabinet = wb_user_cabinet
        for token in tokens:
            if  self._rights.issubset(token.categories) \
                    and self._only_read == token.read_only:
                current_token = token
                self._free_tokens = set(tokens) - {current_token}
                break

        else:
            raise (exceptions.ApiForbiddenError
                   (f'Нет токена с правами {self._rights} и only_read = {self._only_read}',
                    wb_user_cabinet=wb_user_cabinet
                    ))
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



    def set_next_token(self):
        if self._free_tokens:
            self.headers = Headers(self._free_tokens.pop())
        else:
            raise exceptions.ApiForbiddenError('Нет свободных токенов',
                                               wb_user_cabinet=self._wb_user_cabinet)
