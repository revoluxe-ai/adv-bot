__all__ = [
    "delete_keywords_from_wl_by_mean_auto_ctr",
    "ClustersAdvStatUpdater",
    "ClustersAdvStatUpdaterContainer",
]


def __getattr__(name: str):
    if name == "delete_keywords_from_wl_by_mean_auto_ctr":
        from .delete_keywords_from_wl_by_mean_auto_ctr_manager import (
            delete_keywords_from_wl_by_mean_auto_ctr,
        )

        return delete_keywords_from_wl_by_mean_auto_ctr

    if name == "ClustersAdvStatUpdater":
        from .clusters_adv_stat_updater import ClustersAdvStatUpdater

        return ClustersAdvStatUpdater

    if name == "ClustersAdvStatUpdaterContainer":
        from .clusters_adv_stat_updater.di import ClustersAdvStatUpdaterContainer

        return ClustersAdvStatUpdaterContainer

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
