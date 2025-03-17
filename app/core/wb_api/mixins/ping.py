import json
import logging

import aiohttp

from app.core.wb_api.base import BaseAPI
from app.core.wb_api.exceptions import ApiForbiddenError
from app.core.wb_api.http_request import requests, try_except_decorator



class WBAdvPingMixin(BaseAPI):
    @try_except_decorator(3, 30)
    async def ping_analytics_rights_and_connect(self):
        url = 'https://seller-analytics-api.wildberries.ru/ping'
        async with aiohttp.ClientSession() as session:
            response = await requests(session, 'GET', url=url, headers=self.headers.standart)
            response = json.loads(response)
            status = response['Status']
            if status == "OK":
                return 'OK'
            else:
                logging.error(f'Нет доступов для аналитики: {response}')
                raise ApiForbiddenError


