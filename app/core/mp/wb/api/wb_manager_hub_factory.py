from contextvars import ContextVar, Token

from app.core.di.client_di.wb_manager_hub_container import WBManagerHubContainer
from app.core.mp.wb.api.httpx_client_handler import HttpxClientHandler
from app.core.mp.wb.api.wb_manager_hub import WBManagerHub


class WBManagerHubFactory:
    _wb_manager_hub_context_var: ContextVar[WBManagerHub | None] = ContextVar('wb_manager_hub_context',
                                                                              default=None)

    def __init__(self, httpx_client_handler: HttpxClientHandler):

        self.__httpx_client_handler = httpx_client_handler
        self.__object_collection: dict[str,  WBManagerHub] = {}
        self._tokens: dict[str, Token[WBManagerHub | None]] = {}

    def set_wb_manager_hub(self, shop_id: str) -> None:
        if shop_id not in self.__object_collection:
            wb_manager_hub_container: WBManagerHubContainer = WBManagerHubContainer(
                _shop_id=shop_id,
                _httpx_client_handler=self.__httpx_client_handler
            )
            wb_manager_hub: WBManagerHub = wb_manager_hub_container.wb_manager_hub()
            self.__object_collection[shop_id] = wb_manager_hub
            self._set_manager_in_context(shop_id, wb_manager_hub)
        return None

    def get_wb_manager_hub(self, shop_id: str) -> WBManagerHub:
        self.set_wb_manager_hub(shop_id)
        return self.__object_collection[shop_id]

    def _set_manager_in_context(self, shop_id: str, wb_manager_hub: WBManagerHub) -> None:
        token = self._wb_manager_hub_context_var.set(wb_manager_hub)
        self._tokens[shop_id] = token

    def reset_shop(self, shop_id: str) -> None:
        self._wb_manager_hub_context_var.reset(self._tokens[shop_id])
        del self.__object_collection[shop_id]


    @classmethod
    def get_wb_manager_from_context(cls) -> WBManagerHub:
        hub: WBManagerHub | None = cls._wb_manager_hub_context_var.get()
        if hub is None:
            raise RuntimeError('WB manager hub not set')
        return hub





