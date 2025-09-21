import logging
from asyncio import Task

import redis
from aiohttp import ClientSession
from sqlalchemy import select

from app.modules.common_slaves.wildberries import super_cabinet_manager
from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet
from app.modules.shop_runner.modules.wb_api import WBApi
from app.modules.shop_runner.service_manager.exc import StopShopUpdateException
from app.modules.shop_runner.shop_run_worker.redis_manager import RedisShopManager
from app.modules.shop_runner.wb_shop import WBShop
from app.settings import settings
from app.utils.db.session_maker import get_async_session_maker as sm

logger = logging.getLogger(__name__)
import asyncio


async def run_shop_task(shop_id: str, client_session: ClientSession, redis_manager: RedisShopManager) -> None:
    while True:
        try:
            access = await super_cabinet_manager.get_access_for_wb_cabinet(shop_id)
            wb_api = WBApi(access, client_session)
            wb_shop = WBShop(wb_api, redis_manager)
            await wb_shop.run()
        except StopShopUpdateException:
            return None
        except Exception as exc:
            logger.error(f"Ошибка обработки магазина {shop_id}, {exc}", exc_info=True)
            del exc
            await asyncio.sleep(1)


async def _update_tasks(active_tasks: dict[str, Task[None]], client_session: ClientSession) -> None:
    # Получение списка магазинов с активными настройками
    stmt = (
        select(WBCabinet.shop_id)
        .distinct()
        .join(WBCabinet.adv_settings)
        .filter(
            WBCabinet.adv_settings.any(AdvSetting.bot_active is True),
        )
    )

    shop_filter_list: list[str] = settings.SHOP_FILTER_LIST

    if shop_filter_list:
        stmt = stmt.filter(WBCabinet.shop_id.in_(shop_filter_list))
    redis_manager = RedisShopManager()
    async with sm() as session:
        result = await session.execute(stmt)
        all_needs_for_run_shop_ids = result.scalars().all()
        for shop_id in all_needs_for_run_shop_ids:
            if shop_id not in active_tasks:
                # Создание асинхронной задачи
                task = asyncio.create_task(run_shop_task(shop_id, client_session, redis_manager))
                active_tasks[shop_id] = task
                logger.debug(f"Процесс обновления магазина {shop_id} запущен")
            else:
                task = active_tasks[shop_id]
                if task.done():
                    if exc := task.exception():
                        logger.exception(f"Не обработанная ошибка выполнения задачи магазина: {exc}")
                    del active_tasks[shop_id]

            await asyncio.sleep(0.1)

    all_shop_ids = tuple(active_tasks.keys())
    for shop_id in all_shop_ids:
        if shop_id not in all_needs_for_run_shop_ids:
            task = active_tasks.pop(shop_id)
            if not task.done():
                task.cancel()
                logger.debug(f"Обновление магазина {shop_id} остановлено")
        await asyncio.sleep(0.1)


async def run() -> None:
    async with ClientSession() as session:
        active_tasks: dict[str, Task[None]] = {}
        while True:
            try:
                await _update_tasks(active_tasks, session)
            except redis.exceptions.BusyLoadingError:
                logger.warning("Редис еще не загрузилась")
                await asyncio.sleep(15 * 60)
            except Exception as exc:
                logger.error(f"Ошибка обработки задач обновления магазинов: {exc}", exc_info=True)
                exc.__traceback__ = None
                del exc
                await asyncio.sleep(1)
