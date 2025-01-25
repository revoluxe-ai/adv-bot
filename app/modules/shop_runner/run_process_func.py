import asyncio
import os
from asyncio import Task

from sqlalchemy import or_, select

from app.modules.common_slaves.wildberries.models import WBCabinet
from app.modules.shop_runner.wb_shop import WBShop
from app.utils.db.session_maker import get_async_session_maker as sm
import logging

logger = logging.getLogger(__name__)


from multiprocessing import Process, Manager, Pool
import asyncio




def run_shop(shop_id):
    asyncio.run(_run_shop_async(shop_id))


async def _run_shop_async(shop_id):
    try:
        wb_shop = WBShop(shop_id)
        await wb_shop.run()
    except Exception as e:
        logger.error(f"Ошибка в процессе обновления магазина {shop_id}: {e}")


async def __shop_update():
    active_tasks = {}
    with Pool(processes=os.cpu_count()) as pool:
        while True:
            stmt = select(WBCabinet.shop_id).filter(
                or_(
                    WBCabinet.bonus > 0,
                    WBCabinet.balance > 0,
                )
            )
            async with sm() as session:
                result = await session.execute(stmt)
                shop_ids = result.scalars().all()
            for shop_id in shop_ids:
                if shop_id not in active_tasks:
                    # Добавляем задачу в пул
                    active_tasks[shop_id] = pool.apply_async(run_shop, (shop_id,))
                    logger.debug(f"Процесс обновления магазина {shop_id} запущен")
                else:
                    task = active_tasks[shop_id]
                    if task.ready():
                        logger.debug(f"Обновление магазина {shop_id} завершено")
                        if task.successful():
                            logger.debug(f"Процесс {shop_id} завершился успешно")
                        else:
                            logger.error(f"Процесс {shop_id} завершился с ошибкой")
                        del active_tasks[shop_id]

            # Проверка на завершение задач, которые больше не актуальны
            for shop_id in list(active_tasks.keys()):
                if shop_id not in shop_ids:
                    active_tasks[shop_id].terminate()
                    logger.debug(f"Обновление shop_id {shop_id} остановлено")
                    del active_tasks[shop_id]


async def shop_update_run():
    while True:
        try:
            await __shop_update()
        except:
            logger.error('Ошибка обновления магазина', exc_info=True)
        finally:
            await asyncio.sleep(60)

def run():
    asyncio.run(shop_update_run())