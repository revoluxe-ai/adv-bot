import aiohttp
from dependency_injector import providers, containers
from dependency_injector.resources import AsyncResource


class GetIpSessionResource(AsyncResource[aiohttp.ClientSession]):
    async def init(self) -> aiohttp.ClientSession:
        connector = aiohttp.TCPConnector(limit_per_host=1)
        session = aiohttp.ClientSession(connector=connector)
        return session

    async def shutdown(self, session) -> None:
        await session.close()



class AiohttpClientForWBFrontParser(AsyncResource[aiohttp.ClientSession]):
    async def init(self) -> aiohttp.ClientSession:
        connector = aiohttp.TCPConnector(limit_per_host=1)
        session = aiohttp.ClientSession(connector=connector)
        return session

    async def shutdown(self, session) -> None:
        await session.close()


class HttSessionsContainer(containers.DeclarativeContainer):
    """Контейнер для HTTP сессий."""

    get_ip_session = providers.Resource(GetIpSessionResource)
    aiohttp_client_for_parser = providers.Resource(AiohttpClientForWBFrontParser)



