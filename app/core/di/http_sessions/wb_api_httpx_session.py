import httpx
from dependency_injector import resources


def create_httpx_session() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(30.0),
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        verify=True,
    )


class ApiHttpxSessionLifecycle(resources.AsyncResource[None]):
    async def init(self, session: httpx.AsyncClient) -> None:
        pass

    async def shutdown(self, session: httpx.AsyncClient | None = None) -> None:
        if session:
            await session.aclose()
