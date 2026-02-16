from dependency_injector import containers, providers

from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager
from .clickhouse_manager import ClickHouseManager
from .fill_bids_by_positions import FillBidsByPositions


class FillBidsByPositionsContainer(containers.DeclarativeContainer):

    _tasks_manager = providers.Dependency(instance_of=TasksManager)

    _clickhouse_manager = providers.Singleton(ClickHouseManager)


    workers = providers.List(
        providers.Singleton(FillBidsByPositions,
                            clickhouse_manager=_clickhouse_manager,
                            tasks_manager=_tasks_manager,
                            update_time=5 * 60)
    )


