from dependency_injector import containers, providers
from .corounines_manager.coroutines_manager import CommonCoroutineManager
from .coroutines.fill_keyword_deltas import FillKeywordDeltasContainer


class CommonCoroutineContainer(containers.DeclarativeContainer):

    fill_keyword_deltas_container = providers.Container(FillKeywordDeltasContainer)

    coroutine_manager = providers.Singleton(
        CommonCoroutineManager,
        workers=fill_keyword_deltas_container.workers,
    )

    task_queue_managers = providers.List(
        fill_keyword_deltas_container.tasks_queue_manager,
    )
