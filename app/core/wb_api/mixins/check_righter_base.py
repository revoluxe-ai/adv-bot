import json
from abc import ABC, abstractmethod

import aiohttp

from app.core.wb_api.base import BaseAPI
from app.core.wb_api.exceptions import ApiForbiddenError
from app.core.wb_api.http_request import try_except_decorator, requests
import logging

class CheckRighter(BaseAPI, ABC):

    @try_except_decorator(3, 30)
    async def ping_rights(self):
        url = self.ENTRY_POINT
        async with aiohttp.ClientSession() as session:
            response = await requests(session, 'GET', url=url, headers=self.headers.standart)
            response = json.loads(response)
            status = response['Status']
            if status == "OK":
                return 'OK'
            else:
                logging.error(f'Нет доступов для аналитики: {response}')
                raise ApiForbiddenError('Нет прав')

    @property
    @abstractmethod
    def ENTRY_POINT(self) -> str:
        pass