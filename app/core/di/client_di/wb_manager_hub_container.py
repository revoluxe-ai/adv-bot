from typing import cast

from dependency_injector import containers, providers
from dependency_injector.providers import Provider

from .wb_data_container import WBDataContainer
from ...mp.wb.api.auth_client_handler import AuthClientHandler
from ...mp.wb.api.httpx_client_handler import HttpxClientHandler
from ...mp.wb.api.managers import WBDataManager
from ...mp.wb.api.wb_manager_hub import WBManagerHub


class WBManagerHubContainer(containers.DeclarativeContainer):
    _shop_id = providers.Dependency(instance_of=str)
    _httpx_client_handler = providers.Dependency(instance_of=HttpxClientHandler)

    _auth_client_handler = providers.Singleton(
        AuthClientHandler,
        shop_id=_shop_id,
        httpx_client_handler=_httpx_client_handler,
    )

    _wb_data_container: WBDataContainer = providers.Container(  # pyright: ignore
        WBDataContainer,
        _auth_client_handler=_auth_client_handler,
    )

    _wb_data_manager: Provider[WBDataManager] = cast(
        Provider[WBDataManager],
        _wb_data_container.wb_data_manager,
    )

    wb_manager_hub = providers.Singleton(
        WBManagerHub,
        wb_data_manager=_wb_data_manager,
    )
