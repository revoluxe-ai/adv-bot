import asyncio
from asyncio import Task

from sqlalchemy import or_, select

from app.modules.common_slaves.wildberries.models import WBCabinet
from app.modules.shop_runner.wb_shop import WBShop
from app.utils.db.session_maker import get_async_session_maker as sm
import logging

logger = logging.getLogger(__name__)


async def __shop_update(shop_update_tasks):
    stmt = select(WBCabinet.shop_id) \
        .filter(
        or_(WBCabinet.bonus > 0,
                    WBCabinet.balance > 0,
                    )
    )

    async with sm() as session:
        result = await session.execute(stmt)
        shop_ids = result.scalars().all()

    for shop_id in shop_ids:
        if shop_id not in shop_update_tasks:
            wb_shop = WBShop(shop_id)
            task = asyncio.create_task(wb_shop.run())
            logger.debug(f'Задача обновления магазина {shop_id} запущена')
            shop_update_tasks[shop_id] = task
            await asyncio.sleep(1)
        else:
            task = shop_update_tasks[shop_id]
            if task.done():
                logger.debug(f'Обновление магазина {shop_id} завершено')
                if task.exception():
                    logger.error(
                        f'Ошибка обновления магазина: '
                        f'{task.exception()},'
                        f' shop_id:  {shop_id}'
                    )

                del shop_update_tasks[shop_id]

    tasks_shop_ids = list(shop_update_tasks.keys())
    for shop_id in tasks_shop_ids:
        if shop_id not in shop_ids:
            task = shop_update_tasks[shop_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.debug(f'Обновление shop_id {shop_id} остановлено')
                del shop_update_tasks[shop_id]


async def shop_update_run():
    shop_update_tasks: dict[str, Task] = {}
    while True:
        try:
            await __shop_update(shop_update_tasks)
        except:
            logger.error('Ошибка обновления магазина', exc_info=True)
        finally:
            await asyncio.sleep(1)

def run():
    asyncio.run(shop_update_run())