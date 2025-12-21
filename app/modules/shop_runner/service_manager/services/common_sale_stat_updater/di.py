from dependency_injector import containers, providers
from dependency_injector.providers import Provider

from app.core.di.wb_manager_hub import WBManagerHub

from .clickhouse_common_stat_manager import ClickHouseCommonStatManager
from .common_sale_stat_updater import CommonSaleStatUpdater


class CommonSaleStatUpdaterContainer(containers.DeclarativeContainer):
    _wb_manager_hub: Provider[WBManagerHub] = providers.Dependency()  # pyright: ignore

    clickhouse_common_stat_manager: Provider[ClickHouseCommonStatManager] = (
        providers.Singleton(ClickHouseCommonStatManager)
    )

    common_sale_stat_updater: Provider[CommonSaleStatUpdater] = providers.Singleton(
        CommonSaleStatUpdater,
        wb_manager_hub=_wb_manager_hub,
        clickhouse_manager=clickhouse_common_stat_manager,
    )


