from abc import ABC

from dependency_injector.wiring import Provide, inject
import typing
if typing.TYPE_CHECKING:
    from app.core.di.wb_manager_hub import WBManagerHub
    from app.core.di.wb_manager_hub import WBManagerHubFactory


class WBBaseManager(ABC):
    def __init__(self, shop_id: str):
        self._shop_id = shop_id

    @inject
    def _get_wb_manager_hub(self,
                            manager_hub_factory: "WBManagerHubFactory" \
                                    = Provide[
                                'module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory']) \
            -> "WBManagerHub":
        wb_manager_hub = manager_hub_factory.get_wb_manager_hub(self._shop_id)
        return wb_manager_hub


    @property
    def wb_manager_hub(self) -> "WBManagerHub":
        return self._get_wb_manager_hub()


