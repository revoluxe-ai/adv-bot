from __future__ import annotations

from dependency_injector import containers, providers
from dependency_injector.providers import Provider

from app.core.di.wb_manager_hub import WBManagerHub
from .clusters_adv_stat_updater import ClustersAdvStatUpdater


class ClustersAdvStatUpdaterContainer(containers.DeclarativeContainer):

    _wb_manager_hub: Provider["WBManagerHub"] = providers.Dependency(instance_of=WBManagerHub)

    clusters_adv_stat_updater: Provider[ClustersAdvStatUpdater] = providers.Singleton(ClustersAdvStatUpdater,
                                                                            wb_manager_hub=_wb_manager_hub)
