import json
import logging

from app.core.wb_api.exceptions import ApiForbiddenError
from app.core.wb_api.http_request import requests, try_except_decorator
from app.core.wb_api.protocols import WBAPIProtocol


class WBAdvPingMixin(WBAPIProtocol):
    PREFIX = "https://seller-analytics-api"

    @try_except_decorator(3, 30)
    async def ping_analytics_rights_and_connect(self) -> str:
        """Проверяет доступ к аналитике WB и подключение."""
        url = f"{self.PREFIX}.wildberries.ru/ping"
        response = await requests(
            self.session, "GET", url=url, headers=self.headers.standart
        )
        if response:
            response_data = json.loads(response)
            if isinstance(response_data, dict) and "Status" in response_data:
                status = response_data["Status"]
                if status == "OK":
                    return "OK"

        logging.error(f"Нет доступов для аналитики: {response}")
        raise ApiForbiddenError("Неверный API ключ")
