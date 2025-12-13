from dependency_injector import containers, providers

from app.core.di.wb_manager_hub import WBManagerHubFactory
from app.core.mp.wb.api.httpx_client_handler import HttpxClientHandler
from app.core.redis_manager_v2.redis_client import RedisClient


class WBManagerHubFactoryContainer(containers.DeclarativeContainer):
    redis_client = providers.Dependency(instance_of=RedisClient)
    _httpx_client_handler = providers.Resource(HttpxClientHandler)

    wb_manager_hub_factory = providers.Singleton(
        WBManagerHubFactory,
        httpx_client_handler=_httpx_client_handler,
        redis_client_wrapper=redis_client,
    )
