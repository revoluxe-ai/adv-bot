from abc import ABC, abstractmethod
import os
from . import exceptions
from .data_classes.interfaces import ShopInterface
import json
import aiohttp
import logging
from . import models
import app
from .models import WBToken

logger = logging.getLogger(__name__)


class WbRequestApiMixin(ABC):

    async def requests(self, session, method, url, data=None, json_data=None, headers=None, ):
        async with session.request(method, url, data=data, headers=headers, json=json_data) as response:
            try:
                logger.debug(f'Запрос к {url} выполнен. Статус: {response.status}')
                response.raise_for_status()
            except aiohttp.ClientResponseError as e:  # Предполагая использование aiohttp
                if e.status == 401:
                    raise exceptions.ApiForbiddenError('API доступ запрещен',
                                                       shop_id=self._shop_id) from e
                else:
                    # Для всех других ошибок 4xx и 5xx
                    raise exceptions.UnknownApiRequestError(e) from e

            # Если код не в блоке except, значит ответ был успешным (статус 200-299)
            text = await response.text()
            if text:
                json_answer = json.loads(text)
                if isinstance(json_answer, dict):
                    if code := json_answer.get('code'):
                        raise exceptions.ApiErrorWithCode(code, \
                                                          json_answer.get('message'), json_answer.get('rejection'))

            return text






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

    @property
    @abstractmethod
    def _rights(self) -> set[str]:
        pass

    @property
    @abstractmethod
    def _only_read(self):
        pass

    def __init__(self, wb_user_cabinet: app.my_types.WBUserCabinet):
        tokens: list[WBToken]= wb_user_cabinet.user.wb_tokens
        # tokens = [token for token in tokens if token.shop_id == wb_user_cabinet.wb_cabinet.shop_id]
        if not tokens:
            raise exceptions.ApiForbiddenError('Нет токенов для доступа к API',
                                               wb_user_cabinet=wb_user_cabinet)
        # if len(set(token.shop_id for token in tokens)) > 1:
        #     raise exceptions.TokensFromDifferentShopsError
        tokens = sorted(tokens, key=lambda x: x.expires, reverse=True)
        for token in tokens:
            if  self._rights.issubset(token.categories) \
                    and self._only_read == token.read_only:
                current_token = token
                break
        else:
            raise (exceptions.ApiForbiddenError
                   (f'Нет токена с правами {self._rights} и only_read = {self._only_read}',
                    wb_user_cabinet=wb_user_cabinet
                    ))
        self.headers = Headers(current_token)
        self._shop_id = current_token.shop_id



    @staticmethod
    def chunks(lst, n):
        for i in range(0, len(lst), n):
            yield lst[i:i + n]




