import asyncio
import datetime
import logging

from aiohttp import ClientSession

from app.utils.db.session_maker import get_async_session_maker
from app.utils.redis_func_cache import set_config
from . import wb_manager
from .ml_data_manager import update_model
from ..user_message_sender import message_for_not_pay_user_sender

set_config()

sm = get_async_session_maker

logger = logging.getLogger(__name__)


async def run_update_predict_ctr():
    await wb_manager.update_predict_ctr()


async def run_update_all_keywords_on_wb():
    async with ClientSession() as client_session:
        while True:
            try:
                await wb_manager.update_all_keywords_on_wb(client_session)
            except Exception:
                logger.error("Ошибка обновления фраз", exc_info=True)
            await asyncio.sleep(5)


async def sender_message_to_not_pay_users():
    while True:
        try:
            await message_for_not_pay_user_sender.send_messages_to_users()
        except Exception as e:
            logger.error(f"Ошибка отправки сообщений {e}", exc_info=True)
            del e
        await asyncio.sleep(60 * 5)


async def process_payment_for_advs() -> None:
    while True:
        try:
            time_now = datetime.datetime.now()
            if 2 < time_now.hour < 5:
                await wb_manager.process_payment_for_advs()
        except Exception as e:
            logger.error(f"Ошибка обработки платежей {e}", exc_info=True)
            del e
        await asyncio.sleep(30 * 60)


async def run_update_vectors_in_redis() -> None:
    await wb_manager.update_vectors_in_redis()


async def run_vector_update_in_neo4j() -> None:
    await wb_manager.update_vectors_update_in_graph()


async def run_update_model():
    while True:
        try:
            await update_model()
        except Exception as e:
            logger.error(f"Ошибка обновления модели {e}", exc_info=True)
            del e
        await asyncio.sleep(0)


async def update_wb_config_data(client_session) -> None:
    await wb_manager.update_wb_config_data_run(client_session)


async def main_loop(client_session):
    await asyncio.gather(
        process_payment_for_advs(),
        run_update_vectors_in_redis(),
        run_vector_update_in_neo4j(),
        update_wb_config_data(client_session),
    )


async def run_main_coroutines():
    async with ClientSession() as client_session:
        while True:
            try:
                await main_loop(client_session)
            except Exception as e:
                logger.error(f"Ошибка в главном цикле {e}", exc_info=True)
                del e
                await asyncio.sleep(0)
