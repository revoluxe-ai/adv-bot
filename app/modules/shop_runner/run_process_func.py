import asyncio
import os
from asyncio import Task

from sqlalchemy import or_, select

from app.modules.common_slaves.wildberries.models import WBCabinet, AdvSetting, WBToken
from app.modules.shop_runner.wb_shop import WBShop
from app.utils.db.session_maker import get_async_session_maker as sm
import logging

logger = logging.getLogger(__name__)


from multiprocessing import Process, Manager, Pool
import asyncio




def run_shop(shop_id, all_api_keys: list[str]):
    logger.debug(f'Запускаю асинхронную функцию старта обновления магазина с shop_id: {shop_id}')
    asyncio.run(_run_shop_async(shop_id, all_api_keys))


async def _run_shop_async(shop_id, all_api_keys):
    try:
        wb_shop = WBShop(shop_id, all_api_keys)
        await wb_shop.run()
    except Exception as e:
        logger.error(f"Ошибка в процессе обновления магазина {shop_id}", exc_info=True)


async def __shop_update():
    active_tasks = {}
    while True:
        stmt = select(WBCabinet.shop_id)\
            .join(WBCabinet.adv_settings)\
        .filter(
           WBCabinet.adv_settings.any(AdvSetting.bot_active == True)
        )
        async with sm() as session:
            result = await session.execute(stmt)
            shop_ids = result.scalars().all()
        stmt = select(WBToken)
        async with sm() as session:
            result = await session.execute(stmt)
            wb_tokens: list[WBToken] = result.scalars().all()
        all_api_keys = [token.api_key for token in wb_tokens]

        for shop_id in shop_ids:
            if shop_id not in active_tasks:
                process = Process(target=run_shop, args=(shop_id, all_api_keys,))
                process.start()
                active_tasks[shop_id] = process
                logger.debug(f"Процесс обновления магазина {shop_id} запущен")
            else:
                process = active_tasks[shop_id]
                if not process.is_alive():
                    logger.debug(f"Обновление магазина {shop_id} завершено")
                    process.join()  # Ожидание завершения процесса
                    del active_tasks[shop_id]

        # Завершение процессов для магазинов, которые больше не актуальны
        for shop_id in list(active_tasks.keys()):
            if shop_id not in shop_ids:
                active_tasks[shop_id].terminate()
                logger.debug(f"Обновление магазина {shop_id} остановлено")
                del active_tasks[shop_id]

        await asyncio.sleep(60)  # Задержка перед следующим циклом



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