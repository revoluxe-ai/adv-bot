import datetime
from app.utils.redis_func_cache import set_config
from .ml_data_manager import update_model
from ..full_stat_adv_updater import new_update_shop_loop
from ..user_message_sender import message_for_not_pay_user_sender
from ..wb_keywords_parser import parser
from ..wb_keywords_parser.parser import Parser

set_config()
import asyncio
import logging
from app.utils.db.session_maker import get_async_session_maker
from ..common_slaves.wildberries import super_cabinet_manager as users_manager
from . import wb_manager



sm = get_async_session_maker

logger = logging.getLogger(__name__)



async def run_update_predict_ctr():
     await wb_manager.update_predict_ctr()

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
    while True:
        accesses = users_manager.get_accesses_for_wb_cabinets()
        async for access in accesses:
            cabinet_id = access.wb_cabinet.id
            if cabinet_id not in wb_cabinet_tasks:
                task = asyncio.create_task(
                    wb_manager.update_keyword_stat(access,
                                                      adv_update_tasks,))
                wb_cabinet_tasks[cabinet_id] = task

            else:
                if wb_cabinet_tasks[cabinet_id].done():
                    logger.debug(f'Задача обновления статистики ключей завершена для кабинета {cabinet_id}')
                    if wb_cabinet_tasks[cabinet_id].exception():
                        logger.error(
                            f'Ошибка обновления статистики ключей: '
                            f'{wb_cabinet_tasks[cabinet_id].exception()},'
                            f' для кабинета {cabinet_id}'
                        )

                    del wb_cabinet_tasks[cabinet_id]
        await asyncio.sleep(0)



async def run_update_all_keywords_on_wb():
    while True:
        try:
            await wb_manager.update_all_keywords_on_wb()
        except Exception:
            logger.error('Ошибка обновления фраз', exc_info=True)
        await asyncio.sleep(5)



#
# async def update_min_ctr_in_global_wb_category_settings():
#     while True:
#         try:
#             await manager.update_min_ctr_in_global_wb_category_settings()
#         except Exception as e:
#             logger.error(f'Ошибка обновления минимальных цен {e}')
#         # await asyncio.sleep(60)

async def update_all_data_in_db():
    tasks = {}
    while True:
        try:
            await wb_manager.update_all_data_in_db_run(tasks=tasks)
        except Exception as exc:
            logger.error(f'Ошибка обновления данных в базе {exc}', exc_info=True)
        finally:
            await asyncio.sleep(15)


async def demo_subscribe():
    while True:
        await wb_manager.check_accesses()
        await asyncio.sleep(60*60)

async def shop_subscribe_control():
    await wb_manager.shop_subscribe_control()

async def clear_data_for_expired_wb_cabinets():
    while True:
        try:
            await wb_manager.clear_expired_data()
        except Exception as e:
            logger.error(f'Ошибка очистки данных для просроченных кабинетов {e}', exc_info=True)
            await asyncio.sleep(0)


async def sender_message_to_not_pay_users():
    while True:
        try:
            await message_for_not_pay_user_sender.send_messages_to_users()
        except Exception as e:
            logger.error(f'Ошибка отправки сообщений {e}', exc_info=True)
        await asyncio.sleep(60*5)



async def process_payment_for_advs():
    while True:
        try:
            await wb_manager.process_payment_for_advs()
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

async def __keywords_parsing_process():
   parser = Parser()
   await asyncio.gather(parser.generate_parsing_tasks_dict(),
                        parser.parsing_by_dict())


async def reset_out_positions_in_redis():
    while True:
        try:
            await parser.reset_from_redis_positions_of_out_index()
        except Exception as e:
            logger.error(f'Ошибка сброса позиций в redis {e}', exc_info=True)

        await asyncio.sleep(10)


async def keywords_parsing_process():
    while True:
        try:
            await asyncio.wait_for(__keywords_parsing_process(),
                                     timeout=60*60)
        except:
            logger.error('Ошибка парсинга ключей', exc_info=True)
        await asyncio.sleep(0)


async def payment_for_parsing_keyword():
    while True:
        hours = datetime.datetime.now().hour
        if 12 < hours < 21:
            try:
                await wb_manager.process_payment_for_parsing()
            except Exception as e:
                logger.error(f'Ошибка обработки платежей {e}', exc_info=True)
        await asyncio.sleep(60 * 60)

async def payment_for_auto_bidder():
    while True:
        hours = datetime.datetime.now().hour
        if 11 < hours < 21:
            try:
                await wb_manager.process_payment_for_auto_bidder()
            except Exception as e:
                logger.error(f'Ошибка обработки платежей {e}', exc_info=True)
        await asyncio.sleep(0)





async def run_update_vectors_in_redis():
    await wb_manager.update_vectors_in_redis()


async def run_vector_update_in_neo4j():
    await wb_manager.update_vectors_update_in_graph()



async def run_update_model():
    while True:
        try:
            await update_model()
        except Exception as e:
            logger.error(f'Ошибка обновления модели {e}', exc_info=True)
        await asyncio.sleep(0)



async def main_loop():
    await asyncio.gather(
        process_payment_for_advs(),
        run_update_vectors_in_redis(),
        run_vector_update_in_neo4j(),
        return_exceptions=False
    )


async def run_main_coroutines():
    while True:
        try:
            await main_loop()
        except Exception as e:
            logger.error(f'Ошибка в главном цикле {e}', exc_info=True)
            await asyncio.sleep(0)

