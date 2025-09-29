from enum import Enum

import httpx


class ApiSection(Enum):
    """Разделы API WB"""

    PROMOTIONS = "promotions"


class CustomAsyncHttpxClient:
    def __init__(self, httpx_client: httpx.AsyncClient, dyn_headers: Mapping[str, str]):
        self._httpx = httpx_client
        # сюда кладём только динамические заголовки (обычно Authorization)
        self._dyn_headers = dict(dyn_headers)

    async def request(self, *args, **kwargs) -> httpx.Response:
        # заголовки, пришедшие от вызывающего кода (kwargs['headers']), не теряем
        req_headers = kwargs.pop("headers", {})
        # объединяем: динамические (Authorization) + пер-запросные; пер-запросные имеют приоритет
        headers = {**self._dyn_headers, **req_headers}
        # client-level headers, заданные в AsyncClient, автоматически сольются внутри httpx
        return await self._httpx.request(*args, headers=headers, **kwargs)


class ClientProxy:
    """Прокси для клиентов, позволяющий динамически менять токены"""

    def __init__(
        self,
        *,
        shop_id: str,
        base_url: str,
    ):
        """
        Инициализация клиента.

        Args:
            base_url: Базовый URL API
            token_manager: Менеджер токенов
            api_section: Раздел API (promotions, content, etc.)
            shop_id: ID магазина (опционально, может браться из контекста)
            timeout: Таймаут запросов в секундах
            max_connections: Максимальное количество соединений
            raise_on_unexpected_status: Бросать ли исключение при неожиданном статусе
            verify_ssl: Проверка SSL сертификата
            follow_redirects: Следовать ли редиректам
            **kwargs: Дополнительные параметры для httpx
        """
        self._shop_id = shop_id
        self._base_url = base_url
        # Параметры для httpx
        self._timeout = httpx.Timeout(30)
        self._max_connections = 200
        self._verify_ssl = False
        self._follow_redirects = False

        # Атрибуты для совместимости с сгенерированным кодом
        self.raise_on_unexpected_status = True
        self._httpx = httpx.AsyncClient(
            base_url=base_url,
            timeout=self._timeout,
            limits=httpx.Limits(max_connections=self._max_connections),
            verify=self._verify_ssl,
            follow_redirects=self._follow_redirects,
        )

    async def get_async_httpx_client(self) -> "CustomAsyncHttpxClient":
        current_token = await self.token_manager.get_token(
            self._shop_id, self._base_url
        )
        headers = {"Authorization": f"Bearer {current_token}"}
        client = CustomAsyncHttpxClient(self._httpx, headers)
        return client

    async def close(self) -> None:
        await self._httpx.aclose()
