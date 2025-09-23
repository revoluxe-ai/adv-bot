"""Runner coroutines for periodic WB updater tasks."""

import asyncio
import datetime
import logging

from aiohttp import ClientSession

from app.utils.db.session_maker import get_async_session_maker
from . import wb_manager
from .ml_data_manager import update_model
from ..user_message_sender import message_for_not_pay_user_sender

sm = get_async_session_maker

logger = logging.getLogger(__name__)


async def run_update_predict_ctr() -> None:
    await wb_manager.update_predict_ctr()


async def run_update_all_keywords_on_wb():
    async with ClientSession() as client_session:
        while True:
            try:
                await wb_manager.update_all_keywords_on_wb(client_session)
            except Exception as exc:
                logger.critical("Ошибка обновления фраз", exc_info=True)
                raise exc
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
    from app.modules.billing import process_payment_for_advs

    """Запуск один раз в сутки в 3:00"""
    while True:
        now = datetime.datetime.now()

        # Вычисляем следующие 3:00
        next_run = now.replace(hour=3, minute=0, second=0, microsecond=0)
        if now.hour >= 3:
            next_run += datetime.timedelta(days=1)

        # Спим до 3:00
        sleep_seconds = (next_run - now).total_seconds()
        logger.info(
            f"Следующий запуск платежей: {next_run} (через {sleep_seconds / 3600:.1f} часов)"
        )
        await asyncio.sleep(sleep_seconds)

        # Выполняем обработку
        try:
            await process_payment_for_advs()
            logger.info("Обработка платежей завершена успешно")
        except Exception as e:
            logger.error(f"Ошибка обработки платежей: {e}", exc_info=True)


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
        run_vector_update_in_neo4j(),  # TODO: проверить не дублируется ли эта функция в wb_shop runner
    )


async def run_main_coroutines():
    while True:
        try:
            await _run_main_coroutines()
        except Exception as e:
            logger.critical(f"Критическая ошибка в главном цикле {e}", exc_info=True)
            del e
        await asyncio.sleep(5)


async def _run_main_coroutines():
    from app.core.di.app_container import AppContainer

    container = AppContainer()
    try:
        result = container.init_resources()
        if result is not None:
            await result
        await __run_main_coroutines()
    finally:
        result = container.shutdown_resources()
        if result is not None:
            await result


async def __run_main_coroutines():
    async with ClientSession() as client_session:
        while True:
            try:
                await main_loop(client_session)
            except Exception as e:
                logger.error(f"Ошибка в главном цикле {e}", exc_info=True)
                del e
                await asyncio.sleep(0)
