import httpx

from app.core.mp.wb.api.adapter.sections_enum import SectionsEnum


class HttpxClientHandler:
    _BASE_URLS: dict[SectionsEnum, str] = {
        SectionsEnum.ANALYTIC_AND_DATA: "https://seller-analytics-api.wildberries.ru",
        SectionsEnum.PROMOTION: "https://advert-api.wildberries.ru",
    }

    def __init__(self):
        self._httpx_clients: dict[SectionsEnum, httpx.AsyncClient] = {}


    def get_httpx_client(self, section: SectionsEnum) -> httpx.AsyncClient:
        if section not in self._httpx_clients:
            base_url = self._BASE_URLS.get(section)
            if base_url is None:
                raise ValueError(f"Base URL for section {section} is not configured")

            # глобальный клиент
            timeout = httpx.Timeout(
                connect=10.0,
                read=30.0,
                write=10.0,
                pool=60.0
            )
            limits = httpx.Limits(
                max_connections=200,
                max_keepalive_connections=50
            )

            client = httpx.AsyncClient(
                base_url=base_url,
                timeout=timeout,
                limits=limits
            )

            self._httpx_clients[section] = client

        return self._httpx_clients[section]