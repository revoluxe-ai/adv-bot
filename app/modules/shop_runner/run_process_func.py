import asyncio
import logging
from asyncio import Task

import redis
from aiohttp import ClientSession
from dependency_injector.wiring import Provide, inject
from sqlalchemy import select

from app.core.di.wb_manager_hub import WBManagerHubFactory
from app.core.wb_api.exceptions import ApiForbiddenError
from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.common_slaves.wildberries import super_cabinet_manager
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.modules.shop_runner.modules.wb_api import WBApi
from app.modules.shop_runner.service_manager.exc import StopShopUpdateException
from app.modules.shop_runner.service_manager.exceptions import NotFoundActiveAdvCompany
from app.modules.shop_runner.shop_run_worker.redis_manager import RedisShopManager
from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager
from app.modules.shop_runner.wb_shop import WBShop
from app.settings import settings
from app.utils.db.session_maker import get_async_session_maker as sm

logger = logging.getLogger(__name__)


@inject
async def run_shop_task(
    shop_id: str,
    client_session: ClientSession,
    redis_manager: RedisShopManager,
    db_tasks_manager: TasksManager,
    http_tasks_manager: TasksManager,
    redis_client_wrapper: RedisClient = Provide["redis_client_wrapper"],
    wb_manager_hub_factory: WBManagerHubFactory = Provide[
        "module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory"
    ],
) -> None:
    wb_manager_hub_factory.set_wb_manager_hub(shop_id)

    async def _deactivate_cabinet() -> None:
        async with sm() as session:
            stmt = select(WBCabinet).where(WBCabinet.shop_id == shop_id)
            result = await session.execute(stmt)
            wb_cabinet = result.scalar()
            if wb_cabinet is not None:
                wb_cabinet.active = False
                await session.commit()

    try:
        access = await super_cabinet_manager.get_access_for_wb_cabinet(shop_id)
        wb_api = WBApi(access, client_session)
        wb_shop = WBShop(
            wb_api,
            redis_manager,
            redis_client_wrapper,
            db_tasks_manager=db_tasks_manager,
            http_tasks_manager=http_tasks_manager,
        )
        await wb_shop.run()
    except StopShopUpdateException:
        return None
    except ApiForbiddenError:
        await _deactivate_cabinet()
        return None
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
    db_tasks_manager: TasksManager,
    http_tasks_manager: TasksManager,
) -> None:
    stmt = (
        select(WBCabinet.shop_id)
    )

    shop_filter_list: list[str] = settings.SHOP_FILTER_LIST

    stmt = stmt.where(WBCabinet.active.is_(True))
    if shop_filter_list:
        stmt = stmt.where(WBCabinet.shop_id.in_(shop_filter_list))

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
                    db_tasks_manager=db_tasks_manager,
                    http_tasks_manager=http_tasks_manager,
                )
            )
            active_tasks[shop_id] = task
            logger.debug(f"Процесс обновления магазина {shop_id} запущен")
        else:
            task = active_tasks[shop_id]
            if task.done():
                if exc := task.exception():
                    logger.exception(
                        f"Не обработанная ошибка выполнения задачи магазина: {exc}"
                    )
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
    async with ClientSession() as session:
        db_tasks_manager = TasksManager(max_workers=settings.MAX_TASKS)
        db_stop_event = asyncio.Event()
        db_queue_task = asyncio.create_task(db_tasks_manager.run_queue(db_stop_event))
        http_task_manager = TasksManager(max_workers=settings.MAX_HTTP_TASKS)
        http_stop_event = asyncio.Event()
        http_queue_task = asyncio.create_task(http_task_manager.run_queue(http_stop_event))
        shop_loop_task = asyncio.create_task(
            _run_shops_loop(db_tasks_manager=db_tasks_manager,
                            http_task_manager=http_task_manager,
                            client_session=session)
        )
        try:
            await shop_loop_task
        finally:
            db_stop_event.set()
            await db_queue_task
            http_stop_event.set()
            await http_queue_task

async def _run_shops_loop(
    db_tasks_manager: TasksManager,
    http_task_manager: TasksManager,
    client_session: ClientSession,
) -> None:
    redis_manager = RedisShopManager()
    active_tasks: dict[str, Task[None]] = {}
    while True:
        try:
            await _update_tasks(active_tasks,
                                client_session,
                                redis_manager,
                                db_tasks_manager=db_tasks_manager,
                                http_tasks_manager=http_task_manager)
        except redis.exceptions.BusyLoadingError:
            logger.warning("Редис еще не загрузилась")
            await asyncio.sleep(15 * 60)
        except (TimeoutError, redis.exceptions.ConnectionError) as exc:
            logger.warning(
                "Инфраструктурная ошибка (DB/Redis), повтор через 30с: %r", exc
            )
            await asyncio.sleep(30)
        except Exception as exc:
            logger.error(
                f"Ошибка обработки задач обновления магазинов: {exc}", exc_info=True
            )
            raise exc
