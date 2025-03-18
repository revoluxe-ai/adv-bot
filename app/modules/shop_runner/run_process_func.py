from concurrent.futures import ProcessPoolExecutor
from multiprocessing import Manager, cpu_count
import asyncio
import logging

from sqlalchemy import select

from app.modules.common_slaves.wildberries.models import WBCabinet, AdvSetting, WBToken
from app.modules.shop_runner.wb_shop import WBShop
from app.settings import settings
from app.utils.db.session_maker import get_async_session_maker as sm

logger = logging.getLogger(__name__)


async def run_shop(shop_id, wb_cabinet_original_id, all_api_keys, parsing_queue_dict):
    logger.debug(f'Запускаю асинхронную функцию старта обновления магазина с shop_id: {shop_id}')
    await _run_shop_async(shop_id, wb_cabinet_original_id, all_api_keys, parsing_queue_dict)


async def _run_shop_async(shop_id, wb_cabinet_original_id, all_api_keys, parsing_queue_dict):
    while True:
        try:
            wb_shop = WBShop(shop_id, wb_cabinet_original_id, all_api_keys, parsing_queue_dict)
            await wb_shop.run()
        except Exception as e:
            logger.error(f"Ошибка в процессе обновления магазина {shop_id}", exc_info=True)
        await asyncio.sleep(1)


def run_shop_task(shop_id, wb_cabinet_original_id, all_api_keys, parsing_queue_dict):
    try:
        logger.debug(f"Запуск обновления магазина {shop_id}")
        asyncio.run(run_shop(shop_id, wb_cabinet_original_id, all_api_keys, parsing_queue_dict))
        logger.debug(f"Обновление магазина {shop_id} завершено")
    except Exception as e:
        logger.error(f"Ошибка обновления магазина {shop_id}: {e}")


async def shop_update():
    active_tasks = {}
    loop = asyncio.get_running_loop()

    # Создаем пул без явных ограничений - процессы будут распределяться системой автоматически
    with ProcessPoolExecutor() as executor, Manager() as manager:
        parsing_queue_dict = manager.dict()
        logger.info(f"Запущен пул процессов без ограничений")

        while True:
            # Получаем список магазинов
            stmt = select(WBCabinet.shop_id, WBCabinet.id).distinct() \
                .join(WBCabinet.adv_settings) \
                .filter(WBCabinet.adv_settings.any(AdvSetting.bot_active == True))

            shop_filter_list = settings.SHOP_FILTER_LIST
            if shop_filter_list:
                stmt = stmt.filter(WBCabinet.shop_id.in_(shop_filter_list))

            async with sm() as session:
                result = await session.execute(stmt)
                data_rows = result.all()

            # Получаем все API ключи
            stmt = select(WBToken)
            async with sm() as session:
                result = await session.execute(stmt)
                wb_tokens = result.scalars().all()

            all_api_keys = [token.api_key for token in wb_tokens]
            all_shop_ids = {data[0] for data in data_rows}

            # Моментально запускаем все новые магазины без ожидания
            for n, data in enumerate(data_rows):
                shop_id = data[0]
                wb_cabinet_original_id = data[1]
                if shop_id not in active_tasks:
                    logger.debug(f"Запускаем процесс для магазина {shop_id}")
                    future = loop.run_in_executor(
                        executor,
                        run_shop_task,
                        shop_id, wb_cabinet_original_id, all_api_keys, parsing_queue_dict
                    )
                    active_tasks[shop_id] = future
                    logger.info(f'Всего запущено магазинов: {len(active_tasks)}')

            # Завершаем неактуальные магазины
            for shop_id in list(active_tasks.keys()):
                if shop_id not in all_shop_ids:
                    future = active_tasks.pop(shop_id)
                    future.cancel()
                    logger.debug(f"Остановлен процесс для магазина {shop_id}")

            # Очистка завершенных задач для предотвращения утечек памяти
            # (не влияет на работу других процессов)
            for shop_id in list(active_tasks.keys()):
                future = active_tasks[shop_id]
                if future.done():
                    try:
                        future.result()  # Получаем результат для отлова исключений
                    except Exception as e:
                        logger.error(f"Задача для магазина {shop_id} завершилась с ошибкой: {e}")
                    del active_tasks[shop_id]

            await asyncio.sleep(60)  # Пауза перед новым циклом


async def shop_update_run():
    while True:
        try:
            await shop_update()
        except Exception as e:
            logger.error(f'Ошибка обновления магазина: {e}', exc_info=True)
        finally:
            await asyncio.sleep(60)


def run():
    asyncio.run(shop_update_run())