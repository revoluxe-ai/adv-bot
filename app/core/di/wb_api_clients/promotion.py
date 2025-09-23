import httpx
from dependency_injector import containers, providers


class PromotionApiContainer(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(packages=[
        "app.modules.promotion",  # укажите нужные модули, где будет использоваться DI
    ])

    # Singleton httpx.AsyncClient для раздела promotion
    _httpx_session_client = providers.Singleton(
        httpx.AsyncClient,
        timeout=30.0,
    )

    promotion_client: providers.Factory(

    )

    # Lifecycle: инициализация и закрытие
    def init_resources(self):
        session: httpx.AsyncClient = self._httpx_session_client
        session.ping()  # Проверка соединения

    async def shutdown_resources(self):
        client = self.httpx_async_client()
        if not client.is_closed:
            await client.aclose()
