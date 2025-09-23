import httpx
from dependency_injector import containers, providers


class ApiSectionContainer(containers.DeclarativeContainer):
    config = providers.Configuration()
    httpx_async_client = providers.Singleton(
        httpx.AsyncClient,
        timeout=config.timeout.as_float(),
        base_url=config.base_url.as_(str),
    )

    def init_resources(self):
        client = self.httpx_async_client()
        if client.is_closed:
            client = httpx.AsyncClient()
            self.httpx_async_client.override(client)

    async def shutdown_resources(self):
        client = self.httpx_async_client()
        if not client.is_closed:
            await client.aclose()
