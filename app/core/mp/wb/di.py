from dependency_injector import providers, containers


from app.core.mp.wb.api.httpx_client_handler import HttpxClientHandler
from app.core.mp.wb.api.wb_manager_hub_factory import WBManagerHubFactory


class WBManagerHubFactoryContainer(containers.DeclarativeContainer):
    _httpx_client_handler = providers.Singleton(HttpxClientHandler)

    wb_manager_hub_factory = providers.Singleton(WBManagerHubFactory,
                                                 httpx_client_handler=_httpx_client_handler)