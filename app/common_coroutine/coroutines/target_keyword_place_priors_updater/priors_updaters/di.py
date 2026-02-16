from dependency_injector import containers, providers

from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager
from .category_prior_updater import CategoryPriorUpdater
from .category_prior_updater.clickhouse_manager import (
    ClickHouseManager as CategoryClickHouseManager,
)
from .global_prior_updater import GlobalPriorUpdater
from .global_prior_updater.clickhouse_manager import ClickHouseManager

class PriorsUpdatersContainer(containers.DeclarativeContainer):

    _tasks_manager = providers.Dependency(instance_of=TasksManager)

    _global_clickhouse_manager = providers.Singleton(ClickHouseManager)
    _category_clickhouse_manager = providers.Singleton(CategoryClickHouseManager)

    workers = providers.List(
        providers.Singleton(
            GlobalPriorUpdater,
            tasks_manager=_tasks_manager,
            click_house_manager=_global_clickhouse_manager,
            update_period_seconds=5 * 60,
        ),
        providers.Singleton(
            CategoryPriorUpdater,
            tasks_manager=_tasks_manager,
            click_house_manager=_category_clickhouse_manager,
            update_period_seconds=5 * 60,
        ),
    )
