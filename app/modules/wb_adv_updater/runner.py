"""Runner coroutines for periodic WB updater tasks."""

import asyncio
import datetime
import logging
import socket

from aiohttp import ClientSession
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from app.core.di.app_container import AppContainer
from app.core.di.di_manager import DIManager

# Import token monitoring for expiration checks
from app.modules.token_monitoring.services.token_expiration_service import (
    run_token_expiration_check,
)
from app.utils.backoff import retry_delay_with_jitter
from app.utils.db.session_maker import get_async_session_maker
from app.utils.redis_func_cache import set_config
from . import wb_manager
from ..billing.event_manager.event_manager import BillingEventManager
from ..user_message_sender import message_for_not_pay_user_sender
from .modules.balance_exp_informer.manager import balance_expiration_informer_update


set_config()

sm = get_async_session_maker

logger = logging.getLogger(__name__)

INFRA_RETRY_BASE_SECONDS = 5
INFRA_RETRY_MAX_SECONDS = 300
UNKNOWN_RETRY_BASE_SECONDS = 10
UNKNOWN_RETRY_MAX_SECONDS = 120


# TODO: добавить статус -1 в кампании, что значит "кампания на стадии удаления"


def _calc_backoff(
    attempt: int,
    base_seconds: int,
    max_seconds: int,
) -> float:
    return retry_delay_with_jitter(
        attempt,
        base_seconds=base_seconds,
        max_seconds=max_seconds,
    )


def _is_infra_error(exc: BaseException) -> bool:
    if isinstance(exc, (RedisConnectionError, RedisTimeoutError, TimeoutError)):
        return True
    message = str(exc).lower()
    if any(
        hint in message
        for hint in (
            "name or service not known",
            "temporary failure in name resolution",
            "nodename nor servname provided",
            "connection refused",
            "max retries exceeded",
            "failed to resolve",
        )
    ):
        return True
    return isinstance(exc, socket.gaierror)

async def run_update_all_keywords_on_wb() -> None:
    async with await DIManager.create(AppContainer):  # type: ignore[attr-defined]
        async with ClientSession() as client_session:
            while True:
                try:
                    await wb_manager.update_all_keywords_on_wb(client_session)
                except Exception: # noqa
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


async def process_token_expiration_check() -> None:
    """Запуск проверки истекающих токенов один раз в сутки в 9:00"""
    while True:
        try:
            now = datetime.datetime.now()

            # Вычисляем следующие 9:00
            next_run = now.replace(hour=9, minute=0, second=0, microsecond=0)
            if now.hour >= 9:
                next_run += datetime.timedelta(days=1)

            # Спим до 9:00
            sleep_seconds = (next_run - now).total_seconds()
            logger.info(
                f"Следующая проверка токенов: {next_run} (через {sleep_seconds / 3600:.1f} часов)"
            )
            await asyncio.sleep(sleep_seconds)

            # Выполняем проверку токенов
            try:
                stats = await run_token_expiration_check()
                logger.info(f"Проверка токенов завершена: {stats}")
            except Exception as e:
                logger.error(f"Ошибка проверки токенов: {e}", exc_info=True)
        except Exception as e:
            logger.exception('Ошибка процесса уведомлений о токенах')
            await asyncio.sleep(60)

async def process_payment_for_advs() -> None:
    from app.modules.billing import (
        process_payment_for_advs as billing_process_payment_for_advs,
    )
    """Запуск периодического списания с self-heal retry и backoff."""
    run_attempt = 0
    while True:
        try:
            async with await DIManager.create(AppContainer):  # type: ignore[attr-defined]
                run_attempt = 0
                billing_attempt = 0
                logger.info("Billing loop started")
                while True:
                    try:
                        await billing_process_payment_for_advs(global_ttl=900)
                        billing_attempt = 0
                        logger.info(
                            "Billing run completed",
                            extra={
                                "component": "billing_loop",
                                "is_infra": False,
                            },
                        )
                    except Exception as exc:
                        billing_attempt += 1
                        is_infra = _is_infra_error(exc)
                        pause = _calc_backoff(
                            attempt=billing_attempt,
                            base_seconds=INFRA_RETRY_BASE_SECONDS if is_infra else UNKNOWN_RETRY_BASE_SECONDS,
                            max_seconds=INFRA_RETRY_MAX_SECONDS if is_infra else UNKNOWN_RETRY_MAX_SECONDS,
                        )
                        logger.error(
                            "Billing run failed; retry scheduled",
                            exc_info=True,
                            extra={
                                "component": "billing_loop",
                                "error_class": type(exc).__name__,
                                "is_infra": is_infra,
                                "retry_in_sec": round(pause, 2),
                                "restart_count": billing_attempt,
                            },
                        )
                        await asyncio.sleep(pause)
                        continue
                    await asyncio.sleep(60 * 60)
        except Exception as exc:
            run_attempt += 1
            is_infra = _is_infra_error(exc)
            pause = _calc_backoff(
                attempt=run_attempt,
                base_seconds=INFRA_RETRY_BASE_SECONDS if is_infra else UNKNOWN_RETRY_BASE_SECONDS,
                max_seconds=INFRA_RETRY_MAX_SECONDS if is_infra else UNKNOWN_RETRY_MAX_SECONDS,
            )
            logger.error(
                "Billing loop bootstrap failed; restarting loop",
                exc_info=True,
                extra={
                    "component": "billing_loop_bootstrap",
                    "error_class": type(exc).__name__,
                    "is_infra": is_infra,
                    "retry_in_sec": round(pause, 2),
                    "restart_count": run_attempt,
                },
            )
            await asyncio.sleep(pause)



async def main_loop(event_manager: BillingEventManager) -> None:
    await asyncio.gather(
        process_payment_for_advs(),
        # # TODO: этот функционал должен быть перенесен в shop_run, проверить не дублирует ли
        # # TODO: Не понятно эта функция вообще работает или нет
        process_token_expiration_check(),
        balance_expiration_informer_update(event_manager),
    )


async def run_main_coroutines() -> None:
    from app.core.di.app_container import AppContainer
    event_manager = BillingEventManager()
    async with await DIManager.create(AppContainer):  # type: ignore[attr-defined]
        await __run_main_coroutines(event_manager)

async def __run_main_coroutines(event_manager: BillingEventManager) -> None:
    run_attempt = 0
    while True:
        try:
            await main_loop(event_manager)
            run_attempt = 0
        except Exception as exc:
            run_attempt += 1
            is_infra = _is_infra_error(exc)
            pause = _calc_backoff(
                attempt=run_attempt,
                base_seconds=INFRA_RETRY_BASE_SECONDS if is_infra else UNKNOWN_RETRY_BASE_SECONDS,
                max_seconds=INFRA_RETRY_MAX_SECONDS if is_infra else UNKNOWN_RETRY_MAX_SECONDS,
            )
            logger.error(
                "Main updater loop crashed; restarting",
                exc_info=True,
                extra={
                    "component": "main_updater_loop",
                    "error_class": type(exc).__name__,
                    "is_infra": is_infra,
                    "retry_in_sec": round(pause, 2),
                    "restart_count": run_attempt,
                },
            )
            await asyncio.sleep(pause)
