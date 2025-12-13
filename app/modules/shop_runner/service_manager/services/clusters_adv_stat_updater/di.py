import typing

from dependency_injector import containers, providers
from dependency_injector.providers import Provider
if typing.TYPE_CHECKING:
     from app.core.di.wb_manager_hub import WBManagerHub
from app.modules.shop_runner.service_manager.services import ClustersAdvStatUpdater


class ClustersAdvStatUpdaterContainer(containers.DeclarativeContainer):

    _wb_manager_hub: Provider["WBManagerHub"] = providers.Dependency() # pyright: ignore

    clusters_adv_stat_updater: Provider[ClustersAdvStatUpdater] = providers.Singleton(ClustersAdvStatUpdater,
                                                                            wb_manager_hub=_wb_manager_hub)