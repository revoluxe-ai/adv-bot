import asyncio
import os
from asyncio import Task

from sqlalchemy import or_, select

from app.modules.common_slaves.wildberries.models import WBCabinet, AdvSetting, WBToken
from app.modules.shop_runner.wb_shop import WBShop
from app.settings import settings
from app.utils.db.session_maker import get_async_session_maker as sm
import logging

logger = logging.getLogger(__name__)


import asyncio




async def run_shop(shop_id, wb_cabinet_original_id,  all_api_keys: list[str], parsing_queue_dict: dict[set]):
    logger.debug(f'Запускаю асинхронную функцию старта обновления магазина с shop_id: {shop_id}')
    await _run_shop_async(shop_id,
                          wb_cabinet_original_id,
                          all_api_keys,
                          parsing_queue_dict)


async def _run_shop_async(shop_id, wb_cabinet_original_id, all_api_keys, parsing_queue_dict):
    while True:
        try:
            wb_shop = WBShop(shop_id,
                             wb_cabinet_original_id,
                             all_api_keys,
                             parsing_queue_dict)
            await wb_shop.run()
        except Exception as e:
            logger.error(f"Ошибка в процессе обновления магазина {shop_id}", exc_info=True)
        await asyncio.sleep(1)


async def __shop_update():
    active_tasks = {}

    while True:
        # Получение списка магазинов с активными настройками
        stmt = select(WBCabinet.shop_id, WBCabinet.id).distinct()\
            .join(WBCabinet.adv_settings)\
            .filter(
                WBCabinet.adv_settings.any(AdvSetting.bot_active == True),

            )

        shop_filter_list: list[str] = settings.SHOP_FILTER_LIST

        if shop_filter_list:
            stmt = stmt.filter(WBCabinet.shop_id.in_(shop_filter_list))
        async with sm() as session:
            result = await session.execute(stmt)
            data_rows = result.all()

        # Получение всех API ключей
        stmt = select(WBToken)
        async with sm() as session:
            result = await session.execute(stmt)
            wb_tokens: list[WBToken] = result.scalars().all()

        all_api_keys = [token.api_key for token in wb_tokens]
        all_shop_ids = {data[0] for data in data_rows}  # Используем set для удобства

        # Запуск обновления для новых магазинов
        for data in data_rows:
            shop_id = data[0]
            wb_cabinet_original_id = data[1]
            parsing_queue_dict = {'test_key':"test"}
            if shop_id not in active_tasks:
                async def run_shop_task(shop_id,
                                        wb_cabinet_original_id,
                                        all_api_keys,
                                        parsing_queue_dict ):
                    try:
                        logger.debug(f"Запуск обновления магазина {shop_id}")
                        await run_shop(shop_id,
                                       wb_cabinet_original_id,
                                       all_api_keys,
                                       parsing_queue_dict
                                       )
                        logger.debug(f"Обновление магазина {shop_id} завершено")
                    except Exception as e:
                        logger.error(f"Ошибка обновления магазина {shop_id}: {e}")

                # Создание асинхронной задачи
                task = asyncio.create_task(run_shop_task(shop_id,
                                                         wb_cabinet_original_id,
                                                         all_api_keys,
                                                         parsing_queue_dict))
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