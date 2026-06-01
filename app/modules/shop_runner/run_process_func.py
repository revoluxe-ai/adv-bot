import asyncio
import logging
from asyncio import Task

import redis
from aiohttp import ClientSession
from dependency_injector.wiring import Provide, inject
from sqlalchemy import select


from app.core.wb_api.exceptions import ApiForbiddenError, NO_FREE_TOKENS_MESSAGE
from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.common_slaves.wildberries import super_cabinet_manager
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.modules.token_monitoring.models import NotificationType
from app.modules.token_monitoring.services.cabinet_status_service import (
    deactivate_cabinet_atomic_with_user_trackers,
)
from app.modules.shop_runner.modules.wb_api import WBApi

from app.modules.shop_runner.shop_id_filters import apply_shop_id_filters
from app.modules.shop_runner.shop_run_worker.redis_manager import RedisShopManager
from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager
from app.modules.shop_runner.wb_shop import WBShop
from app.settings import settings
from app.utils.backoff import exponential_retry_delay_seconds
from app.utils.db.session_maker import get_async_session_maker as sm
import typing

if typing.TYPE_CHECKING:
    from app.core.di.wb_manager_hub import WBManagerHubFactory
    from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import PlanFactReader


logger = logging.getLogger(__name__)

UNKNOWN_ERROR_RETRY_BASE_SECONDS = 10
UNKNOWN_ERROR_RETRY_MAX_SECONDS = 120


async def run_shop_task(
    shop_id: str,
    client_session: ClientSession,
    redis_manager: RedisShopManager,
    tasks_manager: TasksManager,
    plan_fact_reader: "PlanFactReader",
) -> None:
    try:
        await _run_shop_task(
            shop_id,
            client_session,
            redis_manager,
            tasks_manager,
            plan_fact_reader,
        )
    except Exception as e:
        logger.exception(e,exc_info=True)
        raise e

    return None


@inject
async def _run_shop_task(
    shop_id: str,
    client_session: ClientSession,
    redis_manager: RedisShopManager,
    tasks_manager: TasksManager,
    plan_fact_reader: "PlanFactReader",
    redis_client_wrapper: RedisClient = Provide["redis_client_wrapper"],
    wb_manager_hub_factory: "WBManagerHubFactory" = Provide[
        "module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory"
    ],
) -> None:
    from app.modules.shop_runner.service_manager.exceptions import NotFoundActiveAdvCompany
    from app.modules.shop_runner.service_manager.exc import StopShopUpdateException
    wb_manager_hub_factory.set_wb_manager_hub(shop_id)

    async def _deactivate_cabinet() -> None:
        await deactivate_cabinet_atomic_with_user_trackers(
            shop_id,
            notification_type=NotificationType.TOKEN_DEACTIVATED.value,
        )

    try:
        access = await super_cabinet_manager.get_access_for_wb_cabinet(shop_id)
        wb_api = WBApi(access, client_session)
        wb_manager_hub = wb_manager_hub_factory.get_wb_manager_hub(shop_id)
        wb_shop = WBShop(
            wb_api,
            redis_manager,
            redis_client_wrapper,
            tasks_manager=tasks_manager,
            plan_fact_reader=plan_fact_reader,
            wb_manager_hub=wb_manager_hub,
        )
        await wb_shop.run()
    except StopShopUpdateException:
        return None
    except BaseExceptionGroup as eg:
        api_forbidden = eg.subgroup(lambda e: isinstance(e, ApiForbiddenError))
        if api_forbidden is not None:
            if any(
                getattr(e, "text", None) == NO_FREE_TOKENS_MESSAGE
                for e in api_forbidden.exceptions
            ):
                await _deactivate_cabinet()
                return None
        raise eg
    except ApiForbiddenError as e:
        if e.text == NO_FREE_TOKENS_MESSAGE:
            await _deactivate_cabinet()
            # ЕСЛИ БУДУТ ДРУГИЕ ОШИБКИ, то они проглотся без выброса - таки задуманно
            return None
        raise e
    except NotFoundActiveAdvCompany:
        return None
    except Exception as exc:
        logger.error(f"Ошибка обработки магазина {shop_id}, {exc}", exc_info=True)
        raise exc
    finally:
        wb_manager_hub_factory.reset_shop(shop_id)

async def _update_tasks(
    active_tasks: dict[str, Task[None]],
    client_session: ClientSession,
    redis_manager: RedisShopManager,
    tasks_manager: TasksManager,
    plan_fact_reader: "PlanFactReader",
) -> None:
    stmt = select(WBCabinet.shop_id).where(WBCabinet.active.is_(True))
    stmt = apply_shop_id_filters(stmt, WBCabinet.shop_id)

    shop_ids: set[str] = set()
    async with sm(read_only=True) as session:
        result = await session.execute(stmt)
        all_needs_for_run_shop_ids = result.scalars().all()

    for shop_id in all_needs_for_run_shop_ids:
        shop_ids.add(shop_id)

        if shop_id not in active_tasks:
            task = asyncio.create_task(
                run_shop_task(
                    shop_id,
                    client_session,
                    redis_manager,
                    tasks_manager=tasks_manager,
                    plan_fact_reader=plan_fact_reader,
                )
            )
            active_tasks[shop_id] = task
            logger.debug(f"Процесс обновления магазина {shop_id} запущен")
        else:
            task = active_tasks[shop_id]
            if task.done():
                if exc := task.exception():
                    logger.exception(
                        "Не обработанная ошибка выполнения задачи магазина: %s",
                        exc,
                    )
                    # Удаляем до raise: иначе при retry внешнего цикла та же запись
                    # остаётся done-with-exception и блокирует обход навсегда.
                    del active_tasks[shop_id]
                    raise exc
                del active_tasks[shop_id]

        await asyncio.sleep(0.1)

    # Остановка задач, которые больше не должны крутиться
    for shop_id in tuple(active_tasks.keys()):
        if shop_id not in shop_ids:
            task = active_tasks.pop(shop_id)
            if not task.done():
                _ = task.cancel()
                logger.debug(f"Обновление магазина {shop_id} остановлено")
        await asyncio.sleep(0.1)



async def run() -> None:
    from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import PlanFactReader
    tasks_manager = TasksManager(max_workers=settings.MAX_TASKS)
    stop_event = asyncio.Event()
    queue_task = asyncio.create_task(tasks_manager.run_queue(stop_event))
    plan_fact_reader = PlanFactReader()
    async with ClientSession() as session:
        shop_loop_task = asyncio.create_task(
            _run_shops_loop(
                tasks_manager=tasks_manager,
                client_session=session,
                plan_fact_reader=plan_fact_reader,
            )
        )
        try:
            await shop_loop_task
        finally:
            stop_event.set()
            await queue_task

async def _run_shops_loop(
    tasks_manager: TasksManager,
    client_session: ClientSession,
    plan_fact_reader: "PlanFactReader",
) -> None:
    redis_manager = RedisShopManager()
    active_tasks: dict[str, Task[None]] = {}
    unknown_error_attempt = 0
    while True:
        try:
            await _update_tasks(
                active_tasks,
                client_session,
                redis_manager,
                tasks_manager=tasks_manager,
                plan_fact_reader=plan_fact_reader,
            )
            unknown_error_attempt = 0
        except redis.exceptions.BusyLoadingError:
            logger.warning("Редис еще не загрузилась")
            await asyncio.sleep(15 * 60)
        except (TimeoutError, redis.exceptions.ConnectionError) as exc:
            logger.warning(
                "Инфраструктурная ошибка (DB/Redis), повтор через 30с: %r", exc
            )
            await asyncio.sleep(30)
        except Exception as exc:
            unknown_error_attempt += 1
            pause = int(
                exponential_retry_delay_seconds(
                    unknown_error_attempt,
                    base_seconds=UNKNOWN_ERROR_RETRY_BASE_SECONDS,
                    max_seconds=UNKNOWN_ERROR_RETRY_MAX_SECONDS,
                )
            )
            logger.error(
                "Ошибка обработки задач обновления магазинов, повтор через %ss: %s",
                pause,
                exc,
                exc_info=True,
            )
            await asyncio.sleep(pause)
