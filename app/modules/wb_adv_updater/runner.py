import asyncio
import logging
import datetime
from app.utils.redis_func_cache import set_config
from .ml_data_manager import update_model
from ..user_message_sender import message_for_not_pay_user_sender
from ..wb_keywords_parser.parser import Parser
from app.utils.db.session_maker import get_async_session_maker
from . import wb_manager
from ...settings import settings

set_config()

sm = get_async_session_maker

logger = logging.getLogger(__name__)


async def run_update_predict_ctr():
    await wb_manager.update_predict_ctr()


async def run_update_all_keywords_on_wb():
    while True:
        try:
            await wb_manager.update_all_keywords_on_wb()
        except Exception:
            logger.error('Ошибка обновления фраз', exc_info=True)
        await asyncio.sleep(5)


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


async def __keywords_parsing_process():
    parser = Parser()
    await asyncio.gather(
        parser.generate_parsing_tasks_dict(),
        parser.parsing_by_dict())


async def keywords_parsing_process():
    while True:
        parsing_timeout = settings.PARSING_TIMEOUT
        try:
            await asyncio.wait_for(
                __keywords_parsing_process(),
                timeout=parsing_timeout)
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
        run_vector_update_in_neo4j()
    )


async def run_main_coroutines():
    while True:
        try:
            await main_loop()
        except Exception as e:
            logger.error(f'Ошибка в главном цикле {e}', exc_info=True)
            await asyncio.sleep(0)
