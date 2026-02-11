from dependency_injector import containers, providers

from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager
from .fill_keyword_deltas import FillKeywordDeltas
from .clickhouse_manager import ClickhouseManager

class FillKeywordDeltasContainer(containers.DeclarativeContainer):

    tasks_queue_manager = providers.Singleton(TasksManager, max_workers=1)

    _clickhouse_manager = providers.Singleton(ClickhouseManager)

    workers = providers.List(
        providers.Singleton(FillKeywordDeltas,
                            tasks_queue_manager=tasks_queue_manager,
                            clickhouse_manager=_clickhouse_manager,
                            from_time_hours=2,
                            update_period_time_minutes=5),
        providers.Singleton(FillKeywordDeltas,
                            tasks_queue_manager=tasks_queue_manager,
                            clickhouse_manager=_clickhouse_manager,
                            from_time_hours=6,
                            update_period_time_minutes=30),
        providers.Singleton(FillKeywordDeltas,
                            tasks_queue_manager=tasks_queue_manager,
                            clickhouse_manager=_clickhouse_manager,
                            from_time_hours=48,
                            update_period_time_minutes=24 * 60),
    )
