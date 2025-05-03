import logging
from asyncio import Task

from sqlalchemy import select

from app.modules.common_slaves.wildberries.models import WBCabinet, AdvSetting
from app.modules.shop_runner.exceptions import ShopRunnerCriticalError
from app.modules.shop_runner.wb_shop import WBShop
from app.settings import settings
from app.utils.db.session_maker import get_async_session_maker as sm

logger = logging.getLogger(__name__)


import asyncio


async def run_shop(shop_id: str, wb_cabinet_original_id: int) -> None:
    logger.debug(
        f"Запускаю асинхронную функцию старта обновления магазина с shop_id: {shop_id}"
    )
    await _run_shop_async(shop_id, wb_cabinet_original_id)


async def _run_shop_async(shop_id: str, wb_cabinet_original_id: int) -> None:
    wb_shop = WBShop(shop_id, wb_cabinet_original_id)
    while True:
        try:
            await wb_shop.run()
        except Exception as e:
            logger.error(f"Ошибка в процессе обновления магазина: {e}", exc_info=True)
        finally:
            await asyncio.sleep(15)


async def run_shop_task(shop_id: str, wb_cabinet_original_id: int) -> None:
    while True:
        try:
            await run_shop(shop_id, wb_cabinet_original_id)
        except Exception as e:
            logger.error(f"Ошибка в процессе обновления магазина: {e}", exc_info=True)
        finally:
            await asyncio.sleep(15)


async def __shop_update(active_tasks: dict[str, Task[None]]) -> None:
    # Получение списка магазинов с активными настройками
    stmt = (
        select(WBCabinet.shop_id, WBCabinet.id)
        .distinct()
        .join(WBCabinet.adv_settings)
        .filter(
            WBCabinet.adv_settings.any(AdvSetting.bot_active == True),
        )
    )

    shop_filter_list: list[str] = settings.SHOP_FILTER_LIST

    if shop_filter_list:
        stmt = stmt.filter(WBCabinet.shop_id.in_(shop_filter_list))
    async with sm() as session:
        result = await session.execute(stmt)
        data_rows = result.all()
    all_shop_ids = []
    for row in data_rows:
        shop_id = row[0]
        all_shop_ids.append(shop_id)
        wb_cabinet_original_id = row[1]
        if shop_id not in active_tasks:
            # Создание асинхронной задачи
            task = asyncio.create_task(run_shop_task(shop_id, wb_cabinet_original_id))
            active_tasks[shop_id] = task
            logger.debug(f"Процесс обновления магазина {shop_id} запущен")
            await asyncio.sleep(1)

    # Завершение задач для неактуальных магазинов
    for shop_id in list(active_tasks.keys()):
        if shop_id not in all_shop_ids:
            task = active_tasks.pop(shop_id)
            if not task.done():
                task.cancel()
                logger.debug(f"Обновление магазина {shop_id} остановлено")
        await asyncio.sleep(0)


async def shop_update_run() -> None:
    active_tasks: dict[str, Task[None]] = {}
    while True:
        try:
            await __shop_update(active_tasks)
        except ShopRunnerCriticalError as e:
            raise e
        except Exception as e:
            logger.error(f"Ошибка цикла постановки задач {e}", exc_info=True)
            await asyncio.sleep(15)


def run() -> None:
    try:
        asyncio.run(shop_update_run())
    except Exception as e:
        logger.error(f"Необработанная ошибка: {e}", exc_info=True)
        raise ShopRunnerCriticalError from e
