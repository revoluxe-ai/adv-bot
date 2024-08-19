import datetime
from app.utils.redis_manager import RedisEvent
from app.utils.redis_func_cache import set_config
from ..wb_keywords_parser import parser
from ...admin_bot.sender import sender_manager
set_config()
import asyncio
import logging
from app.modules.wb_adv_updater.data_manager import DataGetter
from app.utils.db.session_maker import get_async_session_maker
from ..common_slaves.wildberries import super_cabinet_manager as users_manager
from .wb_manager import Manager

sm = get_async_session_maker

logger = logging.getLogger(__name__)



async def run_update_predict_ctr():
     manager = Manager()
     await manager.update_predict_ctr()

async def   run_update_keyword_stat():
    while True:
        try:
            await __run_update_keyword_stat()
        except Exception as e:
            logger.error(f'Ошибка обновления статистики ключей {e}', exc_info=True)
        await asyncio.sleep(0)


async def __run_update_keyword_stat():
    wb_cabinet_tasks = {}
    adv_update_tasks = {}
    # not_first_runs = set()
    manager = Manager()
    while True:
        accesses = users_manager.get_accesses_for_wb_cabinets()
        async for access in accesses:
            cabinet_id = access.wb_cabinet.id
            if cabinet_id not in wb_cabinet_tasks:
                task = asyncio.create_task(
                    manager.update_keyword_stat(access,
                                                      adv_update_tasks,))
                wb_cabinet_tasks[cabinet_id] = task

            else:
                if wb_cabinet_tasks[cabinet_id].done():
                    logger.info(f'Задача обновления статистики ключей завершена для кабинета {cabinet_id}')
                    if wb_cabinet_tasks[cabinet_id].exception():
                        logger.error(
                            f'Ошибка обновления статистики ключей: '
                            f'{wb_cabinet_tasks[cabinet_id].exception()},'
                            f' для кабинета {cabinet_id}'
                        )

                    del wb_cabinet_tasks[cabinet_id]
        await asyncio.sleep(0)


async def run_update_data_in_neo4j():
    manager = Manager()
    await asyncio.gather(
            update_cards_in_graph(),
            manager.update_wb_adv_phrase_in_db(),
        )


async def run_update_minus_keywords_on_wb():
    manager = Manager()
    await manager\
        .update_keywords_in_advs()


async def run_update_model():
    manager = Manager()
    while True:
        try:
            await manager.update_model()
        except Exception as e:
            logger.error(f'Ошибка обновления модели {e}', exc_info=True)
        await asyncio.sleep(0)


async def update_cards_in_graph():
    manager = Manager()
    while True:
        try:
            await manager.update_cards_in_graph()
            logger.debug('Карточки обновлены')
        except Exception as exc:
            logger.error(f'Ошибка обновления карточек в neo4j {exc}', exc_info=True)
        await asyncio.sleep(0)



async def update_min_ctr_in_global_wb_category_settings():
    manager = Manager()
    while True:
        try:
            await manager.update_min_ctr_in_global_wb_category_settings()
        except Exception as e:
            logger.error(f'Ошибка обновления минимальных цен {e}')
        # await asyncio.sleep(60)

async def update_all_data_in_db():
    manager = Manager()
    tasks = {}
    while True:
        try:
            await manager.update_all_data_in_db_run(tasks=tasks)
        except Exception as exc:
            logger.error(f'Ошибка обновления данных в базе {exc}', exc_info=True)
            await asyncio.sleep(0)


async def demo_subscribe():
    manager = Manager()
    while True:
        await manager.check_accesses()
        await asyncio.sleep(60*60)

async def shop_subscribe_control():
    manager = Manager()
    await manager.shop_subscribe_control()

async def clear_data_for_expired_wb_cabinets():
    manager = Manager()
    while True:
        try:
            await manager.clear_expired_data()
        except Exception as e:
            logger.error(f'Ошибка очистки данных для просроченных кабинетов {e}', exc_info=True)
            await asyncio.sleep(0)

async def process_payment_for_advs():
    manager = Manager()
    while True:
        hours = datetime.datetime.now().hour
        if 12 < hours < 18:
            try:
                await manager.process_payment_for_advs()
            except Exception as e:
                logger.error(f'Ошибка обработки платежей {e}', exc_info=True)
        await asyncio.sleep(60*60)

async def write_positions_to_db():
    while True:
        try:
            await parser.add_wb_positions_from_queue_to_db()
        except Exception as e:
            logger.error(f'Ошибка добавления позиций в базу {e}', exc_info=True)
        await asyncio.sleep(0)

async def parser_all_white_phrase():
   await parser.parser_all_white_phrase()


async def reset_out_positions_in_redis():
    while True:
        try:
            await parser.reset_from_redis_positions_of_out_index()
        except Exception as e:
            logger.error(f'Ошибка сброса позиций в redis {e}', exc_info=True)

        await asyncio.sleep(10)


async def keywords_parsing_process():
    await __keywords_parsing_process()


async def __keywords_parsing_process():
    await  parser_all_white_phrase()

async def payment_for_parsing_keyword():
    manager = Manager()
    while True:
        hours = datetime.datetime.now().hour
        if 12 < hours < 21:
            try:
                await manager.process_payment_for_parsing()
            except Exception as e:
                logger.error(f'Ошибка обработки платежей {e}', exc_info=True)
        await asyncio.sleep(60 * 60)

async def payment_for_auto_bidder():
    manager =   Manager()
    while True:
        hours = datetime.datetime.now().hour
        if 11 < hours < 21:
            try:
                await manager.process_payment_for_auto_bidder()
            except Exception as e:
                logger.error(f'Ошибка обработки платежей {e}', exc_info=True)
        await asyncio.sleep(0)





async def run_bidder_process():
    manager = Manager()
    while True:
        try:
            await manager.run_bidder_process()
        except Exception as e:
            logger.error(f'Ошибка процесса управления ставками {e}', exc_info=True)
        await asyncio.sleep(0)

async def run_update_vectors_in_redis():
    manager = Manager()
    while True:
        try:
            await manager.update_vectors_in_redis()
        except Exception as e:
            logger.error(f'Ошибка обновления векторов в redis {e}', exc_info=True)
        await asyncio.sleep(0)

async def run_vector_update_in_neo4j():
    manager = Manager()
    await manager.update_vectors_update_in_graph()



def  run_main_process():
    asyncio.run(main_loop())


def run_main_coroutines():
    asyncio.run(main_loop())

async def main_loop():
    await asyncio.gather(
        payment_for_auto_bidder(),
        payment_for_parsing_keyword(),
        run_bidder_process(),
        # .clear_data_for_expired_wb_cabinets(),
        process_payment_for_advs(),
        # .update_min_ctr_in_global_wb_category_settings(),
        update_all_data_in_db(),
        run_update_minus_keywords_on_wb(),
        return_exceptions=False
    )
