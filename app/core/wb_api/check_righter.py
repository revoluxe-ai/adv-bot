import asyncio
import json
import logging

from aiohttp import ClientSession

from app.core.wb_api.exceptions import ApiForbiddenError
from app.core.wb_api.http_request import requests
from app.modules.common_slaves.wildberries.models import WBToken

__all__ = ["CheckRighter"]


class CheckRighter:
    headers: "Headers"

    check_entry_points = [
        ["https://content-api.wildberries.ru/ping", "Контент"],
        [
            "https://seller-analytics-api.wildberries.ru/ping",
            "Аналитика",
        ],
        [
            "https://advert-api.wildberries.ru/ping",
            "Реклама",
        ],
    ]

    async def check_all_rights(self, token: WBToken, session: ClientSession) -> bool:
        from app.modules.common_slaves.wildberries.ABC_WB_API import Headers

        self.headers = Headers(token)
        check_tasks = [
            self.ping_rights(entry_point, session)
            for entry_point in self.check_entry_points
        ]
        try:
            await asyncio.gather(*check_tasks)
        except ApiForbiddenError as e:
            logging.error(f"У токена нет достаточных прав: {e}")
            del e
            return False
        return True

    async def ping_rights(self, entry_point: list[str], session) -> str:
        url = entry_point[0]
        name = entry_point[1]

        response = await requests(
            session, "GET", url=url, headers=self.headers.standart
        )
        response = json.loads(response)
        status = response["Status"]
        if status == "OK":
            return "OK"
        else:
            logging.error(f"Нет доступов для аналитики: {response}")
            raise ApiForbiddenError(f"Нет прав для {name}")
