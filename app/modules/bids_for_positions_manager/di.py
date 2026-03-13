from dependency_injector import containers, providers

from .bids_for_positions_manager import BidsForPositionsManager
from .clickhouse_manager import BidsForPositionsClickHouseManager


class BidsForPositionsManagerContainer(containers.DeclarativeContainer):
    _clickhouse_manager = providers.Singleton(BidsForPositionsClickHouseManager)
    bids_for_positions_manager = providers.Singleton(
        BidsForPositionsManager,
        clickhouse_manager=_clickhouse_manager,
    )
