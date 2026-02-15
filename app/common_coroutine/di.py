from dependency_injector import containers, providers
from poetry.console.commands import self

from .corounines_manager.coroutines_manager import CommonCoroutineManager
from .coroutines.fill_bids_by_positions.di import FillBidsByPositionsContainer
from .coroutines.fill_keyword_deltas import FillKeywordDeltasContainer
from .coroutines.target_keyword_place_priors_updater.priors_updaters.di import PriorsUpdatersContainer
from ..modules.shop_runner.tasks_manager.tasks_manager import TasksManager

class CommonCoroutineContainer(containers.DeclarativeContainer):

    _common_tasks_manager = providers.Singleton(TasksManager, max_workers=1)

    _fill_keyword_deltas_container = providers.Container(
        FillKeywordDeltasContainer,
        tasks_manager=_common_tasks_manager,
    )

    _fill_bids_by_positions_container = providers.Container(
        FillBidsByPositionsContainer,
        _tasks_manager=_common_tasks_manager,
    )

    _target_keyword_place_priors_container = providers.Container(
        PriorsUpdatersContainer,
        _tasks_manager=_common_tasks_manager,
    )

    coroutine_manager = providers.Singleton(
        CommonCoroutineManager,
        workers=providers.Callable(
            lambda keyword_workers, bid_workers, priors_workers: [
                *keyword_workers,
                *bid_workers,
                *priors_workers,
            ],
            _fill_keyword_deltas_container.workers,
            _fill_bids_by_positions_container.workers,
            _target_keyword_place_priors_container.workers,
        ),
    )

    task_queue_managers = providers.List(
        _common_tasks_manager,
    )
